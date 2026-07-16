
# from __future__ import annotations

# import os
# from typing import Any

# from dotenv import load_dotenv
# from langchain_groq import ChatGroq
# from langchain_mistralai import ChatMistralAI
# from langchain_openai import ChatOpenAI

# from app.infrastructure.secrets import SecretManager


# load_dotenv()


# def get_required_environment_value(
#     variable_name: str,
# ) -> str:
#     """Read and validate a required environment variable."""

#     value = os.getenv(variable_name)

#     if value is None or not value.strip():
#         raise ValueError(
#             f"{variable_name} is missing in the .env file"
#         )

#     return value.strip()


# # def get_openai_api_key() -> str:
# #     """
# #     Retrieve and decrypt the OpenAI API key from MongoDB.

# #     SecretManager is created only when OpenAI is selected.
# #     This prevents MongoDB secret loading when Mistral or Groq
# #     is the configured provider.
# #     """

# #     with SecretManager() as secret_manager:
# #         openai_api_key = secret_manager.get_secret(
# #             field_name="Security"
# #         )

# #     if not openai_api_key:
# #         raise ValueError(
# #             "Decrypted OpenAI API key is empty"
# #         )

# #     return openai_api_key

# def get_openai_api_key() -> str:
#     """
#     Read and decrypt the OpenAI API key from MongoDB.

#     The MongoDB Security field must contain only the raw
#     OpenAI API key before encryption.
#     """

#     with SecretManager() as secret_manager:
#         openai_api_key = secret_manager.get_secret(
#             field_name="Security"
#         )

#     openai_api_key = str(
#         openai_api_key or ""
#     ).strip()

#     if not openai_api_key:
#         raise ValueError(
#             "The decrypted OpenAI API key is empty."
#         )

#     if openai_api_key.lower().startswith("bearer "):
#         raise ValueError(
#             "The decrypted OpenAI API key must not "
#             "contain the 'Bearer ' prefix."
#         )

#     if (
#         openai_api_key.startswith('"')
#         or openai_api_key.endswith('"')
#         or openai_api_key.startswith("'")
#         or openai_api_key.endswith("'")
#     ):
#         raise ValueError(
#             "The decrypted OpenAI API key must not "
#             "contain quotation marks."
#         )

#     if not openai_api_key.startswith(
#         ("sk-", "sk-proj-")
#     ):
#         raise ValueError(
#             "The decrypted MongoDB value does not "
#             "look like an OpenAI API key."
#         )

#     # Safe diagnostic information.
#     # Never print the actual API key.
#     print(
#         "OpenAI API key loaded from MongoDB:",
#         {
#             "present": True,
#             "length": len(openai_api_key),
#             "projectKey": openai_api_key.startswith(
#                 "sk-proj-"
#             ),
#         },
#     )

#     return openai_api_key

# def create_llm() -> Any:
#     """
#     Create the configured LangChain LLM.

#     Supported LLM_PROVIDER values:
#         openai
#         mistral
#         groq
#     """

#     provider = get_required_environment_value(
#         "LLM_PROVIDER"
#     ).lower()

#     try:
#         temperature = float(
#             os.getenv(
#                 "LLM_TEMPERATURE",
#                 "0.3",
#             )
#         )
#     except ValueError as exc:
#         raise ValueError(
#             "LLM_TEMPERATURE must be a valid number."
#         ) from exc

#     if provider == "mistral":
#         return ChatMistralAI(
#             model=get_required_environment_value(
#                 "MISTRAL_MODEL"
#             ),
#             api_key=get_required_environment_value(
#                 "MISTRAL_API_KEY"
#             ),
#             temperature=temperature,
#             timeout=600,
#         )

#     if provider == "openai":
#         return ChatOpenAI(
#             model=get_required_environment_value(
#                 "OPENAI_MODEL"
#             ),
#             api_key=get_openai_api_key(),
#             temperature=temperature,
#         )

#     if provider == "groq":
#         return ChatGroq(
#             model=get_required_environment_value(
#                 "GROQ_MODEL"
#             ),
#             api_key=get_required_environment_value(
#                 "GROQ_API_KEY"
#             ),
#             temperature=temperature,
#         )

#     raise ValueError(
#         f"Unsupported LLM_PROVIDER: {provider}. "
#         "Supported providers are openai, mistral and groq."
#     )


from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI

from app.infrastructure.secrets import SecretManager


load_dotenv()


def get_required_environment_value(
    variable_name: str,
) -> str:
    """Read and validate a required environment variable."""

    value = os.getenv(variable_name)

    if value is None or not value.strip():
        raise ValueError(
            f"{variable_name} is missing in the .env file"
        )

    return value.strip()


