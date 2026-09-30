from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt hashes at most 72 bytes and rejects anything longer, so the API layer
# must cap password length before calling hash_password.
MAX_PASSWORD_BYTES = 72


def hash_password(password: str) -> str:
    """Hash a plaintext password.

    bcrypt generates a random salt per call and stores it inside the returned
    hash, so no separate salt column is needed.
    """
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed_password.encode())


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Issue a signed JWT. `subject` is the user id, stored in the `sub` claim."""
    expires_delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "exp": datetime.now(UTC) + expires_delta,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Return the subject of a valid token.

    Raises jwt.InvalidTokenError (including expiry and bad signature) so the
    caller decides how to surface the failure; this module stays HTTP-agnostic.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    subject = payload.get("sub")
    if not subject:
        raise jwt.InvalidTokenError("Token is missing a subject")
    return subject
