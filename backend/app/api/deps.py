from collections.abc import Generator

from sqlalchemy.orm import Session

from app.db.session import SessionLocal


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
