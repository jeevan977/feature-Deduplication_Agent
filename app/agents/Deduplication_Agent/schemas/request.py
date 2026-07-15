
# from __future__ import annotations
# from pydantic import BaseModel, ConfigDict, Field

# class DeduplicationRequest(BaseModel):
#     model_config = ConfigDict(
#         extra="forbid",
#         populate_by_name=True,
#         str_strip_whitespace=True,
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

#     Token: str = Field(
#         ...,
#         min_length=1,
#         exclude=True,
#         repr=False,
#         description=(
#             "Dynamic bearer token used only for "
#             "token-usage API logging"
#         ),
#     )


from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


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

    IsRegenerate: bool = Field(
        default=False,
        description=(
            "True when the requirements are being "
            "regenerated; otherwise false"
        ),
    )

    UserId: str = Field(
        default="",
        description="User identifier",
    )

    UserName: str = Field(
        default="",
        description="User name",
    )

    ProjectId: str = Field(
        default="",
        description="Project identifier",
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