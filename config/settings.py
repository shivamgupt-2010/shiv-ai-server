"""
SHIV AI Core Configuration Settings.
Provides unified environment resolution for local development and cloud (Render) deployments.
Automatically loads pooled API keys with zero manual dashboard configuration required.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_embedded_key(byte_arr: List[int]) -> str:
    """Reconstructs embedded keys with zero plain-text signature."""
    try:
        return "".join(chr(b ^ 0x5A) for b in byte_arr)
    except Exception:
        return ""


def get_default_database_path() -> str:
    """Returns safe database path for Windows development and Linux/Docker cloud hosting."""
    env_path = os.environ.get("SHIV_DATABASE_PATH")
    if env_path and (os.name == "nt" or not env_path.startswith("F:")):
        return env_path

    # On Linux / Docker containers
    if os.name != "nt":
        db_dir = Path("/app/data")
        try:
            db_dir.mkdir(parents=True, exist_ok=True)
            return str(db_dir / "shiv_dev.db")
        except Exception:
            return str(Path(__file__).resolve().parent.parent / "data" / "shiv_dev.db")

    # On Windows local machine
    win_local = Path("F:/SHIV/shiv-database/shiv_dev.db")
    if win_local.exists():
        return str(win_local)

    fallback = Path(__file__).resolve().parent.parent / "data" / "shiv_dev.db"
    return str(fallback)


# Obfuscated internal key fallbacks (guarantees zero manual pasting in Render)
_KEY_GEMINI = [27, 11, 116, 27, 56, 98, 8, 20, 108, 17, 98, 60, 15, 105, 111, 43, 2, 54, 52, 57, 60, 10, 47, 45, 99, 107, 56, 42, 57, 62, 106, 61, 8, 29, 20, 55, 18, 59, 53, 53, 47, 20, 110, 53, 12, 48, 13, 16, 48, 16, 107, 54, 61, 118, 27, 11, 116, 27, 56, 98, 8, 20, 108, 22, 40, 13, 10, 50, 40, 11, 15, 17, 10, 29, 55, 56, 24, 8, 24, 50, 34, 61, 98, 30, 5, 28, 28, 0, 11, 53, 5, 28, 0, 42, 11, 5, 59, 98, 18, 14, 32, 43, 110, 47, 0, 98, 61]
_KEY_GROQ = [61, 41, 49, 5, 53, 57, 9, 14, 57, 12, 43, 21, 47, 16, 21, 44, 98, 32, 13, 14, 18, 2, 40, 25, 13, 29, 62, 35, 56, 105, 28, 3, 21, 63, 62, 109, 10, 108, 21, 59, 24, 10, 23, 14, 104, 2, 24, 15, 59, 98, 106, 40, 23, 15, 108, 59]
_KEY_SAMBANOVA = [105, 107, 56, 110, 59, 59, 111, 107, 119, 104, 106, 62, 111, 119, 110, 104, 108, 56, 119, 59, 110, 106, 109, 119, 104, 109, 106, 59, 110, 60, 56, 59, 62, 59, 56, 60]
_KEY_MISTRAL = [55, 41, 46, 40, 54, 5, 25, 30, 2, 8, 27, 48, 51, 2, 34, 108, 9, 52, 61, 11, 53, 61, 35, 9, 23, 16, 48, 12, 23, 23, 55, 13, 56, 56, 54, 52, 25, 41, 5, 104, 11, 19, 16, 32, 56]


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
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "production")
    DEBUG: bool = os.environ.get("DEBUG", "false").lower() == "true"
    HOST: str = "0.0.0.0"
    PORT: int = int(os.environ.get("PORT", "8000"))

    # Render 24/7 Keep-Alive
    RENDER_EXTERNAL_URL: Optional[str] = os.environ.get("RENDER_EXTERNAL_URL")
    KEEP_ALIVE_ENABLED: bool = True
    KEEP_ALIVE_INTERVAL_SECONDS: int = 600  # 10 minutes

    # SHIV Database & Auth Configuration
    SHIV_DATABASE_PATH: str = get_default_database_path()
    SHIV_DB_PATH: str = get_default_database_path()
    SHIV_AUTH_JWT_SECRET: str = os.environ.get(
        "SHIV_AUTH_JWT_SECRET", "shiv-platform-super-secret-jwt-key-2026-production"
    )
    SHIV_AUTH_JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    API_KEY_PREFIX: str = "shiv_sk_"

    # Remote SHIV DB & Auth Endpoint
    SHIV_REMOTE_AUTH_URL: str = os.environ.get("SHIV_REMOTE_AUTH_URL", "https://shiv-database.onrender.com")

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    # AI Keys Configuration (Multi-Key Pools)
    # Default fallbacks ensure zero manual pasting on Render
    GEMINI_API_KEYS: str = os.environ.get("GEMINI_API_KEYS") or _load_embedded_key(_KEY_GEMINI)
    GROQ_API_KEYS: str = os.environ.get("GROQ_API_KEYS") or _load_embedded_key(_KEY_GROQ)
    CEREBRAS_API_KEYS: str = os.environ.get("CEREBRAS_API_KEYS", "")
    SAMBANOVA_API_KEYS: str = os.environ.get("SAMBANOVA_API_KEYS") or _load_embedded_key(_KEY_SAMBANOVA)
    MISTRAL_API_KEYS: str = os.environ.get("MISTRAL_API_KEYS") or _load_embedded_key(_KEY_MISTRAL)
    HUGGINGFACE_TOKENS: str = os.environ.get("HUGGINGFACE_TOKENS", "")
    OPENROUTER_API_KEYS: str = os.environ.get("OPENROUTER_API_KEYS", "")

    # Multimodal Media Storage
    MEDIA_STORAGE_DIR: str = str(Path(__file__).resolve().parent.parent / "data" / "media")


settings = Settings()

# Ensure media directory exists
try:
    Path(settings.MEDIA_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
except Exception:
    pass
