"""
SHIV Native Authentication & Identity Router.
Provides production registration, Argon2id login, session management, and JWT token rotation.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from core.auth.security import (
    UserContext,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from core.db.client import db_client

logger = logging.getLogger("shivai.api.auth")
router = APIRouter(prefix="/auth", tags=["SHIV Native Auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    username: str
    display_name: Optional[str] = None


class LoginRequest(BaseModel):
    identifier: str  # Email or username
    password: str
    device_info: Optional[str] = "Web/Browser"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, request: Request):
    """Creates a new user account in SHIV DB with Argon2id password encryption."""
    client_ip = request.client.host if request.client else "127.0.0.1"

    # Check if user already exists
    existing = db_client.get_user_for_login(req.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "USER_EXISTS", "message": f"User with email '{req.email}' already exists."}},
        )

    # Hash password with Argon2id
    pw_hash = get_password_hash(req.password)

    try:
        user_res = db_client.create_user(
            email=req.email,
            username=req.username,
            hashed_password=pw_hash,
            display_name=req.display_name or req.username,
        )
        user_id = user_res["id"]
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": {"code": "REGISTRATION_FAILED", "message": "Failed to create user record."}},
        )

    # Issue initial tokens and create session
    access_token = create_access_token(user_id=user_id, email=req.email, role="user")
    raw_refresh, refresh_hash, refresh_exp = create_refresh_token()
    session_id = db_client.create_session(
        user_id=user_id,
        refresh_token_hash=refresh_hash,
        expires_at=refresh_exp,
        device_info="Registration Initializer",
        ip_address=client_ip,
    )

    db_client.log_audit(
        request_id=session_id,
        user_id=user_id,
        event_type="AUTH",
        operation="REGISTER",
        status="SUCCESS",
        details={"email": req.email, "username": req.username},
        ip_address=client_ip,
    )

    return {
        "success": True,
        "user": {
            "id": user_id,
            "email": req.email,
            "username": req.username,
            "display_name": req.display_name or req.username,
            "role": "user",
        },
        "session_id": session_id,
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
    }


@router.post("/login")
async def login(req: LoginRequest, request: Request):
    """Authenticates credentials against SHIV DB and issues session tokens."""
    client_ip = request.client.host if request.client else "127.0.0.1"

    user = db_client.get_user_for_login(req.identifier)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email, username, or password."}},
        )

    stored_hash = user.get("hashed_password") or user.get("password_hash") or ""
    if not verify_password(req.password, stored_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email, username, or password."}},
        )

    if user.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "ACCOUNT_INACTIVE", "message": "Your account is currently disabled."}},
        )

    user_id = user["id"]
    role = user.get("role", "user")

    # Generate HS256 JWT access token and cryptographic refresh token
    access_token = create_access_token(user_id=user_id, email=user["email"], role=role)
    raw_refresh, refresh_hash, refresh_exp = create_refresh_token()

    session_id = db_client.create_session(
        user_id=user_id,
        refresh_token_hash=refresh_hash,
        expires_at=refresh_exp,
        device_info=req.device_info or "Unknown Device",
        ip_address=client_ip,
    )

    db_client.log_audit(
        request_id=session_id,
        user_id=user_id,
        event_type="AUTH",
        operation="LOGIN",
        status="SUCCESS",
        details={"identifier": req.identifier},
        ip_address=client_ip,
    )

    return {
        "success": True,
        "user": {
            "id": user_id,
            "shiv_id": user.get("shiv_id"),
            "email": user["email"],
            "username": user["username"],
            "display_name": user.get("display_name"),
            "role": role,
            "avatar_url": user.get("avatar_url"),
        },
        "session_id": session_id,
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
    }


@router.post("/refresh")
async def refresh_token(req: RefreshRequest):
    """Rotates access token using a valid, non-revoked refresh token."""
    refresh_hash = hashlib.sha256(req.refresh_token.encode()).hexdigest()
    session = db_client.get_valid_session_by_hash(refresh_hash)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "INVALID_REFRESH_TOKEN", "message": "Refresh token is invalid or has been revoked."}},
        )

    access_token = create_access_token(
        user_id=session["user_id"],
        email=session["email"],
        role=session["role"],
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/logout")
async def logout(req: LogoutRequest, current_user: UserContext = Depends(get_current_user)):
    """Revokes active session."""
    if req.refresh_token:
        refresh_hash = hashlib.sha256(req.refresh_token.encode()).hexdigest()
        db_client.revoke_session(refresh_hash)

    return {"success": True, "message": "Session invalidated successfully."}


@router.get("/me")
async def get_me(current_user: UserContext = Depends(get_current_user)):
    """Returns caller's verified profile data from SHIV DB."""
    return {
        "id": current_user.user_id,
        "shiv_id": current_user.shiv_id,
        "email": current_user.email,
        "username": current_user.username,
        "role": current_user.role,
        "status": current_user.status,
    }
