

from fastapi import APIRouter

from app.api.routes.deduplication_route import (
    router as deduplication_router,
)


api_router = APIRouter(
    prefix="/api",
)


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