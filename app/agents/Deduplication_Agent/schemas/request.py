# from __future__ import annotations

# from pydantic import BaseModel, ConfigDict, Field


# class DeduplicationRequest(BaseModel):
#     model_config = ConfigDict(
#         extra="forbid",
#         populate_by_name=True,
#     )

#     CompanyId: str = Field(
#         ...,
#         min_length=1,
#         description="Company identifier",
#     )

#     TenderId: str = Field(
#         ...,
#         min_length=1,
#         description="Tender identifier",
#     )

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DeduplicationRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    CompanyId: str = Field(
        ...,
        min_length=1,
        description="Company identifier",
    )

    TenderId: str = Field(
        ...,
        min_length=1,
        description="Tender identifier",
    )

    Token: str = Field(
        ...,
        min_length=1,
        exclude=True,
        repr=False,
        description=(
            "Dynamic bearer token used only for "
            "token-usage API logging"
        ),
    )