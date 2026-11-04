"""
High-Capacity 50+ Key Pool Manager with Leaky-Bucket Rate Limiting & Circuit Breakers.
Distributes request loads across multiple provider keys and manages automatic cooldowns.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from config.settings import settings

logger = logging.getLogger("shivai.router.key_pool")


class KeyState(str, Enum):
    ACTIVE = "ACTIVE"
    COOLING_DOWN = "COOLING_DOWN"
    EXHAUSTED = "EXHAUSTED"


@dataclass
class APIKeyNode:
    provider: str
    key: str
    rpm_limit: int = 15
    state: KeyState = KeyState.ACTIVE
    consecutive_failures: int = 0
    cooldown_until: float = 0.0
    last_used_at: float = 0.0
    total_requests: int = 0
    total_tokens: int = 0
    request_timestamps: List[float] = field(default_factory=list)

    @property
    def current_rpm(self) -> int:
        """Calculates current requests in the last 60 seconds (Leaky Bucket)."""
        now = time.time()
        self.request_timestamps = [t for t in self.request_timestamps if now - t < 60.0]
        return len(self.request_timestamps)

    def is_available(self) -> bool:
        """Determines if key is active, out of cooldown, and below RPM limit."""
        now = time.time()
        if self.state == KeyState.COOLING_DOWN:
            if now >= self.cooldown_until:
                # Cooldown period ended; probe key
                self.state = KeyState.ACTIVE
                self.consecutive_failures = 0
                logger.info(f"Key [{self.provider}] {self.key[:8]}... recovered from cooldown.")
            else:
                return False

        if self.state == KeyState.EXHAUSTED:
            return False

        return self.current_rpm < self.rpm_limit

    def mark_used(self) -> None:
        now = time.time()
        self.last_used_at = now
        self.total_requests += 1
        self.request_timestamps.append(now)


class KeyPoolManager:
    """Manages multi-provider API key pools with automatic health checking and failover."""

    def __init__(self):
        # provider -> list of APIKeyNode
        self.pools: Dict[str, List[APIKeyNode]] = {
            "gemini": [],
            "groq": [],
            "cerebras": [],
            "sambanova": [],
            "mistral": [],
            "huggingface": [],
            "openrouter": [],
        }
        self.cooldown_duration_seconds: float = 600.0  # 10 minutes
        self.initialize_keys_from_settings()

    def initialize_keys_from_settings(self) -> None:
        """Loads API keys from environment settings into provider pools."""
        self._load_keys("gemini", settings.GEMINI_API_KEYS, default_rpm=15)
        self._load_keys("groq", settings.GROQ_API_KEYS, default_rpm=30)
        self._load_keys("cerebras", settings.CEREBRAS_API_KEYS, default_rpm=30)
        self._load_keys("sambanova", settings.SAMBANOVA_API_KEYS, default_rpm=30)
        self._load_keys("mistral", settings.MISTRAL_API_KEYS, default_rpm=20)
        self._load_keys("huggingface", settings.HUGGINGFACE_TOKENS, default_rpm=10)
        self._load_keys("openrouter", settings.OPENROUTER_API_KEYS, default_rpm=20)

    def _load_keys(self, provider: str, raw_keys: str, default_rpm: int = 15) -> None:
        if not raw_keys:
            return
        keys = [k.strip() for k in raw_keys.split(",") if k.strip()]
        for key in keys:
            self.add_key(provider, key, rpm_limit=default_rpm)

    def add_key(self, provider: str, key: str, rpm_limit: int = 15) -> None:
        """Dynamically registers an API key into the specified provider pool."""
        if provider not in self.pools:
            self.pools[provider] = []

        # Avoid duplicate keys
        if any(node.key == key for node in self.pools[provider]):
            return

        self.pools[provider].append(
            APIKeyNode(provider=provider, key=key, rpm_limit=rpm_limit)
        )
        logger.info(f"Registered key for [{provider}] (Pool size: {len(self.pools[provider])})")

    def get_next_key(self, provider: str) -> Optional[APIKeyNode]:
        """Selects the healthiest, least-recently-used key with available capacity."""
        pool = self.pools.get(provider, [])
        if not pool:
            return None

        # Filter available keys
        available = [node for node in pool if node.is_available()]
        if not available:
            return None

        # Sort by least recently used
        available.sort(key=lambda n: n.last_used_at)
        selected = available[0]
        selected.mark_used()
        return selected

    def record_failure(self, provider: str, key: str, status_code: int) -> None:
        """Handles rate limits or error responses by tripping circuit breaker."""
        node = self._find_node(provider, key)
        if not node:
            return

        node.consecutive_failures += 1
        now = time.time()

        # 429 Too Many Requests or Quota Exhaustion
        if status_code in (429, 403):
            node.state = KeyState.COOLING_DOWN
            node.cooldown_until = now + self.cooldown_duration_seconds
            logger.warning(
                f"Rate limit 429 on [{provider}] key {key[:8]}...! Quarantined for {int(self.cooldown_duration_seconds / 60)} minutes."
            )
        elif node.consecutive_failures >= 3:
            # 3 consecutive network/5xx failures -> temporary 2-min cooldown
            node.state = KeyState.COOLING_DOWN
            node.cooldown_until = now + 120.0
            logger.warning(f"Repeated failures on [{provider}] key {key[:8]}...! Cooldown for 2 minutes.")

    def record_success(self, provider: str, key: str, tokens_used: int = 0) -> None:
        """Resets failure counter and records token usage."""
        node = self._find_node(provider, key)
        if node:
            node.consecutive_failures = 0
            node.total_tokens += tokens_used

    def _find_node(self, provider: str, key: str) -> Optional[APIKeyNode]:
        for node in self.pools.get(provider, []):
            if node.key == key:
                return node
        return None

    def get_status_summary(self) -> Dict[str, Any]:
        """Returns telemetry overview across all key pools."""
        summary = {}
        for prov, nodes in self.pools.items():
            active_count = sum(1 for n in nodes if n.is_available())
            cooling_count = sum(1 for n in nodes if n.state == KeyState.COOLING_DOWN)
            total_reqs = sum(n.total_requests for n in nodes)
            summary[prov] = {
                "total_keys": len(nodes),
                "active_keys": active_count,
                "cooling_down": cooling_count,
                "total_requests_served": total_reqs,
            }
        return summary


key_pool = KeyPoolManager()
