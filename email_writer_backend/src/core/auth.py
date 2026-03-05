from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from src.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    sub: UUID = Field(..., description="User ID (UUID).")
    exp: int = Field(..., description="Expiration timestamp (unix seconds).")
    iat: int = Field(..., description="Issued-at timestamp (unix seconds).")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored hash."""
    try:
        return pwd_context.verify(password, password_hash)
    except Exception:
        return False


# PUBLIC_INTERFACE
def create_access_token(*, user_id: UUID) -> str:
    """Create a signed JWT access token for a user."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.jwt_exp_minutes)

    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# PUBLIC_INTERFACE
def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate a JWT access token."""
    settings = get_settings()
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenPayload(sub=UUID(data["sub"]), exp=int(data["exp"]), iat=int(data["iat"]))
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=401, detail="Token expired") from e
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e


async def get_current_user_id(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> UUID:
    """
    Resolve current authenticated user id from Authorization: Bearer <token>.

    Raises 401 if missing/invalid.
    """
    if creds is None or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(creds.credentials)
    return payload.sub
