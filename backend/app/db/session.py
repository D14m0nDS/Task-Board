from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings

settings = get_settings()

# pool_pre_ping checks a pooled connection is still alive before handing it
# out, which matters when the database restarts under Docker.
engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    # Attributes stay readable after commit, so a route can serialise the
    # object it just saved without triggering another query.
    expire_on_commit=False,
)
