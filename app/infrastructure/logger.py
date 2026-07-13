# import os
# import json
# import uuid
# import time
# import requests

# from datetime import datetime, timezone
# from typing import Any, Optional, Dict
# from dotenv import load_dotenv


# load_dotenv()


# class Logging:
#     def __init__(self,agent_name: str,source_module: str,timeout: int = 10,) -> None:

#         self.base_url = os.getenv("LOG_URL")

#         if not self.base_url:
#             raise ValueError(
#                 "LOG_URL is not set in environment variables."
#             )

#         self.agent_name = agent_name
#         self.source_module = source_module
#         self.timeout = timeout

#     def log(
#         self,
#         message: str,
#         event_type: str,
#         is_success: bool = True,
#         duration_ms: int = 0,
#         start_time: Optional[str] = None,
#         end_time: Optional[str] = None,
#         payload: Optional[Dict[str, Any]] = None,
#         correlation_id: Optional[str] = None) -> None:

#         log_payload = {
#             "agentName": self.agent_name,
#             "message": message,
#             "eventType": event_type,
#             "sourceModule": self.source_module,
#             "isSuccess": is_success,
#             "durationMs": duration_ms,
#             "startTime": start_time,
#             "endTime": end_time,
#             "payloadJson": json.dumps(
#                 payload or {},
#                 default=str,
#             ),
#             "correlationId": (
#                 correlation_id or str(uuid.uuid4())
#             ),
#         }

#         try:
#             response = requests.post(
#                 self.base_url,
#                 json=log_payload,
#                 timeout=self.timeout,
#             )

#             response.raise_for_status()

#         except requests.RequestException as exc:
#             print(f"Enterprise logging failed: {exc}")

#     def start(
#         self,
#         message: str,
#         event_type: str,
#         correlation_id: Optional[str] = None) -> Dict[str, Any]:
#         """
#         Start tracking an operation.

#         Returns a tracking token that must be passed to end().
#         """

#         return {
#             "message": message,
#             "event_type": event_type,
#             "correlation_id": (
#                 correlation_id or str(uuid.uuid4())
#             ),
#             "start_perf": time.perf_counter(),
#             "start_time": datetime.now(
#                 timezone.utc
#             ).isoformat(),
#         }

#     def end(
#         self,
#         tracking_token: Dict[str, Any],
#         is_success: bool = True,
#         payload: Optional[Dict[str, Any]] = None,
#         message: Optional[str] = None,
#         event_type: Optional[str] = None,
#     ) -> None:
#         """
#         Finish tracking and send the enterprise log.
#         """

#         end_perf = time.perf_counter()
#         end_time = datetime.now(timezone.utc).isoformat()

#         duration_ms = round(
#             (
#                 end_perf
#                 - tracking_token["start_perf"]
#             )
#             * 1000
#         )

#         self.log(
#             message=message or tracking_token["message"],
#             event_type=(
#                 event_type
#                 or tracking_token["event_type"]
#             ),
#             is_success=is_success,
#             duration_ms=duration_ms,
#             start_time=tracking_token["start_time"],
#             end_time=end_time,
#             payload=payload,
#             correlation_id=tracking_token[
#                 "correlation_id"
#             ],
#         )



from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import requests
from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)


def clean_bearer_token(
    token: str | None,
) -> str | None:
    if not token:
        return None

    cleaned_token = token.strip()

    if cleaned_token.lower().startswith("bearer "):
        cleaned_token = cleaned_token[7:].strip()

    return cleaned_token or None


def create_correlation_id(
    correlation_id: str | None,
) -> str:
    """
    Enterprise logging APIs commonly expect a UUID.

    MongoDB ObjectIds are retained inside payloadJson,
    while correlationId is kept as a valid UUID.
    """

    if correlation_id:
        try:
            return str(uuid.UUID(str(correlation_id)))
        except ValueError:
            pass

    return str(uuid.uuid4())


