from collections.abc import Generator
from typing import NamedTuple

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import app.models  # noqa: F401  - registers the tables on Base.metadata
from app.api.deps import get_db
from app.core.config import get_settings
from app.db.base import Base
from app.main import app as fastapi_app


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """A dedicated test database, created once per test session.

    Derived from DATABASE_URL so it follows the same host and credentials as
    the real database, but never touches the development data.
    """
    url = make_url(get_settings().database_url)
    test_url = url.set(database=f"{url.database}_test")

    # CREATE DATABASE cannot run inside a transaction, hence AUTOCOMMIT.
    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as connection:
        already_exists = connection.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": test_url.database},
        )
        if not already_exists:
            connection.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    admin_engine.dispose()

    test_engine = create_engine(test_url)
    Base.metadata.create_all(test_engine)

    yield test_engine

    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Generator[Session, None, None]:
    """A session whose work is discarded when the test ends.

    The session joins an outer transaction as a savepoint, so a commit() inside
    application code is real from the code's point of view but disappears on
    rollback. Tests therefore stay isolated without recreating tables.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    """API client wired to the test session instead of the real database."""
    fastapi_app.dependency_overrides[get_db] = lambda: db

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.clear()


PASSWORD = "fixture-password-1"


class Account(NamedTuple):
    id: str
    email: str
    headers: dict[str, str]


def make_account(client: TestClient, email: str) -> Account:
    registration = client.post(
        "/auth/register",
        json={"email": email, "full_name": email.split("@")[0], "password": PASSWORD},
    )
    assert registration.status_code == status.HTTP_201_CREATED

    login = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    token = login.json()["access_token"]

    return Account(
        id=registration.json()["id"],
        email=email,
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.fixture
def owner(client: TestClient) -> Account:
    return make_account(client, "owner@example.com")


@pytest.fixture
def member(client: TestClient) -> Account:
    return make_account(client, "member@example.com")


@pytest.fixture
def outsider(client: TestClient) -> Account:
    return make_account(client, "outsider@example.com")


@pytest.fixture
def workspace(client: TestClient, owner: Account) -> dict:
    response = client.post("/workspaces", json={"name": "Platform"}, headers=owner.headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def shared_workspace(
    client: TestClient, db: Session, workspace: dict, owner: Account, member: Account
) -> dict:
    """The workspace with a second user added as MEMBER.

    Tests share one session across requests, unlike production, so expiring it
    stops already-loaded relationships from serving a pre-insert view.
    """
    response = client.post(
        f"/workspaces/{workspace['id']}/members",
        json={"email": member.email},
        headers=owner.headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    db.expire_all()

    return workspace


@pytest.fixture
def foreign_workspace(client: TestClient, outsider: Account) -> dict:
    """A workspace the main fixtures have nothing to do with."""
    response = client.post("/workspaces", json={"name": "Elsewhere"}, headers=outsider.headers)
    return response.json()
