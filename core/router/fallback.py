"""
Smart Router Engine with Multi-Tier Cascading Fallback & Sovereign Sanitization.
Executes prioritized key rotation across pooled providers (Gemini, Groq, Cerebras, SambaNova, Mistral, OpenRouter)
and automatically falls back to zero-cost public inference when keys are exhausted or unavailable.
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator, Dict, List, Optional

from core.persona.sanitizer import sanitize_output
from core.router.key_pool import key_pool
from core.router.providers import (
    ProviderExecutionError,
    call_gemini,
    call_openai_compatible,
    call_public_fallback,
)

logger = logging.getLogger("shivai.router.fallback")

# Configuration for OpenAI-compatible providers
PROVIDER_CONFIGS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "openai/gpt-oss-20b",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "default_model": "llama3.3-70b",
    },
    "sambanova": {
        "base_url": "https://api.sambanova.ai/v1",
        "default_model": "Meta-Llama-3.3-70B-Instruct",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-small-latest",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.3-70b-instruct:free",
    },
    "huggingface": {
        "base_url": "https://api-inference.huggingface.co/v1",
        "default_model": "meta-llama/Llama-3.2-3B-Instruct",
    },
}

# Order of provider evaluation
PROVIDER_PRIORITY = [
    "gemini",
    "groq",
    "cerebras",
    "sambanova",
    "mistral",
    "openrouter",
    "huggingface",
]


class SmartRouter:
    """Intelligent inference orchestrator with self-healing failover."""

    def __init__(self):
        self.pool = key_pool

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        preferred_model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Streams completions from the highest-priority available provider.
        Automatically catches rate limits (429), auth failures (401/403), or network errors,
        quarantines the failing key, and seamlessly rotates to the next key or provider.
        """
        attempted_keys = 0

        for provider in PROVIDER_PRIORITY:
            # Try available keys in this provider's pool
            while True:
                key_node = self.pool.get_next_key(provider)
                if not key_node:
                    break

                attempted_keys += 1
                logger.info(f"Routing to [{provider}] with key {key_node.key[:8]}...")

                try:
                    tokens_streamed = 0
                    if provider == "gemini":
                        model = preferred_model or "gemini-flash-lite-latest"
                        async for chunk in call_gemini(key=key_node.key, messages=messages, model=model, stream=True):
                            tokens_streamed += 1
                            yield chunk
                    else:
                        cfg = PROVIDER_CONFIGS.get(provider, {})
                        base_url = cfg.get("base_url", "")
                        model = preferred_model or cfg.get("default_model", "")
                        async for chunk in call_openai_compatible(
                            provider_name=provider,
                            base_url=base_url,
                            key=key_node.key,
                            messages=messages,
                            model=model,
                            stream=True,
                        ):
                            tokens_streamed += 1
                            yield chunk

                    # If we yielded content successfully, record success and return
                    if tokens_streamed > 0:
                        self.pool.record_success(provider, key_node.key, tokens_used=tokens_streamed)
                        return

                except ProviderExecutionError as p_err:
                    logger.warning(f"Provider [{provider}] execution failure: {p_err.status_code} - {p_err.message[:120]}")
                    self.pool.record_failure(provider, key_node.key, p_err.status_code)
                    # Loop back to try the next key for this provider or move to next provider
                    continue
                except Exception as e:
                    logger.warning(f"Unexpected error executing [{provider}]: {str(e)[:120]}")
                    self.pool.record_failure(provider, key_node.key, 500)
                    continue

        # If all pooled keys failed or no keys are configured, use Public Emergency Fallback
        logger.warning("All pooled provider keys exhausted or unconfigured. Engaging zero-cost public emergency fallback...")
        try:
            async for chunk in call_public_fallback(messages=messages, stream=True):
                yield chunk
        except Exception as e:
            logger.error(f"Critical: Emergency public fallback failed: {str(e)}")
            yield "I am currently undergoing scheduled system recalibration. Please verify your connection or try again shortly."

    async def complete_chat(
        self,
        messages: List[Dict[str, str]],
        preferred_model: Optional[str] = None,
    ) -> str:
        """Non-streaming version of completion."""
        chunks = []
        async for chunk in self.stream_chat(messages=messages, preferred_model=preferred_model):
            chunks.append(chunk)
        return "".join(chunks)


smart_router = SmartRouter()
