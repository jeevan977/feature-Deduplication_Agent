
# from __future__ import annotations

# from typing import Any, TypedDict


# class DeduplicationState(
#     TypedDict,
#     total=False,
# ):
#     raw_requirements: list[
#         dict[str, Any]
#     ]

#     context: dict[str, Any]

#     bearer_token: str | None

#     correlation_id: str | None

#     prompt: str

#     llm_response: Any

#     result: dict[str, Any]

#     error: str | None



from __future__ import annotations

from typing import Any, TypedDict


class DeduplicationState(
    TypedDict,
    total=False,
):
    raw_requirements: list[
        dict[str, Any]
    ]

    context: dict[str, Any]

    bearer_token: str | None

    correlation_id: str | None

    prompt: str

    llm_response: Any

    result: dict[str, Any]

    error: str | None

    