class Logging:
    def __init__(
        self,
        agent_name: str,
        source_module: str,
        timeout: int = 30,
    ) -> None:
        self.base_url = (
            os.getenv("LOG_URL") or ""
        ).strip()

        self.agent_name = agent_name
        self.source_module = source_module
        self.timeout = timeout

    def resolve_bearer_token(
        self,
        bearer_token: str | None,
    ) -> str | None:
        """
        Priority:

        1. Token received by the API request
        2. LOG_API_BEARER_TOKEN from .env
        3. SERVICE_BEARER_TOKEN from .env
        """

        token = (
            bearer_token
            or os.getenv("LOG_API_BEARER_TOKEN")
            or os.getenv("SERVICE_BEARER_TOKEN")
        )

        return clean_bearer_token(token)

    def build_headers(
        self,
        bearer_token: str | None,
    ) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        token = self.resolve_bearer_token(
            bearer_token
        )

        if token:
            headers["Authorization"] = (
                f"Bearer {token}"
            )

        return headers

    def log(
        self,
        message: str,
        event_type: str,
        is_success: bool = True,
        duration_ms: int = 0,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        bearer_token: str | None = None,
    ) -> dict[str, Any]:
        if not self.base_url:
            message_text = (
                "Enterprise logging skipped because "
                "LOG_URL is not configured."
            )

            logger.warning(message_text)

            return {
                "success": False,
                "message": message_text,
            }

        final_correlation_id = (
            create_correlation_id(correlation_id)
        )

        log_payload = {
            "agentName": self.agent_name,
            "message": message,
            "eventType": event_type,
            "sourceModule": self.source_module,
            "isSuccess": is_success,
            "durationMs": duration_ms,
            "startTime": start_time,
            "endTime": end_time,
            "payloadJson": json.dumps(
                payload or {},
                ensure_ascii=False,
                default=str,
            ),
            "correlationId": final_correlation_id,
        }

        headers = self.build_headers(
            bearer_token
        )

        print(
            "Enterprise log request:",
            {
                "urlConfigured": bool(self.base_url),
                "authorizationPresent": (
                    "Authorization" in headers
                ),
                "eventType": event_type,
                "correlationId": final_correlation_id,
            },
        )

        try:
            response = requests.post(
                self.base_url,
                json=log_payload,
                headers=headers,
                timeout=self.timeout,
            )

            if not response.ok:
                print(
                    "Enterprise logging failed:",
                    {
                        "statusCode": response.status_code,
                        "response": response.text,
                    },
                )

                return {
                    "success": False,
                    "status_code": response.status_code,
                    "message": response.text,
                }

            print(
                "Enterprise log sent successfully:",
                response.status_code,
            )

            response_data: Any = None

            if response.content:
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = response.text

            return {
                "success": True,
                "status_code": response.status_code,
                "response": response_data,
            }

        except requests.RequestException as exc:
            logger.warning(
                "Enterprise logging request failed: %s",
                exc,
            )

            return {
                "success": False,
                "message": str(exc),
            }

        except Exception as exc:
            logger.exception(
                "Unexpected enterprise logging error"
            )

            return {
                "success": False,
                "message": str(exc),
            }

    def start(
        self,
        message: str,
        event_type: str,
        correlation_id: Optional[str] = None,
    ) -> dict[str, Any]:
        return {
            "message": message,
            "event_type": event_type,
            "correlation_id": create_correlation_id(
                correlation_id
            ),
            "start_perf": time.perf_counter(),
            "start_time": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    def end(
        self,
        tracking_token: dict[str, Any],
        is_success: bool = True,
        payload: Optional[dict[str, Any]] = None,
        message: Optional[str] = None,
        event_type: Optional[str] = None,
        bearer_token: str | None = None,
    ) -> dict[str, Any]:
        end_perf = time.perf_counter()

        end_time = datetime.now(
            timezone.utc
        ).isoformat()

        duration_ms = round(
            (
                end_perf
                - tracking_token["start_perf"]
            )
            * 1000
        )

        return self.log(
            message=(
                message
                or tracking_token["message"]
            ),
            event_type=(
                event_type
                or tracking_token["event_type"]
            ),
            is_success=is_success,
            duration_ms=duration_ms,
            start_time=tracking_token[
                "start_time"
            ],
            end_time=end_time,
            payload=payload,
            correlation_id=tracking_token[
                "correlation_id"
            ],
            bearer_token=bearer_token,
        )