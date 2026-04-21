"""SPA fallback — serve the built React frontend."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

DIST = Path(__file__).parent.parent / "frontend" / "dist"

router = APIRouter()


def _spa_response() -> FileResponse:
    index = DIST / "index.html"
    if index.exists():
        return FileResponse(str(index))
    raise HTTPException(
        status_code=503,
        detail="Frontend not built. Run: cd frontend && npm install && npm run build",
    )


@router.get("/", include_in_schema=False)
async def serve_root():
    return _spa_response()


@router.get("/{catchall:path}", include_in_schema=False)
async def serve_spa(_: str):
    return _spa_response()
