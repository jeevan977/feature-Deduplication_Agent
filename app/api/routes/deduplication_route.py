


from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    status,
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

        return await service.process(
            request=request,
            bearer_token=bearer_token,
        )

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