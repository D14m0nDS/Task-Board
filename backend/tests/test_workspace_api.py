import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workspace import WorkspaceMember, WorkspaceRole
from tests.conftest import Account


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


def role_of(db: Session, workspace_id: str, user_id: str) -> WorkspaceRole | None:
    membership = db.get(
        WorkspaceMember,
        {"workspace_id": uuid.UUID(workspace_id), "user_id": uuid.UUID(user_id)},
    )
    return None if membership is None else membership.role


class TestAddWorkspaceMember:
    def test_adds_the_user_as_a_member(
        self, client: TestClient, workspace: dict, owner: Account, member: Account
    ) -> None:
        response = client.post(
            f"/workspaces/{workspace['id']}/members",
            json={"email": "member@example.com"},
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["role"] == "MEMBER"
        assert response.json()["user"]["id"] == member.id

    def test_can_add_the_user_straight_as_an_owner(
        self, client: TestClient, workspace: dict, owner: Account, member: Account
    ) -> None:
        response = client.post(
            f"/workspaces/{workspace['id']}/members",
            json={"email": "member@example.com", "role": "OWNER"},
            headers=owner.headers,
        )

        assert response.json()["role"] == "OWNER"

    def test_grants_the_new_member_access(
        self, client: TestClient, shared_workspace: dict, member: Account
    ) -> None:
        response = client.get(f"/workspaces/{shared_workspace['id']}", headers=member.headers)

        assert response.status_code == status.HTTP_200_OK

    def test_matches_the_email_regardless_of_case(
        self, client: TestClient, shared_workspace: dict, owner: Account
    ) -> None:
        """Lookup goes through the same normalisation as registration."""
        response = client.post(
            f"/workspaces/{shared_workspace['id']}/members",
            json={"email": "MEMBER@Example.com"},
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_rejects_an_email_with_no_account(
        self, client: TestClient, workspace: dict, owner: Account
    ) -> None:
        response = client.post(
            f"/workspaces/{workspace['id']}/members",
            json={"email": "nobody@example.com"},
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_rejects_someone_who_is_already_a_member(
        self, client: TestClient, shared_workspace: dict, owner: Account
    ) -> None:
        response = client.post(
            f"/workspaces/{shared_workspace['id']}/members",
            json={"email": "member@example.com"},
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_forbids_a_member_who_is_not_an_owner(
        self, client: TestClient, shared_workspace: dict, member: Account, outsider: Account
    ) -> None:
        response = client.post(
            f"/workspaces/{shared_workspace['id']}/members",
            json={"email": "outsider@example.com"},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_hides_the_workspace_from_a_non_member(
        self, client: TestClient, workspace: dict, member: Account, outsider: Account
    ) -> None:
        response = client.post(
            f"/workspaces/{workspace['id']}/members",
            json={"email": "member@example.com"},
            headers=outsider.headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestChangeMemberRole:
    def test_promotes_a_member_to_owner(
        self, client: TestClient, db: Session, shared_workspace: dict, owner: Account, member: Account
    ) -> None:
        response = client.patch(
            f"/workspaces/{shared_workspace['id']}/members/{member.id}",
            json={"role": "OWNER"},
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["role"] == "OWNER"
        assert role_of(db, shared_workspace["id"], member.id) == WorkspaceRole.OWNER

    def test_refuses_to_demote_the_only_owner(
        self, client: TestClient, shared_workspace: dict, owner: Account
    ) -> None:
        response = client.patch(
            f"/workspaces/{shared_workspace['id']}/members/{owner.id}",
            json={"role": "MEMBER"},
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_leaves_the_only_owner_in_place_after_refusing(
        self, client: TestClient, db: Session, shared_workspace: dict, owner: Account
    ) -> None:
        """A 409 that had already written the change would be worse than useless."""
        client.patch(
            f"/workspaces/{shared_workspace['id']}/members/{owner.id}",
            json={"role": "MEMBER"},
            headers=owner.headers,
        )

        assert role_of(db, shared_workspace["id"], owner.id) == WorkspaceRole.OWNER

    def test_allows_an_owner_to_step_down_once_another_exists(
        self, client: TestClient, shared_workspace: dict, owner: Account, member: Account
    ) -> None:
        client.patch(
            f"/workspaces/{shared_workspace['id']}/members/{member.id}",
            json={"role": "OWNER"},
            headers=owner.headers,
        )
        response = client.patch(
            f"/workspaces/{shared_workspace['id']}/members/{owner.id}",
            json={"role": "MEMBER"},
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_200_OK

    def test_rejects_a_user_who_is_not_a_member(
        self, client: TestClient, workspace: dict, owner: Account, outsider: Account
    ) -> None:
        response = client.patch(
            f"/workspaces/{workspace['id']}/members/{outsider.id}",
            json={"role": "MEMBER"},
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_rejects_a_member_of_a_different_workspace(
        self, client: TestClient, workspace: dict, owner: Account, outsider: Account
    ) -> None:
        """Membership is scoped to the workspace in the path, not global."""
        client.post("/workspaces", json={"name": "Elsewhere"}, headers=outsider.headers)

        response = client.patch(
            f"/workspaces/{workspace['id']}/members/{outsider.id}",
            json={"role": "OWNER"},
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_forbids_a_member_who_is_not_an_owner(
        self, client: TestClient, shared_workspace: dict, member: Account, owner: Account
    ) -> None:
        response = client.patch(
            f"/workspaces/{shared_workspace['id']}/members/{owner.id}",
            json={"role": "MEMBER"},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_rejects_a_role_that_does_not_exist(
        self, client: TestClient, shared_workspace: dict, owner: Account, member: Account
    ) -> None:
        response = client.patch(
            f"/workspaces/{shared_workspace['id']}/members/{member.id}",
            json={"role": "ADMIN"},
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


class TestRemoveWorkspaceMember:
    def test_removes_the_member(
        self, client: TestClient, db: Session, shared_workspace: dict, owner: Account, member: Account
    ) -> None:
        response = client.delete(
            f"/workspaces/{shared_workspace['id']}/members/{member.id}",
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert role_of(db, shared_workspace["id"], member.id) is None

    def test_revokes_the_removed_users_access(
        self, client: TestClient, shared_workspace: dict, owner: Account, member: Account
    ) -> None:
        client.delete(
            f"/workspaces/{shared_workspace['id']}/members/{member.id}",
            headers=owner.headers,
        )
        response = client.get(f"/workspaces/{shared_workspace['id']}", headers=member.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_refuses_to_remove_the_only_owner(
        self, client: TestClient, db: Session, shared_workspace: dict, owner: Account
    ) -> None:
        response = client.delete(
            f"/workspaces/{shared_workspace['id']}/members/{owner.id}",
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert role_of(db, shared_workspace["id"], owner.id) == WorkspaceRole.OWNER

    def test_allows_removing_an_owner_once_another_exists(
        self, client: TestClient, shared_workspace: dict, owner: Account, member: Account
    ) -> None:
        client.patch(
            f"/workspaces/{shared_workspace['id']}/members/{member.id}",
            json={"role": "OWNER"},
            headers=owner.headers,
        )
        response = client.delete(
            f"/workspaces/{shared_workspace['id']}/members/{owner.id}",
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_rejects_a_user_who_is_not_a_member(
        self, client: TestClient, workspace: dict, owner: Account, outsider: Account
    ) -> None:
        response = client.delete(
            f"/workspaces/{workspace['id']}/members/{outsider.id}",
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_forbids_a_member_who_is_not_an_owner(
        self, client: TestClient, shared_workspace: dict, member: Account, owner: Account
    ) -> None:
        response = client.delete(
            f"/workspaces/{shared_workspace['id']}/members/{owner.id}",
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
