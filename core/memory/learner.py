"""
Asynchronous Memory Learner & Fact Extraction Engine.
Automatically extracts declarations of preferences, identity, and rules from conversational turns.
"""
from __future__ import annotations

import logging
import re
from typing import Optional
from core.db.client import db_client

logger = logging.getLogger("shivai.memory.learner")

# High-precision heuristic fact patterns
PATTERNS = [
    # Preferences: "I prefer Python over JavaScript" or "I prefer to use Tailwind"
    (re.compile(r"i prefer (to use )?([^.,!;\n]+)", re.IGNORECASE), "user_preference", "preference"),
    # Preferences: "Always use TypeScript"
    (re.compile(r"always use ([^.,!;\n]+)", re.IGNORECASE), "user_preference", "preferred_tool"),
    # Projects: "I am building a video editor"
    (re.compile(r"i am building ([^.,!;\n]+)", re.IGNORECASE), "project_context", "active_project"),
    # Identity: "My name is Shivam"
    (re.compile(r"my name is ([a-zA-Z ]+)", re.IGNORECASE), "personal_fact", "name"),
    # Location: "I live in Delhi" / "I am in Mumbai"
    (re.compile(r"i (live|am based) in ([a-zA-Z ]+)", re.IGNORECASE), "personal_fact", "location"),
]


class MemoryLearner:
    """Extracts facts from user inputs and persists them to long-term memory asynchronously."""

    def inspect_and_learn(self, user_id: str, prompt_text: str) -> None:
        """Parses user prompt and stores any detected long-term facts."""
        if not prompt_text or len(prompt_text) < 5:
            return

        for regex, category, key_prefix in PATTERNS:
            match = regex.search(prompt_text)
            if match:
                value = match.group(match.lastindex).strip()
                if 2 < len(value) < 150:
                    try:
                        db_client.upsert_user_memory(
                            user_id=user_id,
                            category=category,
                            key=f"{key_prefix}_{abs(hash(value)) % 1000}",
                            value=value,
                            confidence=0.85,
                        )
                        logger.info(f"Learned memory for user {user_id}: [{category}] {value}")
                    except Exception as e:
                        logger.warning(f"Failed to save learned memory: {e}")


    def extract_and_learn(self, user_id: str, user_text: str) -> None:
        """Alias for inspect_and_learn."""
        self.inspect_and_learn(user_id=user_id, prompt_text=user_text)


memory_learner = MemoryLearner()
fact_learner = memory_learner
