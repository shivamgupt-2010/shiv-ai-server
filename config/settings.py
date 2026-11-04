"""
SHIV AI Core Configuration Settings.
Provides unified environment resolution for local development and cloud (Render) deployments.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Server Information
    PROJECT_NAME: str = "SHIV AI Smart Router"
    APP_NAME: str = "SHIV AI Sovereign Smart Router"
    SERVICE_NAME: str = "shivai"
    VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Render 24/7 Keep-Alive
    RENDER_EXTERNAL_URL: Optional[str] = None
    KEEP_ALIVE_ENABLED: bool = True
    KEEP_ALIVE_INTERVAL_SECONDS: int = 600  # 10 minutes

    # SHIV Database & Auth Configuration
    # Local priority: F:/SHIV/shiv-database/shiv_dev.db
    SHIV_DATABASE_PATH: str = str(
        Path("F:/SHIV/shiv-database/shiv_dev.db")
        if Path("F:/SHIV/shiv-database/shiv_dev.db").exists()
        else Path(__file__).resolve().parent.parent / "data" / "shiv_dev.db"
    )
    SHIV_DB_PATH: str = str(
        Path("F:/SHIV/shiv-database/shiv_dev.db")
        if Path("F:/SHIV/shiv-database/shiv_dev.db").exists()
        else Path(__file__).resolve().parent.parent / "data" / "shiv_dev.db"
    )

    SHIV_AUTH_JWT_SECRET: str = "shiv-platform-super-secret-jwt-key-for-local-dev-12345"
    SHIV_AUTH_JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    API_KEY_PREFIX: str = "shiv_sk_"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    # AI Keys Configuration (Multi-Key Pools)
    GEMINI_API_KEYS: str = ""
    GROQ_API_KEYS: str = ""
    CEREBRAS_API_KEYS: str = ""
    SAMBANOVA_API_KEYS: str = ""
    MISTRAL_API_KEYS: str = ""
    HUGGINGFACE_TOKENS: str = ""
    OPENROUTER_API_KEYS: str = ""

    # Multimodal Media Storage
    MEDIA_STORAGE_DIR: str = str(Path(__file__).resolve().parent.parent / "data" / "media")


settings = Settings()

# Ensure media directory exists
Path(settings.MEDIA_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
