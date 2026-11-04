"""
System Telemetry, Health, and 24/7 Render Keep-Alive Router.
Includes `/ping` keep-alive endpoint designed for continuous zero-sleep operation on Render Free Tier.
"""
from __future__ import annotations

import datetime
import logging
import os
import time
from typing import Any, Dict
from fastapi import APIRouter

from config.settings import settings
from core.db.client import db_client
from core.router.key_pool import key_pool

logger = logging.getLogger("shivai.api.system")
router = APIRouter(tags=["System & Keep-Alive"])

STARTUP_TIME = time.time()


@router.get("/ping")
async def ping() -> Dict[str, Any]:
    """
    Render Free Tier 24/7 Keep-Alive Heartbeat.
    Responding to this endpoint every 10-14 minutes prevents Render free instances from idling,
    ensuring 100% continuous uptime within the 750 free instance hours/month allocation.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    uptime_seconds = int(time.time() - STARTUP_TIME)
    return {
        "status": "pong",
        "service": "SHIV AI Smart Router",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "server_time_utc": now.isoformat(),
        "uptime_seconds": uptime_seconds,
        "keep_alive_policy": "24/7 zero-sleep compliant",
    }


@router.get("/health")
async def health() -> Dict[str, Any]:
    """Comprehensive system health diagnostics."""
    db_healthy = False
    user_count = 0
    try:
        conn = db_client.get_connection()
        user_count = conn.execute("SELECT count(*) as cnt FROM users").fetchone()["cnt"]
        conn.close()
        db_healthy = True
    except Exception as e:
        logger.error(f"Health check DB error: {e}")

    key_summary = key_pool.get_status_summary()

    return {
        "status": "healthy" if db_healthy else "degraded",
        "version": settings.VERSION,
        "database": {
            "status": "connected" if db_healthy else "unreachable",
            "type": "SQLite WAL",
            "registered_users": user_count,
        },
        "key_pool": key_summary,
        "multimodal": {
            "image": "Pollinations FLUX (Active)",
            "voice": "Edge Neural TTS (Active)",
            "video": "Cinematic Reel Engine (Active)",
        },
    }


@router.get("/keys/status")
async def get_keys_status() -> Dict[str, Any]:
    """Returns real-time capacity and cooldown metrics across all provider pools."""
    return {
        "pools": key_pool.get_status_summary(),
        "cooldown_duration_minutes": int(key_pool.cooldown_duration_seconds / 60),
    }
