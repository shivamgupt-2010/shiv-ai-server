"""
SHIV AI Smart Router & Sovereign Inference Server.
Main Application Entry Point.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from apps.api.routers import (
    auth_router,
    chat_router,
    keys_router,
    memory_router,
    multimodal_router,
    system_router,
)
from config.settings import settings
from core.db.client import db_client
from core.router.key_pool import key_pool

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("shivai.main")


async def keep_alive_background_loop():
    """
    Automatic Render Free Tier Self-Ping Loop.
    Pings the service every 10 minutes to prevent Render compute instances from sleeping.
    """
    ping_url = os.environ.get("RENDER_EXTERNAL_URL")
    if ping_url:
        ping_url = f"{ping_url.rstrip('/')}/ping"
        logger.info(f"Self-ping keep-alive initialized targeting {ping_url}")
    else:
        logger.info("Local keep-alive heartbeat loop initialized (runs every 600 seconds).")

    while True:
        try:
            await asyncio.sleep(600)  # 10 minutes
            if ping_url:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(ping_url)
                    logger.info(f"Keep-alive self-ping sent -> HTTP {resp.status_code}")
            else:
                logger.info("Keep-alive heartbeat tick: instance active.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning(f"Keep-alive cycle error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("=" * 60)
    logger.info(f"  SHIV AI Smart Router Backend - v{settings.VERSION}")
    logger.info(f"  Environment: {settings.ENVIRONMENT} | Debug: {settings.DEBUG}")
    logger.info(f"  Database Path: {settings.SHIV_DATABASE_PATH}")
    logger.info("=" * 60)

    # Initialize tables if needed
    db_client.initialize_tables()

    # Log key pool telemetry
    status_summary = key_pool.get_status_summary()
    total_active = sum(p["active_keys"] for p in status_summary.values())
    logger.info(f"Key Pool initialized with {total_active} active provider keys.")

    # Start background keep-alive task
    keep_alive_task = asyncio.create_task(keep_alive_background_loop())

    yield

    # --- Shutdown ---
    logger.info("Shutting down SHIV AI server...")
    keep_alive_task.cancel()
    try:
        await keep_alive_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Sovereign AI Router with 50+ Key Rotation Pool, Native SHIV DB Auth, and Multimodal Engines.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS dynamically for all clients (Web, Vercel, Android, Codespaces)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled Exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred in SHIV AI Engine.",
                "details": str(exc) if settings.DEBUG else None,
            }
        },
    )


# Register all API sub-routers
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(keys_router)
app.include_router(chat_router)
app.include_router(multimodal_router)
app.include_router(memory_router)


@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "identity": "SHIV AI Sovereign Intelligence",
        "version": settings.VERSION,
        "status": "online",
        "documentation": "/docs",
        "health": "/health",
        "keep_alive": "/ping",
    }
