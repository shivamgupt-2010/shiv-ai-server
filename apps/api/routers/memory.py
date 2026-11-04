"""
Two-Tier Persistent Memory Management Router.
Allows users and client applications to view, query, and curate long-term user memories.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from core.auth.security import UserContext, get_current_user
from core.db.client import db_client
from core.memory.long_term import long_term_memory

logger = logging.getLogger("shivai.api.memory")
router = APIRouter(prefix="/memory", tags=["Two-Tier Memory Management"])


class StoreMemoryRequest(BaseModel):
    category: str = Field(..., description="Memory classification (e.g. preference, profile, project)")
    key: str = Field(..., description="Unique attribute identifier")
    value: str = Field(..., description="Attribute fact or description")
    confidence: Optional[float] = 1.0


@router.get("")
async def list_memories(
    limit: int = 50,
    current_user: UserContext = Depends(get_current_user),
):
    """Retrieves all persistent long-term memories for the authenticated caller."""
    memories = long_term_memory.get_memories(user_id=current_user.user_id, limit=limit)
    return {
        "user_id": current_user.user_id,
        "count": len(memories),
        "memories": memories,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_memory(
    req: StoreMemoryRequest,
    current_user: UserContext = Depends(get_current_user),
):
    """Explicitly commits or updates a personal preference or context fact into long-term memory."""
    res = long_term_memory.save_memory(
        user_id=current_user.user_id,
        category=req.category,
        key=req.key,
        value=req.value,
        confidence=req.confidence or 1.0,
    )
    return {"success": True, "memory": res}


@router.delete("/{record_id}")
async def delete_memory(
    record_id: str,
    current_user: UserContext = Depends(get_current_user),
):
    """Removes a long-term memory entry."""
    conn = db_client.get_connection()
    try:
        res = conn.execute(
            "DELETE FROM generic_records WHERE project_id = ? AND collection = 'memories' AND record_id = ?",
            (current_user.user_id, record_id),
        )
        conn.commit()
        if res.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": {"code": "MEMORY_NOT_FOUND", "message": "Memory record not found."}},
            )
        return {"success": True, "message": f"Memory '{record_id}' deleted."}
    finally:
        conn.close()
