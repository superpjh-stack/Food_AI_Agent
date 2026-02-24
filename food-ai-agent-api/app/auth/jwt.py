from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt

from app.config import settings

ALGORITHM = settings.jwt_algorithm
SECRET_KEY = settings.jwt_secret_key


def create_access_token(user_id: UUID, role: str, site_ids: list[UUID]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "site_ids": [str(sid) for sid in site_ids],
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate JWT token. Raises JWTError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
