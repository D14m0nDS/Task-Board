import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.conftest import Account


@pytest.fixture
def projects_url(shared_workspace: dict) -> str:
    return f"/workspaces/{shared_workspace['id']}/projects"


@pytest.fixture
def project(client: TestClient, projects_url: str, owner: Account) -> dict:
    response = client.post(
        projects_url,
        json={"key": "DEV", "name": "Platform"},
        headers=owner.headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


class TestCreateProject:
    def test_returns_the_created_project(
        self, project: dict, shared_workspace: dict
    ) -> None:
        assert project["key"] == "DEV"
        assert project["name"] == "Platform"
        assert project["description"] is None
        assert project["workspace_id"] == shared_workspace["id"]

    def test_normalises_the_key(
        self, client: TestClient, projects_url: str, owner: Account
    ) -> None:
        response = client.post(
            projects_url, json={"key": "  web  ", "name": "Site"}, headers=owner.headers
        )

        assert response.json()["key"] == "WEB"

    def test_strips_the_name(
        self, client: TestClient, projects_url: str, owner: Account
    ) -> None:
        response = client.post(
            projects_url, json={"key": "WEB", "name": "  Site  "}, headers=owner.headers
        )

        assert response.json()["name"] == "Site"

    def test_stores_a_description(
        self, client: TestClient, projects_url: str, owner: Account
    ) -> None:
        response = client.post(
            projects_url,
            json={"key": "WEB", "name": "Site", "description": "Marketing site"},
            headers=owner.headers,
        )

        assert response.json()["description"] == "Marketing site"

    def test_rejects_a_key_already_used_in_the_workspace(
        self, client: TestClient, projects_url: str, project: dict, owner: Account
    ) -> None:
        response = client.post(
            projects_url, json={"key": "DEV", "name": "Other"}, headers=owner.headers
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_rejects_a_key_that_differs_only_in_case(
        self, client: TestClient, projects_url: str, project: dict, owner: Account
    ) -> None:
        """Normalising before the check stops DEV and dev coexisting."""
        response = client.post(
            projects_url, json={"key": "dev", "name": "Other"}, headers=owner.headers
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_allows_the_same_key_in_another_workspace(
        self,
        client: TestClient,
        project: dict,
        foreign_workspace: dict,
        outsider: Account,
    ) -> None:
        """Keys are unique per workspace, not globally."""
        response = client.post(
            f"/workspaces/{foreign_workspace['id']}/projects",
            json={"key": "DEV", "name": "Their Platform"},
            headers=outsider.headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.parametrize("key", ["D", "TOOMANYLETTERS", "DEV2", "DE-V", ""])
    def test_rejects_a_malformed_key(
        self, client: TestClient, projects_url: str, owner: Account, key: str
    ) -> None:
        """Digits are excluded so DEV2-42 can never be read two ways."""
        response = client.post(
            projects_url, json={"key": key, "name": "Thing"}, headers=owner.headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_forbids_a_member_who_is_not_an_owner(
        self, client: TestClient, projects_url: str, member: Account
    ) -> None:
        response = client.post(
            projects_url, json={"key": "WEB", "name": "Site"}, headers=member.headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_hides_the_workspace_from_a_non_member(
        self, client: TestClient, projects_url: str, outsider: Account
    ) -> None:
        response = client.post(
            projects_url, json={"key": "WEB", "name": "Site"}, headers=outsider.headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestListProjects:
    def test_returns_the_workspace_projects(
        self, client: TestClient, projects_url: str, project: dict, member: Account
    ) -> None:
        response = client.get(projects_url, headers=member.headers)

        assert [entry["id"] for entry in response.json()] == [project["id"]]

    def test_orders_by_key(
        self, client: TestClient, projects_url: str, project: dict, owner: Account
    ) -> None:
        client.post(projects_url, json={"key": "APP", "name": "App"}, headers=owner.headers)

        response = client.get(projects_url, headers=owner.headers)

        assert [entry["key"] for entry in response.json()] == ["APP", "DEV"]

    def test_is_empty_for_a_workspace_without_projects(
        self, client: TestClient, workspace: dict, owner: Account
    ) -> None:
        response = client.get(f"/workspaces/{workspace['id']}/projects", headers=owner.headers)

        assert response.json() == []

    def test_excludes_projects_from_other_workspaces(
        self,
        client: TestClient,
        projects_url: str,
        project: dict,
        foreign_workspace: dict,
        outsider: Account,
    ) -> None:
        client.post(
            f"/workspaces/{foreign_workspace['id']}/projects",
            json={"key": "APP", "name": "App"},
            headers=outsider.headers,
        )

        response = client.get(
            f"/workspaces/{foreign_workspace['id']}/projects", headers=outsider.headers
        )

        assert [entry["key"] for entry in response.json()] == ["APP"]

    def test_hides_the_workspace_from_a_non_member(
        self, client: TestClient, projects_url: str, outsider: Account
    ) -> None:
        response = client.get(projects_url, headers=outsider.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetProject:
    def test_returns_the_project_to_a_member(
        self, client: TestClient, projects_url: str, project: dict, member: Account
    ) -> None:
        response = client.get(f"{projects_url}/{project['id']}", headers=member.headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["key"] == "DEV"

    def test_rejects_an_unknown_project(
        self, client: TestClient, projects_url: str, owner: Account
    ) -> None:
        response = client.get(f"{projects_url}/{uuid.uuid4()}", headers=owner.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_rejects_a_project_belonging_to_another_workspace(
        self,
        client: TestClient,
        projects_url: str,
        foreign_workspace: dict,
        owner: Account,
        outsider: Account,
    ) -> None:
        """A real id from elsewhere must not resolve through this workspace."""
        foreign = client.post(
            f"/workspaces/{foreign_workspace['id']}/projects",
            json={"key": "APP", "name": "App"},
            headers=outsider.headers,
        ).json()

        response = client.get(f"{projects_url}/{foreign['id']}", headers=owner.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_hides_the_project_from_a_non_member(
        self, client: TestClient, projects_url: str, project: dict, outsider: Account
    ) -> None:
        response = client.get(f"{projects_url}/{project['id']}", headers=outsider.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUpdateProject:
    def test_lets_an_owner_rename_the_project(
        self, client: TestClient, projects_url: str, project: dict, owner: Account
    ) -> None:
        response = client.patch(
            f"{projects_url}/{project['id']}",
            json={"name": "Platform Team"},
            headers=owner.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["name"] == "Platform Team"

    def test_leaves_an_omitted_description_alone(
        self, client: TestClient, projects_url: str, project: dict, owner: Account
    ) -> None:
        url = f"{projects_url}/{project['id']}"
        client.patch(url, json={"description": "Notes"}, headers=owner.headers)

        response = client.patch(url, json={"name": "Renamed"}, headers=owner.headers)

        assert response.json()["description"] == "Notes"

    def test_clears_the_description_when_null_is_sent(
        self, client: TestClient, projects_url: str, project: dict, owner: Account
    ) -> None:
        """An omitted field and an explicit null have to mean different things."""
        url = f"{projects_url}/{project['id']}"
        client.patch(url, json={"description": "Notes"}, headers=owner.headers)

        response = client.patch(url, json={"description": None}, headers=owner.headers)

        assert response.json()["description"] is None

    def test_ignores_an_attempt_to_change_the_key(
        self, client: TestClient, projects_url: str, project: dict, owner: Account
    ) -> None:
        """The key prefixes every task identifier, so it is not patchable."""
        response = client.patch(
            f"{projects_url}/{project['id']}", json={"key": "WEB"}, headers=owner.headers
        )

        assert response.json()["key"] == "DEV"

    def test_rejects_a_blank_name(
        self, client: TestClient, projects_url: str, project: dict, owner: Account
    ) -> None:
        response = client.patch(
            f"{projects_url}/{project['id']}", json={"name": ""}, headers=owner.headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_forbids_a_member_who_is_not_an_owner(
        self, client: TestClient, projects_url: str, project: dict, member: Account
    ) -> None:
        response = client.patch(
            f"{projects_url}/{project['id']}", json={"name": "Renamed"}, headers=member.headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_hides_the_project_from_a_non_member(
        self, client: TestClient, projects_url: str, project: dict, outsider: Account
    ) -> None:
        response = client.patch(
            f"{projects_url}/{project['id']}", json={"name": "Renamed"}, headers=outsider.headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_reach_a_project_in_a_workspace_the_caller_owns_elsewhere(
        self,
        client: TestClient,
        projects_url: str,
        foreign_workspace: dict,
        owner: Account,
        outsider: Account,
    ) -> None:
        """Owning one workspace must not grant writes to another one's projects."""
        foreign = client.post(
            f"/workspaces/{foreign_workspace['id']}/projects",
            json={"key": "APP", "name": "App"},
            headers=outsider.headers,
        ).json()

        response = client.patch(
            f"{projects_url}/{foreign['id']}", json={"name": "Hijacked"}, headers=owner.headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert (
            client.get(
                f"/workspaces/{foreign_workspace['id']}/projects/{foreign['id']}",
                headers=outsider.headers,
            ).json()["name"]
            == "App"
        )

    def test_leaves_the_project_unchanged_when_the_caller_is_not_an_owner(
        self, client: TestClient, projects_url: str, project: dict, member: Account, owner: Account
    ) -> None:
        client.patch(
            f"{projects_url}/{project['id']}", json={"name": "Renamed"}, headers=member.headers
        )

        response = client.get(f"{projects_url}/{project['id']}", headers=owner.headers)
        assert response.json()["name"] == "Platform"
