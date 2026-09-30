from collections.abc import Generator

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.engine import make_url

import app.models  # noqa: F401  - registers the tables on Base.metadata
from app.core.config import get_settings
from app.db.base import Base


@pytest.fixture
def migrated_engine() -> Generator[Engine, None, None]:
    """A throwaway database built by running the migrations, not create_all."""
    url = make_url(get_settings().database_url)
    scratch_url = url.set(database=f"{url.database}_migrations")

    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{scratch_url.database}" WITH (FORCE)'))
        connection.execute(text(f'CREATE DATABASE "{scratch_url.database}"'))

    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url",
        scratch_url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    command.upgrade(config, "head")

    engine = create_engine(scratch_url)
    yield engine
    engine.dispose()

    with admin_engine.connect() as connection:
        connection.execute(text(f'DROP DATABASE IF EXISTS "{scratch_url.database}" WITH (FORCE)'))
    admin_engine.dispose()


def test_migrations_produce_the_schema_the_models_expect(migrated_engine: Engine) -> None:
    """Catches migrations that drift away from the models."""
    with migrated_engine.connect() as connection:
        context = MigrationContext.configure(connection)
        differences = compare_metadata(context, Base.metadata)

    assert differences == []


def test_migrations_can_be_rolled_back(migrated_engine: Engine) -> None:
    url = make_url(get_settings().database_url)
    scratch_url = url.set(database=f"{url.database}_migrations")

    config = Config("alembic.ini")
    config.set_main_option(
        "sqlalchemy.url",
        scratch_url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    command.downgrade(config, "base")

    assert "users" not in inspect(migrated_engine).get_table_names()
