"""Simple JWT-based authentication helpers for AgenticHR.

Two roles are supported:
  - "hr"       → access HR dashboard
  - "employee" → access Employee / Intern dashboard

Tokens are signed with AGENTHR_SECRET (default: dev-secret-change-in-prod).
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import bcrypt as _bcrypt
import jwt
from pydantic import BaseModel

# ── Config ────────────────────────────────────────────────────────────────
SECRET_KEY  = os.getenv("AGENTHR_SECRET", "dev-secret-change-in-prod")
ALGORITHM   = "HS256"
EXPIRE_MINS = int(os.getenv("TOKEN_EXPIRE_MINS", "480"))   # 8 hours


# ── Pydantic schemas ──────────────────────────────────────────────────────

class UserRecord(BaseModel):
    user_id:       str
    tenant_id:     str
    email:         str
    full_name:     str
    role:          str           # "hr" | "employee"
    department:    Optional[str] = None
    password_hash: str


class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    role:         str
    user_id:      str
    full_name:    str
    tenant_id:    str


# ── Helpers ───────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt.  Works with bcrypt 3.x/4.x/5.x."""
    salt = _bcrypt.gensalt()
    return _bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a stored bcrypt hash."""
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_token(user: UserRecord) -> str:
    payload = {
        "sub":       user.user_id,
        "tenant_id": user.tenant_id,
        "email":     user.email,
        "role":      user.role,
        "full_name": user.full_name,
        "exp":       datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify token. Raises jwt.InvalidTokenError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def user_to_dict(user: UserRecord) -> Dict[str, Any]:
    return {
        "user_id":       user.user_id,
        "tenant_id":     user.tenant_id,
        "email":         user.email,
        "full_name":     user.full_name,
        "role":          user.role,
        "department":    user.department,
        "password_hash": user.password_hash,
        "created_at":    datetime.now(timezone.utc),
    }
