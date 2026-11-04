"""
Long-Term Episodic & Semantic Memory Manager.
Retrieves and indexes persistent user facts, preferences, and project settings from SHIV DB.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from core.db.client import db_client


class LongTermMemoryManager:
    """Interfaces with SHIV DB generic_records to retrieve persistent memories."""

    def get_memories_for_user(self, user_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Fetches active user memories sorted by access frequency and recency."""
        return db_client.get_user_memories(user_id=user_id, limit=limit)

    def get_memories(self, user_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Public alias for get_memories_for_user."""
        return self.get_memories_for_user(user_id=user_id, limit=limit)

    def save_memory(
        self,
        user_id: str,
        category: str,
        key: str,
        value: str,
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """Explicitly records a persistent user preference or fact."""
        return db_client.upsert_user_memory(
            user_id=user_id,
            category=category,
            key=key,
            value=value,
            confidence=confidence,
        )


long_term_memory = LongTermMemoryManager()
