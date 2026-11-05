"""
SHIV AI API Key Management & Quota Router.
Allows users to create, list, and revoke sovereign API keys (shiv_sk_free_... / shiv_sk_live_...)
with enforced rate limiting and credit protection.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.auth.security import UserContext, get_current_user
from core.db.client import db_client

logger = logging.getLogger("shivai.api.keys")
router = APIRouter(prefix="/api-keys", tags=["API Key Management"])


class CreateApiKeyRequest(BaseModel):
    key_name: str = Field(..., min_length=2, max_length=100, description="Friendly identifier for this API key")
    tier: str = Field("free", description="'free' (10 RPM, 250 daily) or 'pro' (60 RPM, 10,000 daily)")


@router.post("", status_code=status.HTTP_201_CREATED)
async def generate_api_key(
    req: CreateApiKeyRequest,
    current_user: UserContext = Depends(get_current_user),
):
    """
    Generates a new sovereign SHIV AI API key for the caller.
    The secret key is returned ONCE upon creation and hashed in the database.
    """
    valid_tiers = {"free", "pro"}
    tier = req.tier.lower() if req.tier.lower() in valid_tiers else "free"

    # Restrict free tier users to max 5 active keys
    existing_keys = db_client.list_user_api_keys(current_user.user_id)
    active_keys = [k for k in existing_keys if not k.get("revoked")]
    if len(active_keys) >= 5 and tier == "free":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "KEY_LIMIT_REACHED", "message": "Free tier is limited to 5 active API keys. Please revoke an unused key."}},
        )

    try:
        new_key = db_client.create_api_key(
            user_id=current_user.user_id,
            key_name=req.key_name,
            tier=tier,
        )
        return {
            "success": True,
            "message": "API Key created successfully. Store this secret key securely — it will not be displayed again.",
            "data": new_key,
        }
    except Exception as e:
        logger.error(f"Failed to generate API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "KEY_CREATION_FAILED", "message": str(e)}},
        )


@router.get("")
async def list_api_keys(current_user: UserContext = Depends(get_current_user)):
    """Lists all API keys created by the authenticated user."""
    keys = db_client.list_user_api_keys(current_user.user_id)
    return {
        "success": True,
        "count": len(keys),
        "data": keys,
    }


@router.delete("/{key_id}")
async def revoke_api_key(key_id: str, current_user: UserContext = Depends(get_current_user)):
    """Instantly revokes an API key."""
    success = db_client.revoke_api_key(user_id=current_user.user_id, key_id=key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "KEY_NOT_FOUND", "message": "API key not found or already revoked."}},
        )
    return {"success": True, "message": "API key revoked successfully."}


@router.get("/tiers")
async def get_tier_limits():
    """Returns the rate limits and specifications for each tier."""
    return {
        "tiers": {
            "free": {
                "name": "Sovereign Free Tier",
                "rpm": 10,
                "daily_requests": 250,
                "max_tokens": 2048,
                "models": ["SHIV-Core-Omni", "SHIV-Vision-FLUX", "SHIV-Voice-Neural", "SHIV-Reels-v1"],
                "price": "$0.00",
            },
            "pro": {
                "name": "Sovereign Pro Tier",
                "rpm": 60,
                "daily_requests": 10000,
                "max_tokens": 8192,
                "models": ["SHIV-Core-Omni", "SHIV-Vision-FLUX", "SHIV-Voice-Neural", "SHIV-Reels-v1"],
                "price": "$19.00/mo",
            },
        }
    }
