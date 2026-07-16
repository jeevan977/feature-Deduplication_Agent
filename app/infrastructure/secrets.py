
from __future__ import annotations

import base64
import os
from typing import Any

from bson import ObjectId
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database


load_dotenv()


class SecretManager:
    """
    Retrieve and decrypt a secret stored in MongoDB.

    Required environment variables:

        MONGO_URI or MONGODB_URI
        SECRET_DB
        SECRET_COLLECTION
        OBJECT_ID
        ENCRYPTION_KEY

    The encrypted MongoDB value is expected to be:

        - Base64 encoded
        - AES-CBC encrypted
        - PKCS7 padded
        - Encrypted using a zero-filled 16-byte IV
    """

    def __init__(self) -> None:
        self.mongo_uri = (
            os.getenv("MONGO_URI")
            or os.getenv("MONGODB_URI")
            or "mongodb://localhost:27017/"
        ).strip()

        self.db_name = (
            os.getenv("SECRET_DB") or ""
        ).strip()

        self.collection_name = (
            os.getenv("SECRET_COLLECTION") or ""
        ).strip()

        self.object_id = (
            os.getenv("OBJECT_ID") or ""
        ).strip()

        self.encryption_key = (
            os.getenv("ENCRYPTION_KEY") or ""
        )

        self.client: MongoClient | None = None
        self.db: Database | None = None

        self._validate_environment_variables()
        self._connect()

    def _validate_environment_variables(self) -> None:
        """Validate the configuration required for secret retrieval."""

        if not self.mongo_uri:
            raise ValueError(
                "MONGO_URI or MONGODB_URI is missing "
                "from the .env file."
            )

        if not self.db_name:
            raise ValueError(
                "SECRET_DB is missing from the .env file."
            )

        if not self.collection_name:
            raise ValueError(
                "SECRET_COLLECTION is missing from "
                "the .env file."
            )

        if not self.object_id:
            raise ValueError(
                "OBJECT_ID is missing from the .env file."
            )

        if not ObjectId.is_valid(self.object_id):
            raise ValueError(
                "OBJECT_ID is not a valid MongoDB ObjectId."
            )

        if not self.encryption_key:
            raise ValueError(
                "ENCRYPTION_KEY is missing from "
                "the .env file."
            )

        key_bytes = self.encryption_key.encode("utf-8")

        if len(key_bytes) not in (16, 24, 32):
            raise ValueError(
                "ENCRYPTION_KEY must be exactly "
                "16, 24, or 32 bytes long."
            )

    def _connect(self) -> None:
        """Create and verify the MongoDB connection."""

        try:
            self.client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=10000,
            )

            self.client.admin.command("ping")

            self.db = self.client[self.db_name]

        except Exception as exc:
            self.close()

            raise ConnectionError(
                "Unable to connect to MongoDB for "
                "secret retrieval."
            ) from exc

    def get_document(self) -> dict[str, Any]:
        """Retrieve the configured security document."""

        if self.db is None:
            raise RuntimeError(
                "MongoDB connection is not available."
            )

        collection = self.db[self.collection_name]

        document = collection.find_one(
            {
                "_id": ObjectId(self.object_id),
            }
        )

        if document is None:
            raise ValueError(
                "MongoDB security document was not found. "
                f"Database: {self.db_name}, "
                f"Collection: {self.collection_name}, "
                f"ObjectId: {self.object_id}"
            )

        return document

    def decrypt(self, encrypted_text: str) -> str:
        """Decrypt a Base64-encoded AES-CBC encrypted value."""

        if not encrypted_text:
            raise ValueError(
                "Encrypted text cannot be empty."
            )

        key_bytes = self.encryption_key.encode("utf-8")
        initialization_vector = bytes(AES.block_size)

        try:
            encrypted_bytes = base64.b64decode(
                encrypted_text,
                validate=True,
            )

        except Exception as exc:
            raise ValueError(
                "The encrypted secret is not valid Base64."
            ) from exc

        if not encrypted_bytes:
            raise ValueError(
                "The encrypted secret decoded to an empty value."
            )

        if len(encrypted_bytes) % AES.block_size != 0:
            raise ValueError(
                "The encrypted secret length is invalid "
                "for AES-CBC."
            )

        try:
            cipher = AES.new(
                key_bytes,
                AES.MODE_CBC,
                initialization_vector,
            )

            padded_plaintext = cipher.decrypt(encrypted_bytes)

            decrypted_bytes = unpad(
                padded_plaintext,
                AES.block_size,
            )

            decrypted_value = decrypted_bytes.decode("utf-8")

        except UnicodeDecodeError as exc:
            raise ValueError(
                "The decrypted secret is not valid UTF-8. "
                "Check ENCRYPTION_KEY."
            ) from exc

        except ValueError as exc:
            raise ValueError(
                "Failed to decrypt the secret. "
                "Check ENCRYPTION_KEY, IV and padding."
            ) from exc

        decrypted_value = decrypted_value.strip()

        if not decrypted_value:
            raise ValueError(
                "The decrypted secret is empty."
            )

        return decrypted_value

    def get_secret(
        self,
        field_name: str = "Security",
    ) -> str:
        """Retrieve and decrypt a secret field from MongoDB."""

        if not field_name or not field_name.strip():
            raise ValueError(
                "field_name cannot be empty."
            )

        document = self.get_document()
        encrypted_secret = document.get(field_name)

        if encrypted_secret is None:
            available_fields = [
                str(key)
                for key in document.keys()
                if key != "_id"
            ]

            raise ValueError(
                f"'{field_name}' field was not found "
                "in the MongoDB security document. "
                f"Available fields: {available_fields}"
            )

        if not isinstance(encrypted_secret, str):
            raise ValueError(
                f"'{field_name}' must contain an "
                "encrypted string value."
            )

        return self.decrypt(encrypted_secret)

    def close(self) -> None:
        """Close the MongoDB connection safely."""

        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None

    def __enter__(self) -> "SecretManager":
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.close()