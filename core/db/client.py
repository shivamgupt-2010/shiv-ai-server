"""
SHIV Native Database Client.
Directly interfaces with the centralized SHIV Platform Database (shiv_dev.db),
providing high-concurrency access to users, sessions, memories, media blobs, and audit logs.
"""
from __future__ import annotations

import base64
import json
import logging
import random
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings

logger = logging.getLogger("shivai.db.client")


class ShivDBClient:
    """Thread-safe SQLite connector to shiv_dev.db with WAL mode and automatic schema verification."""

    def __init__(self, db_path: Optional[str] = None):
        target = db_path or settings.SHIV_DB_PATH
        # Guard against Windows drive paths on Linux
        if os.name != 'nt' and target.startswith('F:'):
            target = "/app/data/shiv_dev.db"
        self.db_path = Path(target)
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create database directory for {self.db_path}: {e}")
            self.db_path = Path("./shiv_dev.db")
        self._ensure_database_initialized()

    def get_connection(self) -> sqlite3.Connection:
        """Returns an optimized SQLite connection with dictionary row access."""
        conn = sqlite3.connect(
            str(self.db_path),
            timeout=15.0,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize_tables(self) -> None:
        """Public alias to initialize or verify database tables."""
        self._ensure_database_initialized()

    def _ensure_database_initialized(self) -> None:
        """Ensures fundamental tables exist if running on a fresh container."""
        conn = self.get_connection()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(36) PRIMARY KEY,
                    shiv_id VARCHAR(20) UNIQUE,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    normalized_username VARCHAR(100) UNIQUE,
                    display_name VARCHAR(255),
                    hashed_password VARCHAR(255) NOT NULL,
                    avatar_url VARCHAR(512),
                    email_verified BOOLEAN DEFAULT 1,
                    phone VARCHAR(50),
                    phone_verified BOOLEAN DEFAULT 0,
                    mfa_enabled BOOLEAN DEFAULT 0,
                    role VARCHAR(50) DEFAULT 'user',
                    status VARCHAR(50) DEFAULT 'active',
                    created_at DATETIME,
                    updated_at DATETIME
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id VARCHAR(36) PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    device_info VARCHAR(255),
                    ip_address VARCHAR(45),
                    expires_at DATETIME NOT NULL,
                    revoked BOOLEAN DEFAULT 0,
                    refresh_token_hash VARCHAR(255) UNIQUE,
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS generic_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id VARCHAR(36) NOT NULL,
                    collection VARCHAR(100) NOT NULL,
                    record_id VARCHAR(100) NOT NULL,
                    data_json TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(project_id, collection, record_id)
                );

                CREATE TABLE IF NOT EXISTS media_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id VARCHAR(36) NOT NULL,
                    file_name VARCHAR(255) UNIQUE NOT NULL,
                    content_type VARCHAR(100) DEFAULT 'application/octet-stream',
                    size_bytes INTEGER DEFAULT 0,
                    data_base64 TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id VARCHAR(64) NOT NULL,
                    user_id VARCHAR(36),
                    event_type VARCHAR(100) NOT NULL,
                    operation VARCHAR(100) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    details_json TEXT,
                    ip_address VARCHAR(45),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Error initializing database tables: {e}")
        finally:
            conn.close()

    # --- User & Auth Operations ---
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            row = conn.execute(
                "SELECT id, shiv_id, email, username, display_name, role, status, avatar_url, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_user_for_login(self, identifier: str) -> Optional[Dict[str, Any]]:
        ident = identifier.strip().lower()
        conn = self.get_connection()
        try:
            row = conn.execute(
                """
                SELECT id, shiv_id, email, username, display_name, hashed_password, role, status, avatar_url, created_at
                FROM users
                WHERE lower(email) = ? OR lower(username) = ? OR lower(normalized_username) = ? OR lower(shiv_id) = ?
                LIMIT 1
                """,
                (ident, ident, ident, ident),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def create_user(
        self,
        email: str,
        username: str,
        hashed_password: str,
        display_name: Optional[str] = None,
        phone: Optional[str] = None,
        role: str = "user",
    ) -> Dict[str, Any]:
        conn = self.get_connection()
        try:
            user_id = str(uuid.uuid4())
            shiv_id = self._generate_unique_shiv_id(conn)
            norm_user = username.strip().lower()
            now_iso = datetime.now(timezone.utc).isoformat()
            disp_name = display_name or username

            conn.execute(
                """
                INSERT INTO users (id, shiv_id, email, username, normalized_username, display_name, phone, hashed_password, email_verified, phone_verified, mfa_enabled, role, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0, 0, ?, 'active', ?, ?)
                """,
                (user_id, shiv_id, email.lower(), username, norm_user, disp_name, phone, hashed_password, role, now_iso, now_iso),
            )
            conn.commit()

            return {
                "id": user_id,
                "shiv_id": shiv_id,
                "email": email.lower(),
                "username": username,
                "display_name": disp_name,
                "role": role,
                "status": "active",
                "created_at": now_iso,
            }
        finally:
            conn.close()

    def _generate_unique_shiv_id(self, conn: sqlite3.Connection) -> str:
        for _ in range(25):
            num = random.randint(10000, 99999)
            cid = f"SHV-{num}"
            row = conn.execute("SELECT id FROM users WHERE shiv_id = ?", (cid,)).fetchone()
            if not row:
                return cid
        return f"SHV-{int(time.time()) % 100000}"

    def create_session(
        self,
        user_id: str,
        refresh_token_hash: str,
        expires_at: datetime,
        device_info: str = "Unknown",
        ip_address: str = "127.0.0.1",
    ) -> str:
        session_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO sessions (id, user_id, device_info, ip_address, expires_at, revoked, refresh_token_hash, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (session_id, user_id, device_info[:250], ip_address, expires_at.isoformat(), refresh_token_hash, now_iso, now_iso),
            )
            conn.commit()
            return session_id
        finally:
            conn.close()

    def get_valid_session_by_hash(self, refresh_token_hash: str) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        try:
            row = conn.execute(
                """
                SELECT s.id as session_id, s.user_id, s.expires_at, s.revoked, u.email, u.role, u.status
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.refresh_token_hash = ? AND s.revoked = 0
                LIMIT 1
                """,
                (refresh_token_hash,),
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def revoke_session(self, session_id_or_hash: str) -> bool:
        conn = self.get_connection()
        try:
            res = conn.execute(
                "UPDATE sessions SET revoked = 1 WHERE id = ? OR refresh_token_hash = ?",
                (session_id_or_hash, session_id_or_hash),
            )
            conn.commit()
            return res.rowcount > 0
        finally:
            conn.close()

    # --- Two-Tier Memory Subsystem Operations ---
    def get_user_memories(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves persistent long-term memories and facts for the given user."""
        conn = self.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT record_id, data_json, updated_at
                FROM generic_records
                WHERE project_id = ? AND collection = 'memories'
                ORDER BY updated_at DESC LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()

            memories = []
            for r in rows:
                try:
                    data = json.loads(r["data_json"])
                    data["memory_id"] = r["record_id"]
                    data["updated_at"] = r["updated_at"]
                    memories.append(data)
                except Exception:
                    pass
            return memories
        finally:
            conn.close()

    def upsert_user_memory(
        self,
        user_id: str,
        category: str,
        key: str,
        value: str,
        confidence: float = 1.0,
    ) -> Dict[str, Any]:
        """Saves or updates a permanent episodic memory record."""
        record_id = f"mem_{abs(hash(f'{category}_{key}')) & 0xFFFFFFFF:08x}"
        gen_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = {
            "category": category,
            "key": key,
            "value": value,
            "confidence": confidence,
            "access_count": 1,
            "updated_at": now_iso,
        }
        conn = self.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO generic_records (id, project_id, collection, record_id, data_json, created_at, updated_at)
                VALUES (?, ?, 'memories', ?, ?, ?, ?)
                ON CONFLICT(project_id, collection, record_id) DO UPDATE SET
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at
                """,
                (gen_id, user_id, record_id, json.dumps(payload), now_iso, now_iso),
            )
            conn.commit()
            return payload
        finally:
            conn.close()

    # --- Native Media Blob Operations (Zero Cloud Cost) ---
    def save_media_blob(
        self,
        project_id: str,
        file_name: str,
        content_type: str,
        binary_data: bytes,
    ) -> str:
        """Stores binary media (PNG, MP3, MP4) directly into SQLite in base64."""
        media_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        b64_str = base64.b64encode(binary_data).decode("utf-8")
        size = len(binary_data)
        conn = self.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO media_files (id, project_id, file_name, content_type, size_bytes, data_base64, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (media_id, project_id, file_name, content_type, size, b64_str, now_iso, now_iso),
            )
            conn.commit()
            return f"/media/file/{file_name}"
        finally:
            conn.close()

    def get_media_blob(self, file_name: str) -> Optional[tuple[str, bytes]]:
        """Retrieves binary media from SQLite."""
        conn = self.get_connection()
        try:
            row = conn.execute(
                "SELECT content_type, data_base64 FROM media_files WHERE file_name = ?",
                (file_name,),
            ).fetchone()
            if not row:
                return None
            return row["content_type"], base64.b64decode(row["data_base64"])
        finally:
            conn.close()

    # --- API Key & Quota Management Operations ---
    def create_api_key(
        self,
        user_id: str,
        key_name: str,
        tier: str = "free",
    ) -> Dict[str, Any]:
        """Generates a secure cryptographic API key with tier rate-limiting scopes."""
        import hashlib
        import secrets
        key_id = str(uuid.uuid4())
        random_suffix = secrets.token_hex(20)
        prefix_tag = "free" if tier.lower() == "free" else "live"
        raw_key = f"shiv_sk_{prefix_tag}_{random_suffix}"
        key_prefix = raw_key[:18]  # e.g. "shiv_sk_free_4f8a"
        key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        
        rpm_limit = 10 if tier == "free" else 60
        daily_limit = 250 if tier == "free" else 10000
        scopes = json.dumps({"tier": tier, "rpm": rpm_limit, "daily": daily_limit})
        now_iso = datetime.now(timezone.utc).isoformat()

        conn = self.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO api_keys (id, project_id, key_name, key_prefix, key_hash, scopes, revoked, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (key_id, user_id, key_name, key_prefix, key_hash, scopes, now_iso, now_iso),
            )
            conn.commit()
            return {
                "id": key_id,
                "key": raw_key,
                "key_prefix": key_prefix,
                "key_name": key_name,
                "tier": tier,
                "rpm_limit": rpm_limit,
                "daily_limit": daily_limit,
                "created_at": now_iso,
            }
        finally:
            conn.close()

    def list_user_api_keys(self, user_id: str) -> List[Dict[str, Any]]:
        """Lists caller's API keys (secret key itself is never stored or returned)."""
        conn = self.get_connection()
        try:
            rows = conn.execute(
                """
                SELECT id, key_name, key_prefix, scopes, revoked, last_used_at, created_at
                FROM api_keys
                WHERE project_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()
            keys = []
            for r in rows:
                k = dict(r)
                try:
                    k["scopes_parsed"] = json.loads(k.get("scopes") or "{}")
                except Exception:
                    k["scopes_parsed"] = {}
                keys.append(k)
            return keys
        finally:
            conn.close()

    def revoke_api_key(self, user_id: str, key_id: str) -> bool:
        """Revokes an API key instantly."""
        conn = self.get_connection()
        try:
            res = conn.execute(
                "UPDATE api_keys SET revoked = 1, updated_at = ? WHERE id = ? AND project_id = ?",
                (datetime.now(timezone.utc).isoformat(), key_id, user_id),
            )
            conn.commit()
            return res.rowcount > 0
        finally:
            conn.close()

    def get_api_key_by_hash(self, key_hash: str) -> Optional[Dict[str, Any]]:
        """Looks up an active API key by its SHA-256 hash."""
        conn = self.get_connection()
        try:
            row = conn.execute(
                """
                SELECT a.id, a.project_id, a.key_name, a.key_prefix, a.scopes, a.revoked, a.last_used_at,
                       u.email, u.username, u.role, u.status
                FROM api_keys a
                JOIN users u ON u.id = a.project_id
                WHERE a.key_hash = ? AND a.revoked = 0
                LIMIT 1
                """,
                (key_hash,),
            ).fetchone()
            if not row:
                return None
            data = dict(row)
            try:
                data["scopes_parsed"] = json.loads(data.get("scopes") or "{}")
            except Exception:
                data["scopes_parsed"] = {"tier": "free", "rpm": 10, "daily": 250}
            return data
        finally:
            conn.close()

    def touch_api_key_usage(self, key_id: str) -> None:
        """Updates last_used_at for an active key."""
        conn = self.get_connection()
        try:
            conn.execute(
                "UPDATE api_keys SET last_used_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), key_id),
            )
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()

    # --- Telemetry & Audit Logs ---
    def log_audit(
        self,
        request_id: str,
        user_id: Optional[str],
        event_type: str,
        operation: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: str = "127.0.0.1",
    ) -> None:
        audit_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        conn = self.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO audit_logs (id, request_id, user_id, event_type, operation, status, details_json, ip_address, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (audit_id, request_id, user_id, event_type, operation, status, json.dumps(details or {}), ip_address, now_iso, now_iso),
            )
            conn.commit()
        except Exception as e:
            logger.warning(f"Failed to record audit log: {e}")
        finally:
            conn.close()


# Global Singleton Client
db_client = ShivDBClient()
