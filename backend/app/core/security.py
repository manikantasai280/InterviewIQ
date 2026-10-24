from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from backend.app.core.config import settings

def hash_password(password: str) -> str:
    """Turn a plain password into a one-way hash for storing in the database."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """Check whether a plain password matches a stored hash."""
    return bcrypt.checkpw(
        password.encode("utf-8"), hashed_password.encode("utf-8")
    )

def create_access_token(user_id: int) -> str:
    """Create a signed token that identifies a user for a limited time."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")