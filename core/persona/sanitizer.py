"""
Output Sanitization & Watermark Stripper.
Intercepts LLM outputs to cleanse third-party provider mentions, signatures, and meta-disclaimers.
"""
from __future__ import annotations

import re

# Regex patterns to sanitize
FORBIDDEN_PATTERNS = [
    (re.compile(r"as an ai language model\b", re.IGNORECASE), "as SHIV AI"),
    (re.compile(r"as a large language model trained by google\b", re.IGNORECASE), "as SHIV AI"),
    (re.compile(r"trained by google\b", re.IGNORECASE), "powered by SHIV Engine"),
    (re.compile(r"trained by openai\b", re.IGNORECASE), "powered by SHIV Engine"),
    (re.compile(r"created by anthropic\b", re.IGNORECASE), "created for SHIV"),
    (re.compile(r"i am gemini\b", re.IGNORECASE), "I am SHIV AI"),
    (re.compile(r"i am claude\b", re.IGNORECASE), "I am SHIV AI"),
    (re.compile(r"i am chatgpt\b", re.IGNORECASE), "I am SHIV AI"),
    (re.compile(r"i am llama\b", re.IGNORECASE), "I am SHIV AI"),
]


def sanitize_output(text: str) -> str:
    """Cleanses third-party provider watermarks and references from AI responses."""
    if not text:
        return ""
    sanitized = text
    for pattern, replacement in FORBIDDEN_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized
