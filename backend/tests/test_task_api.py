import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from tests.conftest import Account


@pytest.fixture
def project(client: TestClient, shared_workspace: dict, owner: Account) -> dict:
    response = client.post(
        f"/workspaces/{shared_workspace['id']}/projects",
        json={"key": "DEV", "name": "Platform"},
        headers=owner.headers,
    )
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def tasks_url(shared_workspace: dict, project: dict) -> str:
    return f"/workspaces/{shared_workspace['id']}/projects/{project['id']}/tasks"


@pytest.fixture
def task(client: TestClient, tasks_url: str, member: Account) -> dict:
    response = client.post(tasks_url, json={"title": "Add login"}, headers=member.headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


class TestCreateTask:
    def test_lets_a_member_create_a_task(self, task: dict, member: Account) -> None:
        assert task["key"] == "DEV-1"
        assert task["number"] == 1
        assert task["title"] == "Add login"
        assert task["status"] == "BACKLOG"
        assert task["priority"] == "MEDIUM"
        assert task["type"] == "FEATURE"
        assert task["description"] is None
        assert task["assignee"] is None
        assert task["reporter"]["id"] == member.id

    def test_never_exposes_a_password_hash(self, task: dict) -> None:
        assert "hashed_password" not in task["reporter"]

    def test_numbers_tasks_in_order(
        self, client: TestClient, tasks_url: str, task: dict, owner: Account
    ) -> None:
        response = client.post(tasks_url, json={"title": "Second"}, headers=owner.headers)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["key"] == "DEV-2"
        assert response.json()["number"] == 2

    def test_starts_numbering_again_in_another_project(
        self, client: TestClient, shared_workspace: dict, task: dict, owner: Account
    ) -> None:
        other = client.post(
            f"/workspaces/{shared_workspace['id']}/projects",
            json={"key": "WEB", "name": "Site"},
            headers=owner.headers,
        ).json()

        response = client.post(
            f"/workspaces/{shared_workspace['id']}/projects/{other['id']}/tasks",
            json={"title": "Homepage"},
            headers=owner.headers,
        )

        assert response.json()["key"] == "WEB-1"

    def test_strips_the_title(
        self, client: TestClient, tasks_url: str, member: Account
    ) -> None:
        response = client.post(
            tasks_url, json={"title": "  Add login  "}, headers=member.headers
        )

        assert response.json()["title"] == "Add login"

    def test_assigns_a_workspace_member(
        self, client: TestClient, tasks_url: str, member: Account, owner: Account
    ) -> None:
        response = client.post(
            tasks_url,
            json={"title": "Add login", "assignee_id": owner.id},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["assignee"]["id"] == owner.id

    def test_rejects_an_assignee_from_outside_the_workspace(
        self, client: TestClient, tasks_url: str, member: Account, outsider: Account
    ) -> None:
        response = client.post(
            tasks_url,
            json={"title": "Add login", "assignee_id": outsider.id},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_rejects_an_unknown_assignee(
        self, client: TestClient, tasks_url: str, member: Account
    ) -> None:
        response = client.post(
            tasks_url,
            json={"title": "Add login", "assignee_id": str(uuid.uuid4())},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_rejects_a_blank_title(
        self, client: TestClient, tasks_url: str, member: Account
    ) -> None:
        response = client.post(tasks_url, json={"title": ""}, headers=member.headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_hides_the_project_from_a_non_member(
        self, client: TestClient, tasks_url: str, outsider: Account
    ) -> None:
        response = client.post(tasks_url, json={"title": "Add login"}, headers=outsider.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_requires_authentication(self, client: TestClient, tasks_url: str) -> None:
        response = client.post(tasks_url, json={"title": "Add login"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListTasks:
    def test_returns_tasks_in_number_order(
        self, client: TestClient, tasks_url: str, task: dict, owner: Account
    ) -> None:
        client.post(tasks_url, json={"title": "Second"}, headers=owner.headers)

        response = client.get(tasks_url, headers=owner.headers)

        assert [entry["key"] for entry in response.json()] == ["DEV-1", "DEV-2"]

    def test_is_empty_before_any_task_exists(
        self, client: TestClient, tasks_url: str, member: Account
    ) -> None:
        response = client.get(tasks_url, headers=member.headers)

        assert response.json() == []

    def test_hides_the_project_from_a_non_member(
        self, client: TestClient, tasks_url: str, outsider: Account
    ) -> None:
        response = client.get(tasks_url, headers=outsider.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestGetTask:
    def test_returns_the_task_to_a_member(
        self, client: TestClient, tasks_url: str, task: dict, owner: Account
    ) -> None:
        response = client.get(f"{tasks_url}/{task['id']}", headers=owner.headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["key"] == "DEV-1"

    def test_rejects_an_unknown_task(
        self, client: TestClient, tasks_url: str, member: Account
    ) -> None:
        response = client.get(f"{tasks_url}/{uuid.uuid4()}", headers=member.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_rejects_a_task_belonging_to_another_project(
        self,
        client: TestClient,
        shared_workspace: dict,
        tasks_url: str,
        owner: Account,
        member: Account,
    ) -> None:
        other = client.post(
            f"/workspaces/{shared_workspace['id']}/projects",
            json={"key": "WEB", "name": "Site"},
            headers=owner.headers,
        ).json()
        foreign = client.post(
            f"/workspaces/{shared_workspace['id']}/projects/{other['id']}/tasks",
            json={"title": "Homepage"},
            headers=member.headers,
        ).json()

        response = client.get(f"{tasks_url}/{foreign['id']}", headers=owner.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_hides_the_task_from_a_non_member(
        self, client: TestClient, tasks_url: str, task: dict, outsider: Account
    ) -> None:
        response = client.get(f"{tasks_url}/{task['id']}", headers=outsider.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


def activity(client: TestClient, tasks_url: str, task_id: str, account: Account) -> list[dict]:
    response = client.get(f"{tasks_url}/{task_id}/activity", headers=account.headers)
    assert response.status_code == status.HTTP_200_OK
    return response.json()


class TestUpdateTask:
    def test_lets_a_member_change_the_status(
        self, client: TestClient, tasks_url: str, task: dict, member: Account
    ) -> None:
        response = client.patch(
            f"{tasks_url}/{task['id']}",
            json={"status": "IN_PROGRESS"},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "IN_PROGRESS"
        assert response.json()["title"] == "Add login"

    def test_records_a_status_change(
        self, client: TestClient, tasks_url: str, task: dict, member: Account
    ) -> None:
        client.patch(
            f"{tasks_url}/{task['id']}",
            json={"status": "IN_PROGRESS"},
            headers=member.headers,
        )

        change = activity(client, tasks_url, task["id"], member)[-1]
        assert change["type"] == "STATUS_CHANGED"
        assert change["source"] == "USER"
        assert change["data"] == {"from": "BACKLOG", "to": "IN_PROGRESS"}
        assert change["actor"]["id"] == member.id
        assert "hashed_password" not in change["actor"]

    def test_does_not_record_a_status_that_did_not_change(
        self, client: TestClient, tasks_url: str, task: dict, member: Account
    ) -> None:
        client.patch(
            f"{tasks_url}/{task['id']}", json={"status": "BACKLOG"}, headers=member.headers
        )

        types = [event["type"] for event in activity(client, tasks_url, task["id"], member)]
        assert types == ["TASK_CREATED"]

    def test_records_an_assignment_and_an_unassignment(
        self, client: TestClient, tasks_url: str, task: dict, member: Account, owner: Account
    ) -> None:
        client.patch(
            f"{tasks_url}/{task['id']}",
            json={"assignee_id": owner.id},
            headers=member.headers,
        )
        client.patch(
            f"{tasks_url}/{task['id']}",
            json={"assignee_id": None},
            headers=owner.headers,
        )

        events = activity(client, tasks_url, task["id"], member)
        assert events[-2]["type"] == "USER_ASSIGNED"
        assert events[-2]["data"] == {"from": None, "to": owner.id}
        assert events[-1]["data"] == {"from": owner.id, "to": None}

    def test_leaves_an_omitted_description_alone(
        self, client: TestClient, tasks_url: str, task: dict, member: Account
    ) -> None:
        url = f"{tasks_url}/{task['id']}"
        client.patch(url, json={"description": "Notes"}, headers=member.headers)

        response = client.patch(url, json={"title": "Renamed"}, headers=member.headers)

        assert response.json()["description"] == "Notes"
        assert response.json()["title"] == "Renamed"

    def test_clears_the_description_when_null_is_sent(
        self, client: TestClient, tasks_url: str, task: dict, member: Account
    ) -> None:
        url = f"{tasks_url}/{task['id']}"
        client.patch(url, json={"description": "Notes"}, headers=member.headers)

        response = client.patch(url, json={"description": None}, headers=member.headers)

        assert response.json()["description"] is None

    def test_rejects_an_assignee_from_outside_the_workspace(
        self, client: TestClient, tasks_url: str, task: dict, member: Account, outsider: Account
    ) -> None:
        response = client.patch(
            f"{tasks_url}/{task['id']}",
            json={"assignee_id": outsider.id, "status": "DONE"},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        unchanged = client.get(f"{tasks_url}/{task['id']}", headers=member.headers)
        assert unchanged.json()["status"] == "BACKLOG"

    def test_hides_the_task_from_a_non_member(
        self, client: TestClient, tasks_url: str, task: dict, outsider: Account
    ) -> None:
        response = client.patch(
            f"{tasks_url}/{task['id']}",
            json={"status": "DONE"},
            headers=outsider.headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_hides_the_activity_from_a_non_member(
        self, client: TestClient, tasks_url: str, task: dict, outsider: Account
    ) -> None:
        response = client.get(f"{tasks_url}/{task['id']}/activity", headers=outsider.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTaskActivity:
    def test_records_creation(
        self, client: TestClient, tasks_url: str, task: dict, member: Account
    ) -> None:
        events = activity(client, tasks_url, task["id"], member)

        assert len(events) == 1
        assert events[0]["type"] == "TASK_CREATED"
        assert events[0]["data"] == {"status": "BACKLOG"}
        assert events[0]["actor"]["id"] == member.id

    def test_records_an_assignee_chosen_at_creation(
        self, client: TestClient, tasks_url: str, member: Account, owner: Account
    ) -> None:
        created = client.post(
            tasks_url,
            json={"title": "Assigned", "assignee_id": owner.id},
            headers=member.headers,
        ).json()

        events = activity(client, tasks_url, created["id"], member)
        assert [event["type"] for event in events] == ["TASK_CREATED", "USER_ASSIGNED"]
        assert events[1]["data"] == {"from": None, "to": owner.id}
