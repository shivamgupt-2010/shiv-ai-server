"""
Multimodal Media Generation Router.
Provides endpoints for AI image generation (Pollinations FLUX), voice synthesis (Edge Neural TTS),
and video reel generation, backed by SQLite zero-cost binary blob storage.
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field

from core.auth.security import UserContext, get_current_user
from core.db.client import db_client
from core.multimodal.image import generate_image
from core.multimodal.video import generate_video_reel
from core.multimodal.voice import synthesize_speech

logger = logging.getLogger("shivai.api.multimodal")
router = APIRouter(prefix="/media", tags=["Multimodal Media Generation"])


class ImageGenRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    width: Optional[int] = 1024
    height: Optional[int] = 1024
    model: Optional[str] = "flux"
    enhance: Optional[bool] = True


class VoiceSynthesisRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: Optional[str] = None
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"


class VideoReelRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    speech_text: Optional[str] = None
    duration_seconds: Optional[int] = Field(default=5, ge=1, le=30)


@router.post("/generate/image")
async def api_generate_image(
    req: ImageGenRequest,
    current_user: UserContext = Depends(get_current_user),
):
    """Generates a high-resolution 1024x1024 image using Pollinations FLUX."""
    try:
        res = await generate_image(
            prompt=req.prompt,
            user_id=current_user.user_id,
            width=req.width or 1024,
            height=req.height or 1024,
            model=req.model or "flux",
            enhance=req.enhance if req.enhance is not None else True,
        )
        return {"success": True, **res}
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "IMAGE_GENERATION_FAILED", "message": str(e)}},
        )


@router.post("/synthesize/voice")
async def api_synthesize_voice(
    req: VoiceSynthesisRequest,
    current_user: UserContext = Depends(get_current_user),
):
    """Synthesizes human-like neural speech in English or Hindi using Microsoft Edge TTS."""
    try:
        res = await synthesize_speech(
            text=req.text,
            user_id=current_user.user_id,
            voice=req.voice,
            rate=req.rate or "+0%",
            pitch=req.pitch or "+0Hz",
        )
        return {"success": True, **res}
    except Exception as e:
        logger.error(f"Voice synthesis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "VOICE_SYNTHESIS_FAILED", "message": str(e)}},
        )


@router.post("/generate/video")
async def api_generate_video(
    req: VideoReelRequest,
    current_user: UserContext = Depends(get_current_user),
):
    """Generates an animated video reel with voice narration and cinematic motion."""
    try:
        res = await generate_video_reel(
            prompt=req.prompt,
            speech_text=req.speech_text,
            user_id=current_user.user_id,
            duration_seconds=req.duration_seconds or 5,
        )
        return {"success": True, **res}
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "VIDEO_GENERATION_FAILED", "message": str(e)}},
        )


@router.get("/file/{file_name}")
async def get_media_file(file_name: str):
    """Serves binary media (PNG, MP3, WebP, MP4) directly from SHIV DB with caching."""
    media_blob = db_client.get_media_blob(file_name)
    if not media_blob:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "FILE_NOT_FOUND", "message": f"Media file '{file_name}' not found."}},
        )

    content_type, binary_data = media_blob
    return Response(
        content=binary_data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400, immutable",
            "Content-Length": str(len(binary_data)),
        },
    )
