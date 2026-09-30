import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


class EmailAlreadyRegisteredError(Exception):
    """Registration was attempted with an email that already exists."""


# Checking a throwaway hash when the email is unknown keeps the response time
# close to a real verification, so timing cannot be used to discover which
# emails are registered.
_DUMMY_HASH = hash_password("timing-equalisation-placeholder")


def normalise_email(email: str) -> str:
    """Postgres unique indexes are case sensitive, so store one canonical form."""
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == normalise_email(email)))


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def register_user(db: Session, payload: UserCreate) -> User:
    email = normalise_email(payload.email)

    if get_user_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError as exc:
        # Two concurrent registrations can both pass the check above; the
        # unique index is the only real guarantee.
        db.rollback()
        raise EmailAlreadyRegisteredError(email) from exc

    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Return the user when the credentials are valid, otherwise None.

    A failed login is an expected outcome rather than an error, and the caller
    must not be able to tell which of the three checks failed.
    """
    user = get_user_by_email(db, email)

    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None

    if not verify_password(password, user.hashed_password):
        return None

    if not user.is_active:
        return None

    return user
