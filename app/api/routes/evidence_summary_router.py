from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    status,
)
from pydantic import BaseModel, Field

from app.agents.Deduplication_Agent.Evidence_Summary_Agent import (
    RequirementEvidenceSummaryAgent,
)

# class EvidenceSummaryRequest(BaseModel):
#     """
#     Request body for the Evidence Summary Agent.

#     The agent uses CompanyId and TenderId to find the latest
#     completed Requirement Deduplication record in MongoDB.
#     The Token is used only for token-usage API logging.
#     """

#     CompanyId: str = Field(
#         ...,
#         min_length=1,
#     )
#     TenderId: str = Field(
#         ...,
#         min_length=1,
#     )
#     Token: str = Field(
#         ...,
#         min_length=1,
#     )


# router = APIRouter(
#     prefix="/evidence-summary",
#     tags=["Evidence Summary Agent"],
# )

# agent = RequirementEvidenceSummaryAgent()


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
#     status_code=status.HTTP_200_OK,
# )
# async def process_evidence_summary(
#     request: EvidenceSummaryRequest,
# ) -> dict[str, Any]:
#     """
#     Run the Evidence Summary Agent.

#     Flow:

#     1. Read the latest completed deduplication output from MongoDB.
#     2. Read its DeduplicatedRequirements records.
#     3. Search relevant company evidence chunks in Qdrant.
#     4. Generate evidence summaries through the configured LLM.
#     5. Save the result in the evidence-summary MongoDB collection.
#     """

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

#         # Never print the actual bearer token.
#         print(
#             "Evidence Summary API bearer token received:",
#             {
#                 "present": True,
#                 "length": len(bearer_token),
#             },
#         )

#         return await agent.process(
#             input_data=request,
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
#                 "Evidence summary generation failed: "
#                 f"{exc}"
#             ),
#         ) from exc


# @router.get(
#     "/{evidence_summary_id}",
# )
# async def get_evidence_summary_result(
#     evidence_summary_id: str,
# ) -> dict[str, Any]:
#     """Return a saved Evidence Summary MongoDB record by ID."""

#     result = await agent.get_by_id(
#         evidence_summary_id
#     )

#     if result is None:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=(
#                 "Evidence Summary record was not found"
#             ),
#         )

#     return result

class EvidenceSummaryRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    CompanyId: str = Field(
        ...,
        min_length=1,
    )

    TenderId: str = Field(
        ...,
        min_length=1,
    )

    IsRegenerate: bool = Field(
        default=False,
    )

    UserId: str = Field(
        ...,
        min_length=1,
        description=(
            "User identifier used in the Agent 2 "
            "token-usage log"
        ),
    )

    UserName: str = Field(
        default="",
    )

    ProjectId: str = Field(
        default="",
    )

    Token: str = Field(
        ...,
        min_length=1,
        exclude=True,
        repr=False,
        description=(
            "Bearer token used only for token-usage logging"
        ),
    )