import uuid
from typing import NamedTuple

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workspace import WorkspaceMember, WorkspaceRole

PASSWORD = "workspace-tests-1"


class Account(NamedTuple):
    id: str
    headers: dict[str, str]


def make_account(client: TestClient, email: str) -> Account:
    registration = client.post(
        "/auth/register",
        json={"email": email, "full_name": email.split("@")[0], "password": PASSWORD},
    )
    assert registration.status_code == status.HTTP_201_CREATED

    login = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    token = login.json()["access_token"]

    return Account(id=registration.json()["id"], headers={"Authorization": f"Bearer {token}"})


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
def shared_workspace(db: Session, workspace: dict, member: Account) -> dict:
    """The workspace with a second user added as MEMBER.

    Inserted directly because there is no add-member endpoint yet. Tests share
    one session across requests, so expiring it afterwards keeps relationships
    from serving the state they were loaded with before this insert.
    """
    db.add(
        WorkspaceMember(
            workspace_id=uuid.UUID(workspace["id"]),
            user_id=uuid.UUID(member.id),
            role=WorkspaceRole.MEMBER,
        )
    )
    db.commit()
    db.expire_all()

    return workspace


class TestCreateWorkspace:
    def test_returns_the_created_workspace(self, workspace: dict) -> None:
        assert workspace["name"] == "Platform"
        assert uuid.UUID(workspace["id"])

    def test_strips_surrounding_whitespace_from_the_name(
        self, client: TestClient, owner: Account
    ) -> None:
        response = client.post("/workspaces", json={"name": "  Platform  "}, headers=owner.headers)

        assert response.json()["name"] == "Platform"

    def test_makes_the_creator_the_only_owner(
        self, db: Session, workspace: dict, owner: Account
    ) -> None:
        """A workspace without an owner could never be administered."""
        memberships = db.scalars(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == uuid.UUID(workspace["id"])
            )
        ).all()

        assert len(memberships) == 1
        assert str(memberships[0].user_id) == owner.id
        assert memberships[0].role == WorkspaceRole.OWNER

    def test_rejects_a_blank_name(self, client: TestClient, owner: Account) -> None:
        response = client.post("/workspaces", json={"name": ""}, headers=owner.headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.post("/workspaces", json={"name": "Platform"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListWorkspaces:
    def test_returns_the_callers_workspaces(
        self, client: TestClient, workspace: dict, owner: Account
    ) -> None:
        response = client.get("/workspaces", headers=owner.headers)

        assert [entry["id"] for entry in response.json()] == [workspace["id"]]

    def test_includes_workspaces_the_caller_only_belongs_to(
        self, client: TestClient, shared_workspace: dict, member: Account
    ) -> None:
        response = client.get("/workspaces", headers=member.headers)

        assert [entry["id"] for entry in response.json()] == [shared_workspace["id"]]

    def test_excludes_workspaces_the_caller_has_no_part_in(
        self, client: TestClient, workspace: dict, outsider: Account
    ) -> None:
        response = client.get("/workspaces", headers=outsider.headers)

        assert response.json() == []

    def test_requires_authentication(self, client: TestClient) -> None:
        response = client.get("/workspaces")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetWorkspace:
    def test_returns_the_workspace_to_a_member(
        self, client: TestClient, shared_workspace: dict, member: Account
    ) -> None:
        response = client.get(f"/workspaces/{shared_workspace['id']}", headers=member.headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Platform"

    def test_hides_the_workspace_from_a_non_member(
        self, client: TestClient, workspace: dict, outsider: Account
    ) -> None:
        """404 rather than 403, so the response does not confirm it exists."""
        response = client.get(f"/workspaces/{workspace['id']}", headers=outsider.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_answers_identically_for_a_workspace_that_does_not_exist(
        self, client: TestClient, workspace: dict, outsider: Account
    ) -> None:
        hidden = client.get(f"/workspaces/{workspace['id']}", headers=outsider.headers)
        unknown = client.get(f"/workspaces/{uuid.uuid4()}", headers=outsider.headers)

        assert hidden.status_code == unknown.status_code
        assert hidden.json() == unknown.json()

    def test_requires_authentication(self, client: TestClient, workspace: dict) -> None:
        response = client.get(f"/workspaces/{workspace['id']}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListWorkspaceMembers:
    def test_returns_every_member_with_their_role(
        self, client: TestClient, shared_workspace: dict, owner: Account, member: Account
    ) -> None:
        response = client.get(
            f"/workspaces/{shared_workspace['id']}/members", headers=owner.headers
        )

        roles = {entry["user"]["id"]: entry["role"] for entry in response.json()}
        assert roles == {owner.id: "OWNER", member.id: "MEMBER"}

    def test_never_exposes_password_hashes(
        self, client: TestClient, shared_workspace: dict, owner: Account
    ) -> None:
        response = client.get(
            f"/workspaces/{shared_workspace['id']}/members", headers=owner.headers
        )

        for entry in response.json():
            assert "hashed_password" not in entry["user"]

    def test_hides_the_member_list_from_a_non_member(
        self, client: TestClient, workspace: dict, outsider: Account
    ) -> None:
        response = client.get(f"/workspaces/{workspace['id']}/members", headers=outsider.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateWorkspace:
    def test_lets_an_owner_rename_the_workspace(
        self, client: TestClient, workspace: dict, owner: Account
    ) -> None:
        response = client.patch(
            f"/workspaces/{workspace['id']}", json={"name": "Platform Team"}, headers=owner.headers
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Platform Team"

    def test_persists_the_new_name(
        self, client: TestClient, workspace: dict, owner: Account
    ) -> None:
        client.patch(
            f"/workspaces/{workspace['id']}", json={"name": "Platform Team"}, headers=owner.headers
        )
        response = client.get(f"/workspaces/{workspace['id']}", headers=owner.headers)

        assert response.json()["name"] == "Platform Team"

    def test_forbids_a_member_who_is_not_an_owner(
        self, client: TestClient, shared_workspace: dict, member: Account
    ) -> None:
        """403, not 404: a member already knows the workspace exists."""
        response = client.patch(
            f"/workspaces/{shared_workspace['id']}",
            json={"name": "Renamed"},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_hides_the_workspace_from_a_non_member(
        self, client: TestClient, workspace: dict, outsider: Account
    ) -> None:
        response = client.patch(
            f"/workspaces/{workspace['id']}", json={"name": "Renamed"}, headers=outsider.headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_leaves_the_name_unchanged_when_the_caller_is_not_an_owner(
        self, client: TestClient, shared_workspace: dict, member: Account, owner: Account
    ) -> None:
        client.patch(
            f"/workspaces/{shared_workspace['id']}",
            json={"name": "Renamed"},
            headers=member.headers,
        )
        response = client.get(f"/workspaces/{shared_workspace['id']}", headers=owner.headers)

        assert response.json()["name"] == "Platform"
