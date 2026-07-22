
from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)


def clean_bearer_token(
    token: str | None,
) -> str | None:
    """
    Clean the bearer token received dynamically
    through the API request.
    """

    if not token:
        return None

    cleaned_token = token.strip()

    if cleaned_token.lower().startswith("bearer "):
        cleaned_token = cleaned_token[7:].strip()

    return cleaned_token or None


class TokenUsageService:
    """
    Shared token-usage and cost service.

    Prices are USD per 1,000,000 tokens. Keep this table aligned
    with the exact model configured in the environment.
    """

    MODEL_PRICING_PER_MILLION: dict[
        str,
        dict[str, float],
    ] = {
        # Mistral models used by the project.
        "mistral-large-latest": {
            "input": 0.50,
            "output": 1.50,
        },
        "mistral-large-2512": {
            "input": 0.50,
            "output": 1.50,
        },

        # OpenAI chat models supported by the project.
        "gpt-4o-mini": {
            "input": 0.15,
            "output": 0.60,
        },
        "gpt-4o-mini-2024-07-18": {
            "input": 0.15,
            "output": 0.60,
        },
        "gpt-4.1-mini": {
            "input": 0.40,
            "output": 1.60,
        },
        "gpt-4.1-mini-2025-04-14": {
            "input": 0.40,
            "output": 1.60,
        },

        # Used by the Evidence Summary Agent for Qdrant queries.
        # This entry is available for embedding-usage logs when
        # exact embedding token counts are supplied.
        "text-embedding-3-small": {
            "input": 0.02,
            "output": 0.0,
        },
    }

    @staticmethod
    def _get_value(
        source: Any,
        key: str,
        default: Any = None,
    ) -> Any:
        if isinstance(source, dict):
            return source.get(key, default)

        return getattr(source, key, default)

    @staticmethod
    def _to_int(
        value: Any,
        default: int = 0,
    ) -> int:
        try:
            return int(value or default)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _to_float(
        value: Any,
        default: float = 0.0,
    ) -> float:
        try:
            return float(value or default)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _calculate_cost(
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """
        Calculate the model cost in USD.

        The input/output rates are read from
        MODEL_PRICING_PER_MILLION. Unknown models return zero rather
        than using an incorrect provider price.
        """

        normalized_model = str(
            model or ""
        ).strip().lower()

        pricing = (
            TokenUsageService
            .MODEL_PRICING_PER_MILLION
            .get(normalized_model)
        )

        if pricing is None:
            logger.warning(
                "Token cost was not calculated because "
                "pricing is not configured for model: %s",
                normalized_model or "<empty>",
            )
            return 0.0

        normalized_input_tokens = (
            TokenUsageService._to_int(
                input_tokens
            )
        )

        normalized_output_tokens = (
            TokenUsageService._to_int(
                output_tokens
            )
        )

        input_rate = (
            TokenUsageService._to_float(
                pricing.get("input", 0)
            )
        )

        output_rate = (
            TokenUsageService._to_float(
                pricing.get("output", 0)
            )
        )

        input_cost = (
            normalized_input_tokens
            / 1_000_000
        ) * input_rate

        output_cost = (
            normalized_output_tokens
            / 1_000_000
        ) * output_rate

        return round(
            input_cost + output_cost,
            8,
        )

    @staticmethod
    def resolve_configured_model_name() -> str:
        """
        Return the model selected in .env.

        This is used only when a provider response does not include
        model metadata.
        """

        provider = str(
            os.getenv("LLM_PROVIDER", "")
            or ""
        ).strip().lower()

        environment_variable_by_provider = {
            "openai": "OPENAI_MODEL",
            "mistral": "MISTRAL_MODEL",
            "groq": "GROQ_MODEL",
        }

        environment_variable = (
            environment_variable_by_provider.get(
                provider,
                "",
            )
        )

        if not environment_variable:
            return ""

        return str(
            os.getenv(
                environment_variable,
                "",
            )
            or ""
        ).strip()

    @staticmethod
    def _to_source_ids(
        value: Any,
    ) -> list[dict[str, str]]:
        """
        Convert source IDs into the object structure expected
        by the .NET AiUsageSourceId model.
        """

        if value is None:
            return []

        if not isinstance(
            value,
            (list, tuple, set),
        ):
            value = [value]

        source_items: list[dict[str, str]] = []

        for item in value:
            if item is None:
                continue

            # Preserve already-correct source objects.
            if isinstance(item, dict):
                source_id = (
                    item.get("sourceId")
                    or item.get("SourceId")
                    or item.get("id")
                    or item.get("Id")
                )

                if source_id:
                    source_items.append(
                        {
                            "sourceId": str(
                                source_id
                            ).strip()
                        }
                    )

                continue

            source_id = str(item).strip()

            if source_id:
                source_items.append(
                    {
                        "sourceId": source_id
                    }
                )

        return source_items

    @staticmethod
    def extract_token_usage(
        response: Any,
    ) -> dict[str, Any]:
        """
        Extract token usage information from common
        LangChain and model response structures.
        """

        response_metadata = (
            TokenUsageService._get_value(
                response,
                "response_metadata",
                {},
            )
            or {}
        )

        usage_metadata = (
            TokenUsageService._get_value(
                response,
                "usage_metadata",
                None,
            )
            or response_metadata.get("token_usage")
            or response_metadata.get("usage")
            or {}
        )

        input_tokens = (
            TokenUsageService._get_value(
                usage_metadata,
                "input_tokens",
                None,
            )
        )

        if input_tokens is None:
            input_tokens = (
                TokenUsageService._get_value(
                    usage_metadata,
                    "prompt_tokens",
                    0,
                )
            )

        output_tokens = (
            TokenUsageService._get_value(
                usage_metadata,
                "output_tokens",
                None,
            )
        )

        if output_tokens is None:
            output_tokens = (
                TokenUsageService._get_value(
                    usage_metadata,
                    "completion_tokens",
                    0,
                )
            )

        total_tokens = (
            TokenUsageService._get_value(
                usage_metadata,
                "total_tokens",
                None,
            )
        )

        if total_tokens is None:
            total_tokens = (
                TokenUsageService._to_int(
                    input_tokens
                )
                + TokenUsageService._to_int(
                    output_tokens
                )
            )

        model_name = (
            response_metadata.get("model_name")
            or response_metadata.get("model")
            or TokenUsageService._get_value(
                response,
                "model_name",
                "",
            )
            or TokenUsageService.resolve_configured_model_name()
            or ""
        )

        return {
            "input_tokens": (
                TokenUsageService._to_int(
                    input_tokens
                )
            ),
            "output_tokens": (
                TokenUsageService._to_int(
                    output_tokens
                )
            ),
            "total_tokens": (
                TokenUsageService._to_int(
                    total_tokens
                )
            ),
            "model": str(model_name),
        }

    @staticmethod
    def resolve_bearer_token(
        bearer_token: str | None,
    ) -> str | None:
        """
        Use only the dynamic bearer token received
        through the current API call.
        """

        return clean_bearer_token(
            bearer_token
        )

    @staticmethod
    def build_request_payload(
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build the exact payload required by the
        token-usage API.
        """

        cost = payload.get("cost")

        if not isinstance(cost, dict):
            cost = {}

        currency = (
            cost.get("currency")
            or payload.get("currency")
            or "USD"
        )

        supplied_cost_value = (
            cost.get("value")
            if cost.get("value") is not None
            else payload.get("costValue")
        )

        input_tokens = (
            TokenUsageService._to_int(
                payload.get(
                    "inputToken",
                    payload.get(
                        "input_tokens",
                        0,
                    ),
                )
            )
        )

        output_tokens = (
            TokenUsageService._to_int(
                payload.get(
                    "outputToken",
                    payload.get(
                        "output_tokens",
                        0,
                    ),
                )
            )
        )

        total_tokens = (
            TokenUsageService._to_int(
                payload.get(
                    "totalTokens",
                    payload.get(
                        "total_tokens",
                        0,
                    ),
                )
            )
        )

        model = str(
            payload.get("model", "")
            or ""
        )

        supplied_cost = (
            TokenUsageService._to_float(
                supplied_cost_value
            )
            if supplied_cost_value is not None
            else 0.0
        )

        if supplied_cost > 0:
            cost_value = supplied_cost
        else:
            cost_value = (
                TokenUsageService._calculate_cost(
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )

        return {
            "applicationName": str(
                payload.get(
                    "applicationName",
                    "Requirement Deduplication",
                )
                or "Requirement Deduplication"
            ),

            "sourceIds": (
                TokenUsageService._to_source_ids(
                    payload.get("sourceIds")
                )
            ),

            "runId": str(
                payload.get("runId", "")
                or ""
            ),

            "userId": str(
                payload.get("userId", "")
                or ""
            ),

            "purpose": str(
                payload.get(
                    "purpose",
                    "Requirement Deduplication",
                )
                or "Requirement Deduplication"
            ),

            "method": str(
                payload.get(
                    "method",
                    "ainvoke",
                )
                or "ainvoke"
            ),

            "agentName": str(
                payload.get(
                    "agentName",
                    "Requirement Deduplication Agent",
                )
                or "Requirement Deduplication Agent"
            ),

            "usageType": str(
                payload.get(
                    "usageType",
                    "LLM",
                )
                or "LLM"
            ),

            "inputToken": input_tokens,

            "outputToken": output_tokens,

            "totalTokens": total_tokens,

            "model": model,

            "duration": (
                TokenUsageService._to_float(
                    payload.get(
                        "duration",
                        0,
                    )
                )
            ),

            "cost": {
                "currency": str(
                    currency
                    or "USD"
                ),
                "value": round(
                    TokenUsageService._to_float(
                        cost_value
                    ),
                    6,
                ),
            },

            "companyId": str(
                payload.get(
                    "companyId",
                    "",
                )
                or ""
            ),

            "tenderId": str(
                payload.get(
                    "tenderId",
                    "",
                )
                or ""
            ),

            "projectId": str(
                payload.get(
                    "projectId",
                    "",
                )
                or ""
            ),
        }

    @staticmethod
    async def log_usage(
        payload: dict[str, Any],
        bearer_token: str | None = None,
    ) -> dict[str, Any]:
        """
        Send token usage details to the configured API.

        Failure to log token usage does not stop the
        deduplication agent.
        """

        api_url = (
            os.getenv("AI_USAGE_LOG_API")
            or os.getenv("Token_UASAGE")
            or ""
        ).strip()

        if not api_url:
            message = (
                "Token usage logging skipped because "
                "AI_USAGE_LOG_API is not configured."
            )

            logger.warning(message)

            return {
                "success": False,
                "status_code": 500,
                "message": message,
            }

        token = (
            TokenUsageService.resolve_bearer_token(
                bearer_token
            )
        )

        if not token:
            message = (
                "Token usage logging skipped because "
                "no bearer token was supplied in the "
                "API request."
            )

            logger.warning(message)

            return {
                "success": False,
                "status_code": 401,
                "message": message,
            }

        request_payload = (
            TokenUsageService.build_request_payload(
                payload
            )
        )

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }

       

        print(
            "Token usage HTTP request:",
            {
                "urlConfigured": bool(api_url),
                "authorizationPresent": True,
                "tokenLength": len(token),
                "payload": request_payload,
                "formattedCost": format(
                    request_payload.get(
                        "cost",
                        {},
                    ).get(
                        "value",
                        0,
                    ),
                    ".6f",
                ),
            },
        )

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(60.0)
            ) as client:
                response = await client.post(
                    api_url,
                    json=request_payload,
                    headers=headers,
                )

            if not response.is_success:
                print(
                    "Token usage logging failed:",
                    {
                        "statusCode": (
                            response.status_code
                        ),
                        "response": response.text,
                    },
                )

                return {
                    "success": False,
                    "status_code": (
                        response.status_code
                    ),
                    "message": response.text,
                }

            response_data: Any = None

            if response.content:
                try:
                    response_data = (
                        response.json()
                    )
                except ValueError:
                    response_data = (
                        response.text
                    )

            print(
                "Token usage log sent successfully:",
                response.status_code,
            )

            return {
                "success": True,
                "status_code": (
                    response.status_code
                ),
                "response": response_data,
            }

        except httpx.TimeoutException as exc:
            message = (
                "Token usage logging timed out: "
                f"{exc}"
            )

            logger.warning(message)

            return {
                "success": False,
                "status_code": 408,
                "message": message,
            }

        except httpx.HTTPError as exc:
            message = (
                "Token usage logging request failed: "
                f"{exc}"
            )

            logger.warning(message)

            return {
                "success": False,
                "status_code": 500,
                "message": message,
            }

        except Exception as exc:
            logger.exception(
                "Unexpected token usage logging error"
            )

            return {
                "success": False,
                "status_code": 500,
                "message": str(exc),
            }
