"""FastAPI backend for the ABC Dental Clinic AI Receptionist."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database.connection import init_db
from routes.token import router as token_router
from routes.health import router as health_router
from routes.spa import router as spa_router, DIST

logger = logging.getLogger("backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes first
app.include_router(token_router)
app.include_router(health_router)

# Static assets + SPA catch-all (must come AFTER API routes)
if (DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(DIST / "assets")), name="frontend-assets")

app.include_router(spa_router)