def print_secret_source_configuration() -> None:
    """
    Print safe MongoDB secret-source diagnostics.

    This function never prints:
    - the encrypted Security value
    - the decrypted OpenAI API key
    - the Swagger bearer token
    """

    secret_database = (
        os.getenv("SECRET_DB")
        or os.getenv("SECRET_DATABASE")
        or os.getenv("MONGO_DATABASE")
        or ""
    ).strip()

    secret_collection = (
        os.getenv("SECRET_COLLECTION")
        or os.getenv("SECRET_COLLECTION_NAME")
        or ""
    ).strip()

    secret_object_id = (
        os.getenv("OBJECT_ID")
        or os.getenv("SECRET_OBJECT_ID")
        or ""
    ).strip()

    print(
        "OpenAI secret MongoDB configuration:",
        {
            "database": (
                secret_database
                if secret_database
                else "NOT_CONFIGURED"
            ),
            "collection": (
                secret_collection
                if secret_collection
                else "NOT_CONFIGURED"
            ),
            "objectId": (
                secret_object_id
                if secret_object_id
                else "NOT_CONFIGURED"
            ),
        },
    )


def get_openai_api_key() -> str:
    """
    Read and decrypt the OpenAI API key from MongoDB.

    The MongoDB document is selected by SecretManager.
    The Security field must contain an encrypted OpenAI API key.

    This function prints only safe diagnostic information.
    It never prints the actual encrypted or decrypted key.
    """

    print_secret_source_configuration()

    print(
        "Starting encrypted OpenAI key lookup "
        "through SecretManager."
    )

    try:
        with SecretManager() as secret_manager:
            openai_api_key = secret_manager.get_secret(
                field_name="Security"
            )

    except Exception as exc:
        print(
            "OpenAI key lookup or decryption failed:",
            {
                "errorType": type(exc).__name__,
                "message": str(exc),
            },
        )
        raise

    openai_api_key = str(
        openai_api_key or ""
    ).strip()

    if not openai_api_key:
        raise ValueError(
            "The decrypted OpenAI API key is empty."
        )

    if openai_api_key.lower().startswith("bearer "):
        raise ValueError(
            "The decrypted OpenAI API key must not "
            "contain the 'Bearer ' prefix."
        )

    if (
        openai_api_key.startswith('"')
        or openai_api_key.endswith('"')
        or openai_api_key.startswith("'")
        or openai_api_key.endswith("'")
    ):
        raise ValueError(
            "The decrypted OpenAI API key must not "
            "contain quotation marks."
        )

    if not openai_api_key.startswith(
        ("sk-", "sk-proj-")
    ):
        raise ValueError(
            "The decrypted MongoDB value does not "
            "look like an OpenAI API key."
        )

    print(
        "OpenAI API key loaded and decrypted "
        "from MongoDB:",
        {
            "present": True,
            "length": len(openai_api_key),
            "projectKey": openai_api_key.startswith(
                "sk-proj-"
            ),
            "startsWithExpectedPrefix": (
                openai_api_key.startswith(
                    ("sk-", "sk-proj-")
                )
            ),
        },
    )

    return openai_api_key


def create_llm() -> Any:
    """
    Create the configured LangChain LLM.

    Supported LLM_PROVIDER values:
        openai
        mistral
        groq
    """

    provider = get_required_environment_value(
        "LLM_PROVIDER"
    ).lower()

    print(
        "Creating configured LLM:",
        {
            "provider": provider,
        },
    )

    try:
        temperature = float(
            os.getenv(
                "LLM_TEMPERATURE",
                "0.3",
            )
        )

    except ValueError as exc:
        raise ValueError(
            "LLM_TEMPERATURE must be a valid number."
        ) from exc

    if provider == "mistral":
        mistral_model = (
            get_required_environment_value(
                "MISTRAL_MODEL"
            )
        )

        mistral_api_key = (
            get_required_environment_value(
                "MISTRAL_API_KEY"
            )
        )

        print(
            "Mistral configuration loaded:",
            {
                "model": mistral_model,
                "apiKeyPresent": bool(
                    mistral_api_key
                ),
                "apiKeyLength": len(
                    mistral_api_key
                ),
            },
        )

        return ChatMistralAI(
            model=mistral_model,
            api_key=mistral_api_key,
            temperature=temperature,
            timeout=600,
        )

    if provider == "openai":
        openai_model = (
            get_required_environment_value(
                "OPENAI_MODEL"
            )
        )

        print(
            "OpenAI LLM configuration:",
            {
                "model": openai_model,
            },
        )

        return ChatOpenAI(
            model=openai_model,
            api_key=get_openai_api_key(),
            temperature=temperature,
        )

    if provider == "groq":
        groq_model = (
            get_required_environment_value(
                "GROQ_MODEL"
            )
        )

        groq_api_key = (
            get_required_environment_value(
                "GROQ_API_KEY"
            )
        )

        print(
            "Groq configuration loaded:",
            {
                "model": groq_model,
                "apiKeyPresent": bool(
                    groq_api_key
                ),
                "apiKeyLength": len(
                    groq_api_key
                ),
            },
        )

        return ChatGroq(
            model=groq_model,
            api_key=groq_api_key,
            temperature=temperature,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER: {provider}. "
        "Supported providers are openai, mistral and groq."
    )
    