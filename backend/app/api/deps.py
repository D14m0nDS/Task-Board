import uuid
from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.services import user_service

# auto_error=False so a missing header reaches our code and produces a 401;
# the default behaviour would return 403, which is misleading here.
bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """One session per request, always closed.

    Committing is left to the service layer so a request can span several
    writes and still fail as a single unit.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Resolve the bearer token into a user, or reject the request.

    Every failure returns the same message so the response cannot be used to
    probe which user ids or emails exist.
    """
    if credentials is None:
        raise _unauthorized()

    try:
        subject = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(subject)
    except (jwt.InvalidTokenError, ValueError):
        raise _unauthorized() from None

    user = user_service.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
