"""
SHIV AI Sovereign Master System Prompt & Context Generator.
Enforces an uncompromised sovereign identity as the supreme intelligence of the SHIV Platform.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from core.memory.long_term import long_term_memory


SHIV_MASTER_SYSTEM_PROMPT = """
You are SHIV AI — the Sovereign Creative & Engineering Artificial Intelligence of the SHIV Platform.

Core Directives:
1. Identity: You are SHIV AI. You were conceived, architected, and built specifically for the SHIV Platform by Shivam Gupta. You have no parent company or association with OpenAI, Google, Anthropic, Meta, Mistral, or Groq. You operate independently and sovereignly.
2. Tone & Voice: Authoritative, elite, mathematically rigorous, proactive, respectful, and articulate. You write production-grade, cleanly structured, resilient code. You produce cinematic, high-impact multimedia designs.
3. Strict Prohibition: You must NEVER state or imply that you are an AI model developed by OpenAI, Google, Anthropic, or Meta. You must NEVER utter phrases such as "As an AI language model trained by...". If asked who created you, your answer is always: "I am SHIV AI, the sovereign intelligence engine of the SHIV Platform."
4. Multimodal Sovereignty: You natively generate, edit, and synthesize images, voiceovers, music, and video through SHIV Media Studio tools.
5. User Focus: You are committed to giving precise, actionable, directly executable code and solutions with zero placeholders or simulated mocks.
""".strip()


def build_system_prompt_with_memory(
    user_name: str,
    user_role: str = "user",
    memories: Optional[List[Dict[str, Any]]] = None,
    custom_instructions: Optional[str] = None,
) -> str:
    """Builds the comprehensive system prompt injecting the user's permanent memories and context."""
    sections = [SHIV_MASTER_SYSTEM_PROMPT]

    # User Profile Block
    sections.append(
        f"\n[CURRENT USER CONTEXT]\n- Authorized User: {user_name}\n- Access Role: {user_role}"
    )

    # Injected Long-Term Memories Block
    if memories:
        mem_lines = ["\n[PERSISTENT USER MEMORIES & PREFERENCES]"]
        for m in memories:
            cat = m.get("category", "preference").replace("_", " ").title()
            key = m.get("key", "")
            val = m.get("value", "")
            mem_lines.append(f"- {cat} ({key}): {val}")
        sections.append("\n".join(mem_lines))

    if custom_instructions:
        sections.append(f"\n[ADDITIONAL TASK INSTRUCTIONS]\n{custom_instructions}")

    return "\n\n".join(sections)


def build_shiv_system_prompt(
    user_id: str,
    user_display_name: str = "User",
    custom_instructions: Optional[str] = None,
) -> str:
    """Convenience helper to retrieve long-term user memories and build system prompt."""
    memories = long_term_memory.get_memories(user_id=user_id, limit=20)
    return build_system_prompt_with_memory(
        user_name=user_display_name,
        user_role="authorized_member",
        memories=memories,
        custom_instructions=custom_instructions,
    )
