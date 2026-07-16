# # # from fastapi import APIRouter

# # # from app.api.routes.deduplication_route import (
# # #     router as deduplication_router,
# # # )


# # # api_router = APIRouter(prefix="/api")

# # # api_router.include_router(deduplication_router)


# # # @api_router.get("/status")
# # # async def api_status():
# # #     return {
# # #         "status": "success",
# # #         "agent": "Requirement Deduplication Agent",
# # #         "message": "API is running",
# # #     }

# # from fastapi import APIRouter

# # from app.api.routes.deduplication_route import (
# #     router as deduplication_router,
# # )
# # from app.api.routes.evidence_summary_router import (
# #     router as evidence_summary_router,
# # )


# # api_router = APIRouter(prefix="/api")

# # api_router.include_router(deduplication_router)
# # api_router.include_router(evidence_summary_router)


# # @api_router.get("/status")
# # async def api_status():
# #     return {
# #         "status": "success",
# #         "agents": [
# #             "Requirement Deduplication Agent",
# #             "Evidence Summary Agent",
# #         ],
# #         "message": "API is running",
# #     }



# from fastapi import APIRouter

# from app.api.routes.deduplication_route import (
#     router as deduplication_router,
# )
# from app.api.routes.evidence_summary_router import (
#     router as evidence_summary_router,
# )


# api_router = APIRouter(
#     prefix="/api",
# )


# api_router.include_router(
#     deduplication_router,
# )

# api_router.include_router(
#     evidence_summary_router,
# )


# @api_router.get("/status")
# async def api_status():
#     return {
#         "status": "success",
#         "agents": [
#             "Requirement Deduplication Agent",
#             "Evidence Summary Agent",
#         ],
#         "message": "API is running",
#     }


from fastapi import APIRouter

from app.api.routes.deduplication_route import (
    router as deduplication_router,
)


api_router = APIRouter(
    prefix="/api",
)


# Register only the main workflow route.
#
# POST /api/requirement-deduplication/process
#
# Workflow:
#   1. Requirement Deduplication Agent runs.
#   2. Agent 1 completes successfully.
#   3. Evidence Summary Agent runs automatically.
#   4. Agent 2 saves its output in MongoDB.
#
# The Evidence Summary route is not registered separately
# because Agent 2 is called internally from:
#
# app/api/routes/deduplication_route.py
api_router.include_router(
    deduplication_router,
)


@api_router.get(
    "/status",
    tags=["default"],
)
async def api_status() -> dict:
    return {
        "status": "success",
        "workflow": [
            "Requirement Deduplication Agent",
            "Evidence Summary Agent",
        ],
        "entryPoint": (
            "POST "
            "/api/requirement-deduplication/process"
        ),
        "message": (
            "Requirement Deduplication runs first. "
            "Evidence Summary runs automatically "
            "after Agent 1 completes successfully."
        ),
    }