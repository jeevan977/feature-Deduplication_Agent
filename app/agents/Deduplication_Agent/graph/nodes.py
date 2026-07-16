

# from __future__ import annotations

# import asyncio
# import logging
# import time
# from typing import Any

# from app.infrastructure.token_usage import (
#     TokenUsageService,
# )

# from app.agents.Deduplication_Agent.graph.agent_state import (
#     DeduplicationState,
# )
# from app.agents.Deduplication_Agent.utils.helper import (
#     build_deduplication_prompt,
#     parse_llm_response,
#     validate_deduplication_result,
# )


# logger = logging.getLogger(__name__)


# async def prepare_prompt_node(
#     state: DeduplicationState,
# ) -> dict[str, Any]:
#     """
#     Create the deduplication prompt.
#     """

#     prompt = build_deduplication_prompt(
#         raw_requirements=state.get(
#             "raw_requirements",
#             [],
#         ),
#         context=state.get(
#             "context",
#             {},
#         ),
#     )

#     return {
#         "prompt": prompt,
#         "error": None,
#     }


# async def invoke_llm(
#     llm: Any,
#     prompt: str,
# ) -> Any:
#     """
#     Invoke asynchronous or synchronous LangChain LLMs.
#     """

#     if hasattr(llm, "ainvoke"):
#         return await llm.ainvoke(prompt)

#     if hasattr(llm, "invoke"):
#         return await asyncio.to_thread(
#             llm.invoke,
#             prompt,
#         )

#     raise TypeError(
#         "Configured LLM does not support "
#         "invoke() or ainvoke()."
#     )


# async def log_llm_token_usage(
#     response: Any,
#     state: DeduplicationState,
#     duration: float,
# ) -> None:
#     """
#     Extract token usage and send the complete
#     usage-log payload.

#     The bearer token comes dynamically from the
#     API request and is used only for token logging.
#     """

#     usage = (
#         TokenUsageService.extract_token_usage(
#             response
#         )
#     )

#     bearer_token = state.get(
#         "bearer_token"
#     )

#     context = state.get(
#         "context",
#         {},
#     ) or {}

#     correlation_id = (
#         state.get("correlation_id")
#         or ""
#     )

#     company_id = (
#         context.get("companyId")
#         or context.get("CompanyId")
#         or context.get("company_id")
#         or ""
#     )

#     tender_id = (
#         context.get("tenderId")
#         or context.get("TenderId")
#         or context.get("tender_id")
#         or ""
#     )

#     deduplication_id = (
#         context.get("deduplicationId")
#         or context.get("DeduplicationId")
#         or context.get("runId")
#         or correlation_id
#         or ""
#     )

#     source_ids = (
#         context.get("sourceIds")
#         or context.get("SourceIds")
#         or context.get("sourceDocumentIds")
#         or context.get("SourceDocumentIds")
#         or []
#     )

#     if not isinstance(
#         source_ids,
#         (list, tuple, set),
#     ):
#         source_ids = [source_ids]

#     source_ids = [
#         str(source_id)
#         for source_id in source_ids
#         if source_id is not None
#         and str(source_id).strip()
#     ]

#     payload = {
#         "applicationName": (
#             context.get("applicationName")
#             or "Requirement Deduplication"
#         ),

#         "sourceIds": source_ids,

#         "runId": str(
#             deduplication_id
#         ),

#         "userId": str(
#             context.get("userId")
#             or context.get("UserId")
#             or ""
#         ),

#         "purpose": (
#             context.get("purpose")
#             or "Requirement Deduplication"
#         ),

#         "method": (
#             context.get("method")
#             or "ainvoke"
#         ),

#         "agentName": (
#             context.get("agentName")
#             or "Requirement Deduplication Agent"
#         ),

#         "usageType": (
#             context.get("usageType")
#             or "LLM"
#         ),

#         "inputToken": usage.get(
#             "input_tokens",
#             0,
#         ),

#         "outputToken": usage.get(
#             "output_tokens",
#             0,
#         ),

#         "totalTokens": usage.get(
#             "total_tokens",
#             0,
#         ),

#         "model": usage.get(
#             "model",
#             "",
#         ),

