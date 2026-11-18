from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

import bcrypt
import jwt
from fastapi import HTTPException

from app.config import get_settings

# bcrypt only uses the first 72 bytes; passlib truncated silently, so keep that
# behaviour for existing passwords instead of rejecting them.
_BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return str(password or "").encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_password_bytes(plain_password), str(hashed_password or "").encode("ascii"))
    except (ValueError, TypeError):
        # Not a bcrypt hash (or malformed): never a match.
        return False


def decode_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload


def create_access_token(payload: Dict[str, Any]) -> str:
    settings = get_settings()

    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {**payload, "exp": expire, "type": "access"}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(payload: Dict[str, Any]) -> str:
    settings = get_settings()

    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {**payload, "exp": expire, "type": "refresh", "jti": str(uuid4())}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

