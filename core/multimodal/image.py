"""
Real Multimodal Image Generation Engine.
Integrates Pollinations FLUX & Turbo models for zero-cost, high-resolution AI art synthesis.
Generated images are persisted directly into SHIV DB media storage.
"""
from __future__ import annotations

import base64
import logging
import urllib.parse
import uuid
from typing import Any, Dict, Optional
import httpx

from core.db.client import db_client

logger = logging.getLogger("shivai.multimodal.image")


async def generate_image(
    prompt: str,
    user_id: str = "guest",
    width: int = 1024,
    height: int = 1024,
    model: str = "flux",
    enhance: bool = True,
) -> Dict[str, Any]:
    """
    Generates a 1024x1024 image using Pollinations FLUX engine and stores it in SHIV DB.
    Zero API key required; 100% free with unlimited generation capacity.
    """
    encoded_prompt = urllib.parse.quote(prompt.strip())
    params = f"?width={width}&height={height}&model={model}&nologo=true"
    if enhance:
        params += "&enhance=true"
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}{params}"

    logger.info(f"Generating image with prompt: '{prompt[:60]}...' model: {model}")

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise RuntimeError(f"Image generation failed with HTTP {resp.status_code}: {resp.text[:200]}")
        
        image_bytes = resp.content

    file_name = f"img_{uuid.uuid4().hex[:12]}.png"
    relative_url = db_client.save_media_blob(
        project_id=user_id,
        file_name=file_name,
        content_type="image/png",
        binary_data=image_bytes,
    )

    b64_data = base64.b64encode(image_bytes).decode("utf-8")

    return {
        "file_name": file_name,
        "url": relative_url,
        "content_type": "image/png",
        "size_bytes": len(image_bytes),
        "prompt": prompt,
        "width": width,
        "height": height,
        "model": model,
        "data_base64": b64_data,
    }
