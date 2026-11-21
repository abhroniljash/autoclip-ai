"""JWT authentication and password hashing for AutoClip AI."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Generator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = max(5, int(os.environ.get("ACCESS_TOKEN_MINUTES", "60")))
password_hash = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


def _require_secret() -> str:
    if len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must be configured with at least 32 characters.")
    return JWT_SECRET


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return password_hash.verify(password, encoded)
    except Exception:
        return False


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user.id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
        "iss": "autoclip-ai",
        "aud": "autoclip-api",
    }
    return jwt.encode(payload, _require_secret(), algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            _require_secret(),
            algorithms=[JWT_ALGORITHM],
            issuer="autoclip-ai",
            audience="autoclip-api",
            options={"require": ["sub", "exp", "iat", "iss", "aud"]},
        )
        user_id = payload.get("sub")
    except (jwt.PyJWTError, RuntimeError):
        raise unauthorized
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise unauthorized
    return user
