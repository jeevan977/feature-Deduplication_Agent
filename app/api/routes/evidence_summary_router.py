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