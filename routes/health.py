"""GET /health endpoint."""

from fastapi import APIRouter

from config import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": "1.0.0",
    }
