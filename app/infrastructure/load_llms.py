
# from __future__ import annotations

# import os
# from typing import Any

# from dotenv import load_dotenv
# from langchain_groq import ChatGroq
# from langchain_mistralai import ChatMistralAI
# from langchain_openai import ChatOpenAI

# from app.utils.helpers import SecretManager


# load_dotenv()


# def get_required_environment_value(
#     variable_name: str,
# ) -> str:
#     """
#     Read and validate a required environment variable.
#     """

#     value = os.getenv(variable_name)

#     if value is None or not value.strip():
#         raise ValueError(
#             f"{variable_name} is missing in the .env file"
#         )

#     return value.strip()


# def get_openai_api_key() -> str:
#     """
#     Retrieve and decrypt the OpenAI API key from MongoDB.

#     SecretManager is created only when OpenAI is selected.
#     """

#     secret_manager = SecretManager()

#     try:
#         openai_api_key = secret_manager.get_secret(
#             field_name="Security"
#         )

#         if not openai_api_key:
#             raise ValueError(
#                 "Decrypted OpenAI API key is empty"
#             )

#         return openai_api_key

#     finally:
#         secret_manager.close()


# def create_llm() -> Any:
#     """
#     Create the configured LangChain LLM.

#     Supported providers:
#     - OpenAI
#     - Mistral
#     - Groq
#     """

#     provider = get_required_environment_value(
#         "LLM_PROVIDER"
#     ).lower()

#     temperature = float(
#         os.getenv(
#             "LLM_TEMPERATURE",
#             "0.3",
#         )
#     )

#     if provider == "mistral":
#         return ChatMistralAI(
#             model=get_required_environment_value(
#                 "MISTRAL_MODEL"
#             ),
#             api_key=get_required_environment_value(
#                 "MISTRAL_API_KEY"
#             ),
#             temperature=temperature,
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


def get_openai_api_key() -> str:
    """
    Retrieve and decrypt the OpenAI API key from MongoDB.

    SecretManager is created only when OpenAI is selected.
    This prevents MongoDB secret loading when Mistral or Groq
    is the configured provider.
    """

    with SecretManager() as secret_manager:
        openai_api_key = secret_manager.get_secret(
            field_name="Security"
        )

    if not openai_api_key:
        raise ValueError(
            "Decrypted OpenAI API key is empty"
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
        return ChatMistralAI(
            model=get_required_environment_value(
                "MISTRAL_MODEL"
            ),
            api_key=get_required_environment_value(
                "MISTRAL_API_KEY"
            ),
            temperature=temperature,
        )

    if provider == "openai":
        return ChatOpenAI(
            model=get_required_environment_value(
                "OPENAI_MODEL"
            ),
            api_key=get_openai_api_key(),
            temperature=temperature,
        )

    if provider == "groq":
        return ChatGroq(
            model=get_required_environment_value(
                "GROQ_MODEL"
            ),
            api_key=get_required_environment_value(
                "GROQ_API_KEY"
            ),
            temperature=temperature,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER: {provider}. "
        "Supported providers are openai, mistral and groq."
    )