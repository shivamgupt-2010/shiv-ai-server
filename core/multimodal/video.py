"""
Real Multimodal Video & Animation Engine.
Synthesizes video reels, animated visual sequences, and media compositions.
Utilizes FFmpeg (when present in Linux/Render containers) and native Pillow frame interpolation
to generate animated WebP/MP4 media stored directly into SHIV DB.
"""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import shutil
import tempfile
import uuid
from typing import Any, Dict, List, Optional
from PIL import Image, ImageDraw, ImageFont

from core.db.client import db_client
from core.multimodal.image import generate_image
from core.multimodal.voice import synthesize_speech

logger = logging.getLogger("shivai.multimodal.video")


async def generate_video_reel(
    prompt: str,
    speech_text: Optional[str] = None,
    user_id: str = "guest",
    duration_seconds: int = 5,
    fps: int = 10,
) -> Dict[str, Any]:
    """
    Generates a multimodal video reel:
    1. Generates a base image matching the prompt.
    2. Synthesizes voice narration if speech_text is provided.
    3. Renders animated frames with cinematic zoom/pan and text overlay.
    4. Encodes as MP4 (if ffmpeg is available) or high-quality animated WebP/GIF.
    5. Saves the final media asset in SHIV DB.
    """
    logger.info(f"Generating video reel for prompt: '{prompt[:50]}' (duration: {duration_seconds}s)")

    # Step 1: Generate base image
    img_res = await generate_image(prompt=prompt, user_id=user_id, width=768, height=768)
    img_bytes = base64.b64decode(img_res["data_base64"])
    base_image = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    # Step 2: Synthesize voice if requested
    audio_info = None
    if speech_text:
        try:
            audio_info = await synthesize_speech(text=speech_text, user_id=user_id)
        except Exception as e:
            logger.warning(f"Voice narration failed: {e}")

    # Step 3: Check for FFmpeg availability
    ffmpeg_bin = shutil.which("ffmpeg")

    total_frames = duration_seconds * fps
    width, height = base_image.size

    frames: List[Image.Image] = []

    # Generate subtle Ken Burns zoom effect
    for f in range(total_frames):
        zoom_factor = 1.0 + (0.15 * (f / max(1, total_frames - 1)))
        crop_w = int(width / zoom_factor)
        crop_h = int(height / zoom_factor)
        left = (width - crop_w) // 2
        top = (height - crop_h) // 2
        right = left + crop_w
        bottom = top + crop_h

        cropped = base_image.crop((left, top, right, bottom))
        frame = cropped.resize((width, height), Image.Resampling.BICUBIC)

        # Subtle watermark
        draw = ImageDraw.Draw(frame)
        draw.text((20, height - 35), "SHIV AI REEL", fill=(255, 255, 255, 180))

        frames.append(frame)

    output_bytes: bytes = b""
    content_type = "image/webp"
    file_ext = "webp"

    # Step 4: Encode
    if ffmpeg_bin and audio_info:
        # Use FFmpeg to combine frames and audio into real MP4
        with tempfile.TemporaryDirectory() as tmpdir:
            frame_pattern = os.path.join(tmpdir, "frame_%04d.png")
            for idx, fr in enumerate(frames):
                fr.save(frame_pattern % idx, "PNG")

            audio_path = os.path.join(tmpdir, "narration.mp3")
            with open(audio_path, "wb") as af:
                af.write(base64.b64decode(audio_info["data_base64"]))

            out_mp4 = os.path.join(tmpdir, "output.mp4")
            cmd = [
                ffmpeg_bin,
                "-y",
                "-framerate", str(fps),
                "-i", frame_pattern,
                "-i", audio_path,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-shortest",
                out_mp4,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if os.path.exists(out_mp4):
                with open(out_mp4, "rb") as mf:
                    output_bytes = mf.read()
                content_type = "video/mp4"
                file_ext = "mp4"

    if not output_bytes:
        # Fallback to high-quality animated WebP
        buffer = io.BytesIO()
        frame_duration_ms = int(1000 / fps)
        frames[0].save(
            buffer,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=frame_duration_ms,
            loop=0,
            quality=85,
        )
        output_bytes = buffer.getvalue()
        content_type = "image/webp"
        file_ext = "webp"

    file_name = f"reel_{uuid.uuid4().hex[:12]}.{file_ext}"
    relative_url = db_client.save_media_blob(
        project_id=user_id,
        file_name=file_name,
        content_type=content_type,
        binary_data=output_bytes,
    )

    b64_data = base64.b64encode(output_bytes).decode("utf-8")

    return {
        "file_name": file_name,
        "url": relative_url,
        "content_type": content_type,
        "size_bytes": len(output_bytes),
        "prompt": prompt,
        "duration_seconds": duration_seconds,
        "frames_count": len(frames),
        "audio_url": audio_info["url"] if audio_info else None,
        "data_base64": b64_data,
    }