#         "duration": round(
#             duration,
#             3,
#         ),

#         "cost": {
#             "currency": (
#                 context.get("currency")
#                 or "USD"
#             ),
#             "value": context.get(
#                 "costValue",
#                 0,
#             ),
#         },

#         "companyId": str(
#             company_id
#         ),

#         "tenderId": str(
#             tender_id
#         ),

#         "projectId": str(
#             context.get("projectId")
#             or context.get("ProjectId")
#             or ""
#         ),
#     }

#     print(
#         "Token logging state:",
#         {
#             "bearerTokenPresent": bool(
#                 bearer_token
#             ),
#             "bearerTokenLength": (
#                 len(bearer_token)
#                 if bearer_token
#                 else 0
#             ),
#             "companyId": company_id,
#             "tenderId": tender_id,
#             "runId": deduplication_id,
#             "duration": round(
#                 duration,
#                 3,
#             ),
#             "usage": usage,
#         },
#     )

#     result = await TokenUsageService.log_usage(
#         payload=payload,
#         bearer_token=bearer_token,
#     )

#     if not result.get(
#         "success",
#         False,
#     ):
#         print(
#             "Token usage API logging failed:",
#             result,
#         )


# async def deduplicate_requirements_node(
#     state: DeduplicationState,
#     llm: Any,
# ) -> dict[str, Any]:
#     """
#     Invoke the LLM and parse the deduplication output.
#     """

#     prompt = state.get("prompt")

#     if not prompt:
#         raise ValueError(
#             "Deduplication prompt is missing."
#         )

#     agent_start_time = time.perf_counter()

#     llm_response = await invoke_llm(
#         llm=llm,
#         prompt=prompt,
#     )

#     parsed_result = parse_llm_response(
#         llm_response
#     )

#     agent_duration = (
#         time.perf_counter()
#         - agent_start_time
#     )

#     # Log the actual LLM agent execution duration.
#     await log_llm_token_usage(
#         response=llm_response,
#         state=state,
#         duration=agent_duration,
#     )

#     return {
#         "llm_response": llm_response,
#         "result": parsed_result,
#     }


# async def validate_result_node(
#     state: DeduplicationState,
# ) -> dict[str, Any]:
#     """
#     Validate the LLM deduplication output.
#     """

#     validated_result = (
#         validate_deduplication_result(
#             result=state.get(
#                 "result",
#                 {},
#             ),
#             raw_requirements=state.get(
#                 "raw_requirements",
#                 [],
#             ),
#         )
#     )

#     return {
#         "result": validated_result,
#     }





from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.infrastructure.token_usage import (
    TokenUsageService,
)

from app.agents.Deduplication_Agent.graph.agent_state import (
    DeduplicationState,
)
from app.utils.helpers import (
    build_deduplication_prompt,
    parse_llm_response,
    validate_deduplication_result,
)


logger = logging.getLogger(__name__)


async def prepare_prompt_node(
    state: DeduplicationState,
) -> dict[str, Any]:
    """
    Create the deduplication prompt.
    """

    prompt = build_deduplication_prompt(
        raw_requirements=state.get(
            "raw_requirements",
            [],
        ),
        context=state.get(
            "context",
            {},
        ),
    )

    return {
        "prompt": prompt,
        "error": None,
    }


async def invoke_llm(
    llm: Any,
    prompt: str,
) -> Any:
    """
    Invoke asynchronous or synchronous LangChain LLMs.
    """

    if hasattr(llm, "ainvoke"):
        return await llm.ainvoke(prompt)

    if hasattr(llm, "invoke"):
        return await asyncio.to_thread(
            llm.invoke,
            prompt,
        )

    raise TypeError(
        "Configured LLM does not support "
        "invoke() or ainvoke()."
    )


