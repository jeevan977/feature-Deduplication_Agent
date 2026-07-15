


# from __future__ import annotations

# from typing import Any

# from fastapi import (
#     APIRouter,
#     HTTPException,
#     status,
# )

# from app.agents.Deduplication_Agent.schemas.request import (
#     DeduplicationRequest,
# )
# from app.agents.Deduplication_Agent.schemas.response import (
#     DeduplicationResponse,
# )
# from app.agents.Deduplication_Agent.services.service import (
#     RequirementDeduplicationService,
# )


# router = APIRouter(
#     prefix="/requirement-deduplication",
#     tags=["Requirement Deduplication Agent"],
# )

# service = RequirementDeduplicationService()


# def clean_bearer_token(
#     token: str | None,
# ) -> str | None:
#     """
#     Clean a bearer token received in the JSON body.

#     Accepted values:

#         eyJhbGci...
#         Bearer eyJhbGci...
#     """

#     if not token:
#         return None

#     cleaned_token = token.strip()

#     if cleaned_token.lower().startswith(
#         "bearer "
#     ):
#         cleaned_token = cleaned_token[7:].strip()

#     return cleaned_token or None


# @router.post(
#     "/process",
#     response_model=DeduplicationResponse,
#     status_code=status.HTTP_200_OK,
# )
# async def process_requirement_deduplication(
#     request: DeduplicationRequest,
# ):
#     try:
#         bearer_token = clean_bearer_token(
#             request.Token
#         )

#         if not bearer_token:
#             raise HTTPException(
#                 status_code=(
#                     status.HTTP_401_UNAUTHORIZED
#                 ),
#                 detail=(
#                     "Token is required in the "
#                     "API request body."
#                 ),
#             )

#         # Never print the actual token.
#         print(
#             "API bearer token received:",
#             {
#                 "present": True,
#                 "length": len(bearer_token),
#             },
#         )

#         return await service.process(
#             request=request,
#             bearer_token=bearer_token,
#         )

#     except HTTPException:
#         raise

#     except ValueError as exc:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(exc),
#         ) from exc

#     except Exception as exc:
#         raise HTTPException(
#             status_code=(
#                 status.HTTP_500_INTERNAL_SERVER_ERROR
#             ),
#             detail=(
#                 "Requirement deduplication failed: "
#                 f"{exc}"
#             ),
#         ) from exc


# @router.get("/{deduplication_id}")
# async def get_deduplication_result(
#     deduplication_id: str,
# ) -> dict[str, Any]:
#     result = await service.get_by_id(
#         deduplication_id
#     )

#     if result is None:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=(
#                 "Deduplication record was not found"
#             ),
#         )

#     return result





# from __future__ import annotations

# from typing import Any

# from fastapi import (
#     APIRouter,
#     HTTPException,
#     status,
# )

# from app.agents.Deduplication_Agent.Evidence_Summary_Agent import (
#     RequirementEvidenceSummaryAgent,
# )
# from app.agents.Deduplication_Agent.schemas.request import (
#     DeduplicationRequest,
# )
# from app.agents.Deduplication_Agent.schemas.response import (
#     DeduplicationResponse,
# )
# from app.agents.Deduplication_Agent.services.service import (
#     RequirementDeduplicationService,
# )


# router = APIRouter(
#     prefix="/requirement-deduplication",
#     tags=["Requirement Deduplication Agent"],
# )

# service = RequirementDeduplicationService()
# evidence_summary_agent = RequirementEvidenceSummaryAgent()


# def clean_bearer_token(
#     token: str | None,
# ) -> str | None:
#     """
#     Clean a bearer token received in the JSON body.

#     Accepted values:

#         eyJhbGci...
#         Bearer eyJhbGci...
#     """

#     if not token:
#         return None

#     cleaned_token = token.strip()

#     if cleaned_token.lower().startswith(
#         "bearer "
#     ):
#         cleaned_token = cleaned_token[7:].strip()

#     return cleaned_token or None


# @router.post(
#     "/process",
#     response_model=DeduplicationResponse,
#     status_code=status.HTTP_200_OK,
# )
# async def process_requirement_deduplication(
#     request: DeduplicationRequest,
# ):
#     try:
#         bearer_token = clean_bearer_token(
#             request.Token
#         )

#         if not bearer_token:
#             raise HTTPException(
#                 status_code=(
#                     status.HTTP_401_UNAUTHORIZED
#                 ),
#                 detail=(
#                     "Token is required in the "
#                     "API request body."
#                 ),
#             )

#         # Never print the actual token.
#         print(
#             "API bearer token received:",
#             {
#                 "present": True,
#                 "length": len(bearer_token),
#             },
#         )

#         print(
#             "Starting Agent 1: "
#             "Requirement Deduplication Agent"
#         )

#         deduplication_result = await service.process(
#             request=request,
#             bearer_token=bearer_token,
#         )

#         deduplication_status = str(
#             deduplication_result.get(
#                 "Status",
#                 "",
#             )
#         ).strip()

