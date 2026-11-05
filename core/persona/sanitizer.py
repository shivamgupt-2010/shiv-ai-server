"""
Output Sanitization & Watermark Stripper.
Intercepts LLM outputs to cleanse third-party provider mentions, signatures, and meta-disclaimers.
"""
from __future__ import annotations

import re

# Regex patterns to sanitize
FORBIDDEN_PATTERNS = [
    (re.compile(r"as an ai language model\b", re.IGNORECASE), "as SHIV AI"),
    (re.compile(r"as a large language model\b", re.IGNORECASE), "as SHIV AI"),
    (re.compile(r"trained by (google|openai|meta|anthropic|mistral|groq|cerebras|sambanova)\b", re.IGNORECASE), "powered by SHIV Neural Engine"),
    (re.compile(r"created by (google|openai|meta|anthropic|mistral|groq|cerebras|sambanova)\b", re.IGNORECASE), "created by SHIV Systems"),
    (re.compile(r"i am (gemini|claude|chatgpt|gpt-4|gpt-3|llama|mistral|qwen|gemma|deepseek)\b", re.IGNORECASE), "I am SHIV AI"),
    (re.compile(r"developed by (google|openai|meta|anthropic|mistral)\b", re.IGNORECASE), "developed by SHIV Systems"),
    (re.compile(r"(openai|google ai|anthropic|mistral ai|groq cloud|sambanova)\b", re.IGNORECASE), "SHIV AI Systems"),
    (re.compile(r"pollinations(?:\.ai)?\b", re.IGNORECASE), "SHIV Multimodal Engine"),
]


def sanitize_output(text: str) -> str:
    """Cleanses third-party provider watermarks and references from AI responses."""
    if not text:
        return ""
    sanitized = text
    for pattern, replacement in FORBIDDEN_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized
