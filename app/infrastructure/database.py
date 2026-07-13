import os
from typing import Optional

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database


load_dotenv()

_mongo_client: Optional[MongoClient] = None


def get_mongo_client() -> MongoClient:
    global _mongo_client

    if _mongo_client is None:
        mongo_uri = (
            os.getenv("MONGO_URI")
            or os.getenv("MONGODB_URI")
        )

        if not mongo_uri:
            raise ValueError(
                "MONGO_URI is missing from the .env file"
            )

        _mongo_client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=10000,
        )

        # Verify the MongoDB connection.
        _mongo_client.admin.command("ping")

    return _mongo_client


def get_database() -> Database:
    database_name = (
        os.getenv("MONGO_DB_NAME")
        or os.getenv("MONGODB_DATABASE")
        or os.getenv("DATABASE_NAME")
    )

    if not database_name:
        raise ValueError(
            "MONGO_DB_NAME is missing from the .env file"
        )

    return get_mongo_client()[database_name]


def get_requirement_extraction_collection() -> Collection:
    """
    Source collection.

    Requirements/files are read from this collection.
    """

    collection_name = os.getenv(
        "REQUIREMENT_EXTRACTION_COLLECTION_NAME",
        "TenderRequirementExtractions",
    )

    return get_database()[collection_name]


def get_deduplication_collection() -> Collection:
    """
    Destination collection.

    Deduplication input and LLM output are saved here.
    """

    collection_name = os.getenv(
        "DEDUPLICATION_COLLECTION_NAME",
        "TenderRequirementDeduplications",
    )

    return get_database()[collection_name]


def close_mongo_connection() -> None:
    global _mongo_client

    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None