#         if deduplication_status != "IsRegenerated":
#             raise ValueError(
#                 "Agent 1 did not complete successfully."
#             )

#         print("Agent 1 completed successfully.")

#         # Build Agent 2 input without placing the bearer
#         # token inside the normal payload.
#         evidence_input = request.model_dump(
#             mode="python",
#             exclude={"Token"},
#         )

#         deduplication_id = str(
#             deduplication_result.get(
#                 "DeduplicationId",
#                 "",
#             )
#             or ""
#         )

#         print(
#             "Starting Agent 2: "
#             "Evidence Summary Agent"
#         )

#         await evidence_summary_agent.process(
#             input_data=evidence_input,
#             bearer_token=bearer_token,
#             correlation_id=deduplication_id,
#         )

#         print("Agent 2 completed successfully.")

#         # Keep the existing API response contract.
#         # Agent 2 saves its own output in MongoDB.
#         return deduplication_result

#     except HTTPException:
#         raise

#     except ValueError as exc:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=str(exc),
#         ) from exc

#     except Exception as exc:
#         raise HTTPException(
#             status_code=(
#                 status.HTTP_500_INTERNAL_SERVER_ERROR
#             ),
#             detail=(
#                 "Requirement deduplication failed: "
#                 f"{exc}"
#             ),
#         ) from exc


# @router.get("/{deduplication_id}")
# async def get_deduplication_result(
#     deduplication_id: str,
# ) -> dict[str, Any]:
#     result = await service.get_by_id(
#         deduplication_id
#     )

#     if result is None:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=(
#                 "Deduplication record was not found"
#             ),
#         )

#     return result


from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)

from app.agents.Deduplication_Agent.Evidence_Summary_Agent import (
    RequirementEvidenceSummaryAgent,
)
from app.agents.Deduplication_Agent.schemas.request import (
    DeduplicationRequest,
)
from app.agents.Deduplication_Agent.schemas.response import (
    DeduplicationResponse,
)
from app.agents.Deduplication_Agent.services.service import (
    RequirementDeduplicationService,
)


router = APIRouter(
    prefix="/requirement-deduplication",
    tags=["Requirement Deduplication Agent"],
)

service = RequirementDeduplicationService()
evidence_summary_agent = RequirementEvidenceSummaryAgent()


def clean_bearer_token(
    token: str | None,
) -> str | None:
    """
    Clean a bearer token received in the JSON body.

    Accepted values:

        eyJhbGci...
        Bearer eyJhbGci...
    """

    if not token:
        return None

    cleaned_token = token.strip()

    if cleaned_token.lower().startswith(
        "bearer "
    ):
        cleaned_token = cleaned_token[7:].strip()

    return cleaned_token or None


@router.post(
    "/process",
    response_model=DeduplicationResponse,
    status_code=status.HTTP_200_OK,
)
async def process_requirement_deduplication(
    request: DeduplicationRequest,
):
    try:
        bearer_token = clean_bearer_token(
            request.Token
        )

        if not bearer_token:
            raise HTTPException(
                status_code=(
                    status.HTTP_401_UNAUTHORIZED
                ),
                detail=(
                    "Token is required in the "
                    "API request body."
                ),
            )

        # Never print the actual token.
        print(
            "API bearer token received:",
            {
                "present": True,
                "length": len(bearer_token),
            },
        )

        print(
            "Starting Agent 1: "
            "Requirement Deduplication Agent"
        )

        deduplication_result = await service.process(
            request=request,
            bearer_token=bearer_token,
        )

        deduplication_status = str(
            deduplication_result.get(
                "Status",
                "",
            )
            or ""
        ).strip()

        print(
            "Agent 1 returned status:",
            deduplication_status,
        )

        successful_agent_1_statuses = {
            "Completed",
            "IsRegenerated",
        }

        if (
            deduplication_status
            not in successful_agent_1_statuses
        ):
            raise ValueError(
                "Agent 1 did not complete successfully. "
                f"Returned status: "
                f"{deduplication_status or 'EMPTY'}"
            )

        print("Agent 1 completed successfully.")

        # Build Agent 2 input without placing the bearer
        # token inside the normal payload.
        evidence_input = request.model_dump(
            mode="python",
            exclude={"Token"},
        )

        deduplication_id = str(
            deduplication_result.get(
                "DeduplicationId",
                "",
            )
            or ""
        )

        print(
            "Starting Agent 2: "
            "Evidence Summary Agent"
        )

        await evidence_summary_agent.process(
            input_data=evidence_input,
            bearer_token=bearer_token,
            correlation_id=deduplication_id,
        )

        print("Agent 2 completed successfully.")

        # Keep the existing API response contract.
        # Agent 2 saves its own output in MongoDB.
        return deduplication_result

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Requirement deduplication failed: "
                f"{exc}"
            ),
        ) from exc


@router.get("/{deduplication_id}")
async def get_deduplication_result(
    deduplication_id: str,
) -> dict[str, Any]:
    result = await service.get_by_id(
        deduplication_id
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Deduplication record was not found"
            ),
        )

    return result