from typing import Any

from pydantic import BaseModel, Field


class DeduplicationResponse(BaseModel):
    DeduplicationId: str

    Status: str

    Result: dict[str, Any] = Field(
        default_factory=dict
    )