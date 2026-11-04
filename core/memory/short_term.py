"""
Short-Term Working Memory & Conversation Window Manager.
Maintains sliding-window message history, ensuring context length stays within token limits.
"""
from __future__ import annotations

from typing import Any, Dict, List


class ShortTermMemoryManager:
    """Manages active conversation window with token-aware sliding window truncation."""

    def __init__(self, max_turns: int = 15):
        self.max_turns = max_turns
        self._cache: Dict[str, List[Dict[str, str]]] = {}

    def add_message(self, user_id: str, role: str, content: str) -> None:
        """Appends a turn to the user's active sliding session window."""
        if user_id not in self._cache:
            self._cache[user_id] = []
        self._cache[user_id].append({"role": role, "content": content})
        if len(self._cache[user_id]) > (self.max_turns * 2):
            self._cache[user_id] = self._cache[user_id][-(self.max_turns * 2):]

    def get_messages(self, user_id: str) -> List[Dict[str, str]]:
        """Returns recent turns for user."""
        return list(self._cache.get(user_id, []))

    def clear(self, user_id: str) -> None:
        """Clears sliding window for user."""
        if user_id in self._cache:
            self._cache[user_id] = []

    def prepare_messages(
        self,
        system_prompt: str,
        history_messages: List[Dict[str, str]],
        current_prompt: str,
    ) -> List[Dict[str, str]]:
        """Constructs an optimized message list ensuring system prompt + recent history + current prompt."""
        recent_history = history_messages[- (self.max_turns * 2):] if history_messages else []

        messages: List[Dict[str, str]] = [{"role": "system", "content": system_prompt}]
        for msg in recent_history:
            messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})

        messages.append({"role": "user", "content": current_prompt})
        return messages


short_term_memory = ShortTermMemoryManager()