async def log_llm_token_usage(
    response: Any,
    state: DeduplicationState,
    duration: float,
) -> None:
    """
    Extract token usage and send the complete
    usage-log payload.

    The bearer token comes dynamically from the
    API request and is used only for token logging.
    """

    usage = (
        TokenUsageService.extract_token_usage(
            response
        )
    )

    bearer_token = state.get(
        "bearer_token"
    )

    context = state.get(
        "context",
        {},
    ) or {}

    correlation_id = (
        state.get("correlation_id")
        or ""
    )

    company_id = (
        context.get("companyId")
        or context.get("CompanyId")
        or context.get("company_id")
        or ""
    )

    tender_id = (
        context.get("tenderId")
        or context.get("TenderId")
        or context.get("tender_id")
        or ""
    )

    deduplication_id = (
        context.get("deduplicationId")
        or context.get("DeduplicationId")
        or context.get("runId")
        or correlation_id
        or ""
    )

    source_ids = (
        context.get("sourceIds")
        or context.get("SourceIds")
        or context.get("sourceDocumentIds")
        or context.get("SourceDocumentIds")
        or []
    )

    if not isinstance(
        source_ids,
        (list, tuple, set),
    ):
        source_ids = [source_ids]

    source_ids = [
        str(source_id)
        for source_id in source_ids
        if source_id is not None
        and str(source_id).strip()
    ]

    payload = {
        "applicationName": (
            context.get("applicationName")
            or "Requirement Deduplication"
        ),

        "sourceIds": source_ids,

        "runId": str(
            deduplication_id
        ),

        "userId": str(
            context.get("userId")
            or context.get("UserId")
            or ""
        ),

        "purpose": (
            context.get("purpose")
            or "Requirement Deduplication"
        ),

        "method": (
            context.get("method")
            or "ainvoke"
        ),

        "agentName": (
            context.get("agentName")
            or "Requirement Deduplication Agent"
        ),

        "usageType": (
            context.get("usageType")
            or "LLM"
        ),

        "inputToken": usage.get(
            "input_tokens",
            0,
        ),

        "outputToken": usage.get(
            "output_tokens",
            0,
        ),

        "totalTokens": usage.get(
            "total_tokens",
            0,
        ),

        "model": usage.get(
            "model",
            "",
        ),

        "duration": round(
            duration,
            3,
        ),

        "cost": {
            "currency": (
                context.get("currency")
                or "USD"
            ),
            "value": context.get(
                "costValue",
                0,
            ),
        },

        "companyId": str(
            company_id
        ),

        "tenderId": str(
            tender_id
        ),

        "projectId": str(
            context.get("projectId")
            or context.get("ProjectId")
            or ""
        ),
    }

    print(
        "Token logging state:",
        {
            "bearerTokenPresent": bool(
                bearer_token
            ),
            "bearerTokenLength": (
                len(bearer_token)
                if bearer_token
                else 0
            ),
            "companyId": company_id,
            "tenderId": tender_id,
            "runId": deduplication_id,
            "duration": round(
                duration,
                3,
            ),
            "usage": usage,
        },
    )

    result = await TokenUsageService.log_usage(
        payload=payload,
        bearer_token=bearer_token,
    )

    if not result.get(
        "success",
        False,
    ):
        print(
            "Token usage API logging failed:",
            result,
        )


async def deduplicate_requirements_node(
    state: DeduplicationState,
    llm: Any,
) -> dict[str, Any]:
    """
    Invoke the LLM and parse the deduplication output.
    """

    prompt = state.get("prompt")

    if not prompt:
        raise ValueError(
            "Deduplication prompt is missing."
        )

    agent_start_time = time.perf_counter()

    llm_response = await invoke_llm(
        llm=llm,
        prompt=prompt,
    )

    parsed_result = parse_llm_response(
        llm_response
    )

    agent_duration = (
        time.perf_counter()
        - agent_start_time
    )

    # Log the actual LLM agent execution duration.
    await log_llm_token_usage(
        response=llm_response,
        state=state,
        duration=agent_duration,
    )

    return {
        "llm_response": llm_response,
        "result": parsed_result,
    }


async def validate_result_node(
    state: DeduplicationState,
) -> dict[str, Any]:
    """
    Validate the LLM deduplication output.
    """

    validated_result = (
        validate_deduplication_result(
            result=state.get(
                "result",
                {},
            ),
            raw_requirements=state.get(
                "raw_requirements",
                [],
            ),
        )
    )

    return {
        "result": validated_result,
    }