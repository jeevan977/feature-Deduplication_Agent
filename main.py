from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.infrastructure.database import close_mongo_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_mongo_connection()


app = FastAPI(
    title="Requirement Deduplication Agent",
    description="LangGraph-based requirement deduplication agent",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "status": "success",
        "agent": "Requirement Deduplication Agent",
        "message": "Requirement Deduplication Agent is running",
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
    }
