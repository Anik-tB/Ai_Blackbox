"""
AIBD FastAPI Backend Application.
"""

from __future__ import annotations
import logging
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aidbg.backend.api.health import router as health_router
from aidbg.backend.api.incidents import router as incidents_router
from aidbg.backend.api.ws import router as ws_router
from aidbg.backend.config import settings
from aidbg.backend.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aidbg.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AIBD database tables...")
    await init_db()
    logger.info(f"AIBD backend started in {settings.environment} mode.")
    yield
    logger.info("AIBD backend shutting down.")


app = FastAPI(
    title=settings.app_name,
    description="AI Black Box Debugger - Telemetry Ingestion and Root Cause Reasoning API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(incidents_router)
app.include_router(ws_router)


def start():
    """Start uvicorn server directly."""
    uvicorn.run(
        "aidbg.backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )


if __name__ == "__main__":
    start()
