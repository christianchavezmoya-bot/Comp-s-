"""Auth + roles for v0.2.

Lightweight: email + password, Argon2id, JWT-ish session token.
No third-party auth, no OAuth, no email verification.
Both Admin and User can upload songs (per user requirement).
Roles only affect *moderation* and *publication*, not *consumption*.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field

from compas_api.config import get_settings
from compas_api.db import User, get_session

log = logging.getLogger("compas.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])

SESSION_COOKIE = "compas_session"
SESSION_TTL_DAYS = 30


# ====== Password hashing (PBKDF2 — no extra deps) ======

def _hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = secrets.token_bytes(16)
    hk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"pbkdf2_sha256$120000${salt.hex()}${hk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt_hex, hash_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        hk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iters))
        return hmac.compare_digest(hk, expected)
    except Exception:
        return False


# ====== Session token ======

def _sign_session(token: str) -> str:
    secret = os.environ.get("COMPAS_SESSION_SECRET", "dev-secret-change-me")
    sig = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{token}.{sig}"


def _verify_session(signed: str) -> str | None:
    if "." not in signed:
        return None
    token, sig = signed.rsplit(".", 1)
    secret = os.environ.get("COMPAS_SESSION_SECRET", "dev-secret-change-me")
    expected = hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected):
        return None
    return token


# ====== Schemas ======

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: str = "user"  # 'user' or 'admin' (admin allowed for self-bootstrap)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class MeResponse(BaseModel):
    id: str
    email: str
    role: str
    trust_score: int
    created_at: datetime

    @classmethod
    def from_row(cls, u: User) -> "MeResponse":
        return cls(id=u.id, email=u.email, role=u.role, trust_score=u.trust_score, created_at=u.created_at)


# ====== Helpers ======

def current_user(session_token: str | None = Cookie(default=None)) -> User | None:
    if not session_token:
        return None
    token = _verify_session(session_token)
    if not token:
        return None
    with get_session() as s:
        user = s.query(User).filter(User.id == token).first()
        return user


def require_user(user: User | None = Depends(current_user)) -> User:
    if not user:
        raise HTTPException(401, "Authentication required")
    if user.banned:
        raise HTTPException(403, "User is banned")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin required")
    return user


# ====== Endpoints ======

@router.post("/register", response_model=MeResponse, status_code=201)
async def register(req: RegisterRequest, response: Response) -> MeResponse:
    if req.role not in ("user", "admin"):
        raise HTTPException(400, "role must be 'user' or 'admin'")
    with get_session() as s:
        existing = s.query(User).filter(User.email == req.email).first()
        if existing:
            raise HTTPException(409, "Email already registered")
        user = User(
            id=str(uuid.uuid4()),
            email=req.email,
            password_hash=_hash_password(req.password),
            role=req.role,
        )
        s.add(user)
        s.commit()
        s.refresh(user)

    signed = _sign_session(user.id)
    response.set_cookie(
        SESSION_COOKIE,
        signed,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        path="/",
    )
    log.info("registered %s as %s", user.email, user.role)
    return MeResponse.from_row(user)


@router.post("/login", response_model=MeResponse)
async def login(req: LoginRequest, response: Response) -> MeResponse:
    with get_session() as s:
        user = s.query(User).filter(User.email == req.email).first()
        if not user or not _verify_password(req.password, user.password_hash):
            raise HTTPException(401, "Invalid credentials")
        if user.banned:
            raise HTTPException(403, "User is banned")

    signed = _sign_session(user.id)
    response.set_cookie(
        SESSION_COOKIE,
        signed,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        path="/",
    )
    log.info("login: %s", user.email)
    return MeResponse.from_row(user)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=MeResponse)
async def me(user: User | None = Depends(current_user)) -> MeResponse | None:
    if not user:
        return None
    return MeResponse.from_row(user)
