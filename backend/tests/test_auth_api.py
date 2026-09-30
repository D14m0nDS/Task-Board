from datetime import timedelta

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User

REGISTRATION = {
    "email": "ada@example.com",
    "full_name": "Ada Lovelace",
    "password": "super-secret-1",
}


@pytest.fixture
def registered_user(client: TestClient) -> dict:
    response = client.post("/auth/register", json=REGISTRATION)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def token(client: TestClient, registered_user: dict) -> str:
    response = client.post(
        "/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    return response.json()["access_token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestRegister:
    def test_returns_the_created_user(self, registered_user: dict) -> None:
        assert registered_user["email"] == REGISTRATION["email"]
        assert registered_user["full_name"] == REGISTRATION["full_name"]
        assert registered_user["is_active"] is True

    def test_never_exposes_the_password(self, registered_user: dict) -> None:
        assert "password" not in registered_user
        assert "hashed_password" not in registered_user

    def test_stores_a_hash_rather_than_the_plaintext(
        self, client: TestClient, db: Session, registered_user: dict
    ) -> None:
        user = db.scalar(select(User).where(User.email == REGISTRATION["email"]))

        assert user is not None
        assert user.hashed_password != REGISTRATION["password"]
        assert user.hashed_password.startswith("$2b$")

    def test_rejects_a_duplicate_email(self, client: TestClient, registered_user: dict) -> None:
        response = client.post("/auth/register", json=REGISTRATION)

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_rejects_a_duplicate_email_in_a_different_case(
        self, client: TestClient, registered_user: dict
    ) -> None:
        response = client.post(
            "/auth/register",
            json={**REGISTRATION, "email": REGISTRATION["email"].upper()},
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_rejects_a_short_password(self, client: TestClient) -> None:
        response = client.post("/auth/register", json={**REGISTRATION, "password": "short"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_rejects_a_password_bcrypt_cannot_hash(self, client: TestClient) -> None:
        response = client.post("/auth/register", json={**REGISTRATION, "password": "a" * 73})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_rejects_a_malformed_email(self, client: TestClient) -> None:
        response = client.post("/auth/register", json={**REGISTRATION, "email": "not-an-email"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestLogin:
    def test_returns_a_bearer_token(self, token: str) -> None:
        assert token

    def test_accepts_a_differently_cased_email(
        self, client: TestClient, registered_user: dict
    ) -> None:
        response = client.post(
            "/auth/login",
            json={"email": "ADA@Example.com", "password": REGISTRATION["password"]},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["token_type"] == "bearer"

    def test_rejects_a_wrong_password(self, client: TestClient, registered_user: dict) -> None:
        response = client.post(
            "/auth/login",
            json={"email": REGISTRATION["email"], "password": "not-the-password"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_gives_the_same_answer_for_an_unknown_email(
        self, client: TestClient, registered_user: dict
    ) -> None:
        """An attacker must not be able to tell which emails are registered."""
        wrong_password = client.post(
            "/auth/login",
            json={"email": REGISTRATION["email"], "password": "not-the-password"},
        )
        unknown_email = client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "not-the-password"},
        )

        assert unknown_email.status_code == wrong_password.status_code
        assert unknown_email.json() == wrong_password.json()

    def test_rejects_a_deactivated_user(
        self, client: TestClient, db: Session, registered_user: dict
    ) -> None:
        user = db.scalar(select(User).where(User.email == REGISTRATION["email"]))
        assert user is not None
        user.is_active = False
        db.commit()

        response = client.post(
            "/auth/login",
            json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestCurrentUser:
    def test_returns_the_authenticated_user(self, client: TestClient, token: str) -> None:
        response = client.get("/auth/me", headers=bearer(token))

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["email"] == REGISTRATION["email"]

    def test_requires_a_token(self, client: TestClient) -> None:
        response = client.get("/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rejects_a_malformed_token(self, client: TestClient) -> None:
        response = client.get("/auth/me", headers=bearer("not-a-jwt"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rejects_an_expired_token(
        self, client: TestClient, registered_user: dict
    ) -> None:
        expired = create_access_token(registered_user["id"], expires_delta=timedelta(seconds=-1))

        response = client.get("/auth/me", headers=bearer(expired))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_rejects_a_token_for_a_user_that_no_longer_exists(
        self, client: TestClient, db: Session, token: str, registered_user: dict
    ) -> None:
        user = db.get(User, registered_user["id"])
        assert user is not None
        db.delete(user)
        db.commit()

        response = client.get("/auth/me", headers=bearer(token))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
