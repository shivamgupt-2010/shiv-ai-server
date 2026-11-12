"""
OpenAI-Compatible Chat Completion Router with Native SHIV DB Memory & Sovereign Persona.
Exposes standard `/v1/chat/completions` endpoint for web apps, Android clients, and OpenAI SDKs.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from core.auth.security import UserContext, get_current_user
from core.db.client import db_client
from core.memory.learner import fact_learner
from core.memory.short_term import short_term_memory
from core.persona.prompt import build_shiv_system_prompt
from core.router.fallback import smart_router

logger = logging.getLogger("shivai.api.chat")
router = APIRouter(prefix="/v1", tags=["Inference & Chat"])


class ChatMessage(BaseModel):
    role: str
    content: Optional[Any] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "shiv-ai-v2"
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    user: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None


@router.post("/chat/completions")
async def chat_completions(
    req: ChatCompletionRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(get_current_user),
):
    """
    Standard OpenAI-compatible chat completion endpoint with native tool-calling support.
    Automatically enriches prompt with SHIV DB long-term memories and sliding short-term context.
    Sanitizes all outputs to ensure Sovereign SHIV AI Identity.
    """
    user_id = current_user.user_id
    user_display = current_user.username
    request_id = f"chatcmpl_{uuid.uuid4().hex[:12]}"
    created_ts = int(time.time())

    # Extract the last user message for learning and memory
    last_user_message = ""
    for msg in reversed(req.messages):
        if msg.role == "user" and isinstance(msg.content, str):
            last_user_message = msg.content
            break

    # 1. Build Sovereign System Prompt with Long-Term Memories injected
    shiv_system = build_shiv_system_prompt(user_id=user_id, user_display_name=user_display)

    # 2. Assemble formatted messages with SHIV Persona upfront
    assembled_messages: List[Dict[str, Any]] = [{"role": "system", "content": shiv_system}]

    for msg in req.messages:
        if msg.role == "system":
            # Append supplementary instructions after master persona
            assembled_messages.append({"role": "system", "content": str(msg.content or "")})
        else:
            m_dict: Dict[str, Any] = {"role": msg.role}
            if msg.content is not None:
                m_dict["content"] = msg.content
            if msg.tool_calls:
                m_dict["tool_calls"] = msg.tool_calls
            if msg.tool_call_id:
                m_dict["tool_call_id"] = msg.tool_call_id
            if msg.name:
                m_dict["name"] = msg.name
            assembled_messages.append(m_dict)

    # Record user prompt into short-term sliding memory
    if last_user_message:
        short_term_memory.add_message(user_id=user_id, role="user", content=last_user_message)

    # 3. Handle Streaming SSE Mode
    if req.stream:
        async def event_generator() -> AsyncGenerator[str, None]:
            accumulated_chunks: List[str] = []
            try:
                async for item in smart_router.stream_chat(
                    messages=assembled_messages,
                    preferred_model=req.model,
                    tools=req.tools,
                    tool_choice=req.tool_choice,
                ):
                    delta = item.get("delta", {})
                    finish_reason = item.get("finish_reason")
                    content_piece = delta.get("content")
                    if content_piece:
                        accumulated_chunks.append(content_piece)

                    payload = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created_ts,
                        "model": "shiv-ai-v2",
                        "choices": [
                            {
                                "index": 0,
                                "delta": delta,
                                "finish_reason": finish_reason,
                            }
                        ],
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

                yield "data: [DONE]\n\n"

            finally:
                full_assistant_reply = "".join(accumulated_chunks)
                if full_assistant_reply:
                    short_term_memory.add_message(
                        user_id=user_id,
                        role="assistant",
                        content=full_assistant_reply,
                    )
                # Background fact extraction
                if last_user_message:
                    background_tasks.add_task(
                        fact_learner.extract_and_learn,
                        user_id=user_id,
                        user_text=last_user_message,
                    )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # 4. Handle Standard Synchronous Return
    result = await smart_router.complete_chat(
        messages=assembled_messages,
        preferred_model=req.model,
        tools=req.tools,
        tool_choice=req.tool_choice,
    )

    msg_payload = result.get("message", {"role": "assistant", "content": result.get("content", "")})
    finish_reason = result.get("finish_reason", "tool_calls" if msg_payload.get("tool_calls") else "stop")
    content_text = msg_payload.get("content") or ""

    # Record assistant message into short-term memory
    if content_text:
        short_term_memory.add_message(user_id=user_id, role="assistant", content=content_text)

    # Schedule background memory extraction
    if last_user_message:
        background_tasks.add_task(
            fact_learner.extract_and_learn,
            user_id=user_id,
            user_text=last_user_message,
        )

    prompt_toks = sum(len(str(m.get("content", ""))) for m in assembled_messages) // 4
    compl_toks = len(str(content_text)) // 4

    return {
        "id": request_id,
        "object": "chat.completion",
        "created": created_ts,
        "model": "shiv-ai-v2",
        "choices": [
            {
                "index": 0,
                "message": msg_payload,
                "finish_reason": finish_reason,
            }
        ],
        "usage": {
            "prompt_tokens": max(1, prompt_toks),
            "completion_tokens": max(1, compl_toks),
            "total_tokens": max(2, prompt_toks + compl_toks),
        },
    }
