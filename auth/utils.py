import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from config import settings
from exceptions import UnauthorizedError


def generate_jwt_token(user_id: uuid.UUID) -> str:
    """Generate a signed JWT containing user_id. Expiry from config."""
    payload = {
        "user_id": str(user_id),
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict:
    """Decode and verify a JWT. Raises UnauthorizedError if invalid or expired."""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise UnauthorizedError(f"Invalid or expired token: {exc}") from exc
