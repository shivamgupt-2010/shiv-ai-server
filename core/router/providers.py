"""
Asynchronous HTTP Provider Adapters for Multi-Model Inference.
Interfaces with Gemini, Groq, Cerebras, SambaNova, Mistral, OpenRouter, and zero-cost public fallbacks.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator, Dict, List, Optional
import httpx

from core.persona.sanitizer import sanitize_output

logger = logging.getLogger("shivai.router.providers")

DEFAULT_TIMEOUT = 45.0


class ProviderExecutionError(Exception):
    def __init__(self, provider: str, status_code: int, message: str):
        self.provider = provider
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{provider}] Error {status_code}: {message}")


# --- 1. Google Gemini Provider ---
async def call_gemini(
    key: str,
    messages: List[Dict[str, str]],
    model: str = "gemini-flash-lite-latest",
    stream: bool = False,
) -> AsyncGenerator[str, None]:
    """Invokes Google Gemini API with SSE streaming or standard return."""
    # Convert OpenAI message format to Gemini contents
    contents = []
    system_instruction = None

    for m in messages:
        role = m.get("role", "user")
        text = m.get("content", "")
        if role == "system":
            system_instruction = {"parts": [{"text": text}]}
        elif role == "assistant":
            contents.append({"role": "model", "parts": [{"text": text}]})
        else:
            contents.append({"role": "user", "parts": [{"text": text}]})

    payload = {"contents": contents}
    if system_instruction:
        payload["systemInstruction"] = system_instruction

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={key}"

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        async with client.stream("POST", url, json=payload, headers={"Content-Type": "application/json"}) as resp:
            if resp.status_code != 200:
                err_text = await resp.aread()
                raise ProviderExecutionError("gemini", resp.status_code, err_text.decode("utf-8", "replace"))

            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    raw_json = line[6:].strip()
                    if raw_json:
                        try:
                            data = json.loads(raw_json)
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = candidates[0].get("content", {}).get("parts", [])
                                for p in parts:
                                    chunk = p.get("text", "")
                                    if chunk:
                                        yield sanitize_output(chunk)
                        except Exception:
                            pass


# --- 2. OpenAI-Compatible Adapter (Groq, Cerebras, SambaNova, Mistral, OpenRouter) ---
async def call_openai_compatible(
    provider_name: str,
    base_url: str,
    key: str,
    messages: List[Dict[str, str]],
    model: str,
    stream: bool = False,
) -> AsyncGenerator[str, None]:
    """Invokes any standard OpenAI-compatible chat completion endpoint."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": stream,
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        if stream:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    err_text = await resp.aread()
                    raise ProviderExecutionError(provider_name, resp.status_code, err_text.decode("utf-8", "replace"))

                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_obj = json.loads(data_str)
                            delta = chunk_obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                yield sanitize_output(delta)
                        except Exception:
                            pass
        else:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise ProviderExecutionError(provider_name, resp.status_code, resp.text)
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            yield sanitize_output(content)


# --- 3. Zero-Cost Public Emergency Fallback ---
async def call_public_fallback(
    messages: List[Dict[str, str]],
    stream: bool = False,
) -> AsyncGenerator[str, None]:
    """
    Guaranteed zero-cost public inference adapter (Pollinations AI text).
    Zero API key required; ensures the server functions immediately before keys are added.
    """
    url = "https://text.pollinations.ai/"
    headers = {"Content-Type": "application/json"}
    payload = {
        "messages": messages,
        "model": "openai",
        "stream": stream,
    }

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        if stream:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    err_text = await resp.aread()
                    raise ProviderExecutionError("public_fallback", resp.status_code, err_text.decode("utf-8", "replace"))

                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            data_obj = json.loads(data_str)
                            delta = data_obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if delta:
                                yield sanitize_output(delta)
                        except Exception:
                            pass
                    elif line.strip():
                        yield sanitize_output(line.strip())
        else:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise ProviderExecutionError("public_fallback", resp.status_code, resp.text)
            yield sanitize_output(resp.text)
