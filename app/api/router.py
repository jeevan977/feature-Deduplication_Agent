# from fastapi import APIRouter

# from app.api.routes.deduplication_route import (
#     router as deduplication_router,
# )


# api_router = APIRouter(prefix="/api")

# api_router.include_router(deduplication_router)


# @api_router.get("/status")
# async def api_status():
#     return {
#         "status": "success",
#         "agent": "Requirement Deduplication Agent",
#         "message": "API is running",
#     }

from fastapi import APIRouter

from app.api.routes.deduplication_route import (
    router as deduplication_router,
)
from app.api.routes.evidence_summary_router import (
    router as evidence_summary_router,
)


api_router = APIRouter(prefix="/api")

api_router.include_router(deduplication_router)
api_router.include_router(evidence_summary_router)


@api_router.get("/status")
async def api_status():
    return {
        "status": "success",
        "agents": [
            "Requirement Deduplication Agent",
            "Evidence Summary Agent",
        ],
        "message": "API is running",
    }