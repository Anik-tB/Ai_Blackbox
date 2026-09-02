"""
AIBD FastAPI Backend Application.
Hardened with rotating file logging, CORS, and production lifecycle hooks.
"""

from __future__ import annotations
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from aidbg.backend.api.health import router as health_router
from aidbg.backend.api.incidents import router as incidents_router
from aidbg.backend.api.ws import router as ws_router
from aidbg.backend.config import settings
from aidbg.backend.database import init_db

# Configure rotating file log handler for production observability
log_dir = Path(".aidbg/logs")
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
root_logger = logging.getLogger()
file_handler = RotatingFileHandler(
    log_dir / "backend.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8"
)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
root_logger.addHandler(file_handler)

logger = logging.getLogger("aidbg.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AIBD database tables...")
    try:
        await init_db()
        logger.info(f"AIBD backend started successfully in {settings.environment} mode.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
    yield
    logger.info("AIBD backend shutting down gracefully.")


app = FastAPI(
    title=settings.app_name,
    description="AI Black Box Debugger - Telemetry Ingestion and Root Cause Reasoning API",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
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
    """Start uvicorn server with production settings."""
    uvicorn.run(
        "aidbg.backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        access_log=False
    )


if __name__ == "__main__":
    start()
