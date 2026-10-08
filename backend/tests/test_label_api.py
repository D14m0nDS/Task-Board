import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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
def labels_url(shared_workspace: dict, project: dict) -> str:
    return f"/workspaces/{shared_workspace['id']}/projects/{project['id']}/labels"


@pytest.fixture
def tasks_url(shared_workspace: dict, project: dict) -> str:
    return f"/workspaces/{shared_workspace['id']}/projects/{project['id']}/tasks"


@pytest.fixture
def task(client: TestClient, tasks_url: str, member: Account) -> dict:
    response = client.post(tasks_url, json={"title": "Add login"}, headers=member.headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


@pytest.fixture
def label(client: TestClient, labels_url: str, member: Account) -> dict:
    response = client.post(labels_url, json={"name": "Bug"}, headers=member.headers)
    assert response.status_code == status.HTTP_201_CREATED
    return response.json()


class TestCreateLabel:
    def test_returns_the_created_label(self, label: dict, project: dict) -> None:
        assert label["name"] == "Bug"
        assert label["color"] == "#6B7280"
        assert label["project_id"] == project["id"]

    def test_stores_a_supplied_color_in_uppercase(
        self, client: TestClient, labels_url: str, member: Account
    ) -> None:
        response = client.post(
            labels_url,
            json={"name": "Feature", "color": "#aabbcc"},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["color"] == "#AABBCC"

    def test_strips_the_name(self, client: TestClient, labels_url: str, member: Account) -> None:
        response = client.post(labels_url, json={"name": "  Bug  "}, headers=member.headers)

        assert response.json()["name"] == "Bug"

    def test_rejects_a_blank_name(
        self, client: TestClient, labels_url: str, member: Account
    ) -> None:
        response = client.post(labels_url, json={"name": "   "}, headers=member.headers)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_rejects_a_malformed_color(
        self, client: TestClient, labels_url: str, member: Account
    ) -> None:
        response = client.post(
            labels_url,
            json={"name": "Bug", "color": "red"},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_rejects_a_name_already_used_in_the_project(
        self, client: TestClient, labels_url: str, label: dict, member: Account
    ) -> None:
        response = client.post(labels_url, json={"name": "Bug"}, headers=member.headers)

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_rejects_a_name_that_differs_only_in_case(
        self, client: TestClient, labels_url: str, label: dict, member: Account
    ) -> None:
        response = client.post(labels_url, json={"name": "bug"}, headers=member.headers)

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_allows_the_same_name_in_another_project(
        self,
        client: TestClient,
        shared_workspace: dict,
        labels_url: str,
        label: dict,
        owner: Account,
        member: Account,
    ) -> None:
        other = client.post(
            f"/workspaces/{shared_workspace['id']}/projects",
            json={"key": "WEB", "name": "Site"},
            headers=owner.headers,
        ).json()

        response = client.post(
            f"/workspaces/{shared_workspace['id']}/projects/{other['id']}/labels",
            json={"name": "Bug"},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_hides_the_project_from_a_non_member(
        self, client: TestClient, labels_url: str, outsider: Account
    ) -> None:
        response = client.post(labels_url, json={"name": "Bug"}, headers=outsider.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_requires_authentication(self, client: TestClient, labels_url: str) -> None:
        response = client.post(labels_url, json={"name": "Bug"})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestListLabels:
    def test_returns_labels_in_case_insensitive_name_order(
        self, client: TestClient, labels_url: str, member: Account
    ) -> None:
        for name in ("Zebra", "bug", "Alpha"):
            created = client.post(labels_url, json={"name": name}, headers=member.headers)
            assert created.status_code == status.HTTP_201_CREATED

        response = client.get(labels_url, headers=member.headers)

        assert [entry["name"] for entry in response.json()] == ["Alpha", "bug", "Zebra"]

    def test_is_empty_before_any_label_exists(
        self, client: TestClient, labels_url: str, member: Account
    ) -> None:
        response = client.get(labels_url, headers=member.headers)

        assert response.json() == []

    def test_hides_the_project_from_a_non_member(
        self, client: TestClient, labels_url: str, outsider: Account
    ) -> None:
        response = client.get(labels_url, headers=outsider.headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSetTaskLabels:
    def test_a_new_task_has_no_labels(self, task: dict) -> None:
        assert task["labels"] == []

    def test_replaces_the_whole_set(
        self,
        client: TestClient,
        db: Session,
        labels_url: str,
        tasks_url: str,
        task: dict,
        member: Account,
    ) -> None:
        bug = client.post(labels_url, json={"name": "Bug"}, headers=member.headers).json()
        docs = client.post(labels_url, json={"name": "Docs"}, headers=member.headers).json()
        url = f"{tasks_url}/{task['id']}/labels"

        first = client.put(url, json={"label_ids": [bug["id"]]}, headers=member.headers)
        second = client.put(
            url, json={"label_ids": [docs["id"], bug["id"]]}, headers=member.headers
        )

        assert first.status_code == status.HTTP_200_OK
        assert [entry["id"] for entry in first.json()["labels"]] == [bug["id"]]
        assert {entry["id"] for entry in second.json()["labels"]} == {bug["id"], docs["id"]}

        # The test session does not expire on commit, so reload to see name order.
        db.expire_all()
        fetched = client.get(f"{tasks_url}/{task['id']}", headers=member.headers)
        assert [entry["name"] for entry in fetched.json()["labels"]] == ["Bug", "Docs"]

    def test_clears_the_labels_when_an_empty_list_is_sent(
        self, client: TestClient, labels_url: str, tasks_url: str, task: dict, member: Account
    ) -> None:
        bug = client.post(labels_url, json={"name": "Bug"}, headers=member.headers).json()
        url = f"{tasks_url}/{task['id']}/labels"
        client.put(url, json={"label_ids": [bug["id"]]}, headers=member.headers)

        response = client.put(url, json={"label_ids": []}, headers=member.headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["labels"] == []

    def test_rejects_a_label_from_another_project_without_changing_the_task(
        self,
        client: TestClient,
        shared_workspace: dict,
        labels_url: str,
        tasks_url: str,
        task: dict,
        owner: Account,
        member: Account,
    ) -> None:
        kept = client.post(labels_url, json={"name": "Bug"}, headers=member.headers).json()
        url = f"{tasks_url}/{task['id']}/labels"
        client.put(url, json={"label_ids": [kept["id"]]}, headers=member.headers)

        other = client.post(
            f"/workspaces/{shared_workspace['id']}/projects",
            json={"key": "WEB", "name": "Site"},
            headers=owner.headers,
        ).json()
        foreign = client.post(
            f"/workspaces/{shared_workspace['id']}/projects/{other['id']}/labels",
            json={"name": "Docs"},
            headers=member.headers,
        ).json()

        response = client.put(
            url,
            json={"label_ids": [kept["id"], foreign["id"]]},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        unchanged = client.get(f"{tasks_url}/{task['id']}", headers=member.headers)
        assert [entry["id"] for entry in unchanged.json()["labels"]] == [kept["id"]]

    def test_rejects_an_unknown_label_without_changing_the_task(
        self, client: TestClient, labels_url: str, tasks_url: str, task: dict, member: Account
    ) -> None:
        kept = client.post(labels_url, json={"name": "Bug"}, headers=member.headers).json()
        url = f"{tasks_url}/{task['id']}/labels"
        client.put(url, json={"label_ids": [kept["id"]]}, headers=member.headers)

        response = client.put(
            url,
            json={"label_ids": [kept["id"], str(uuid.uuid4())]},
            headers=member.headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        unchanged = client.get(f"{tasks_url}/{task['id']}", headers=member.headers)
        assert [entry["id"] for entry in unchanged.json()["labels"]] == [kept["id"]]

    def test_does_not_record_activity(
        self, client: TestClient, labels_url: str, tasks_url: str, task: dict, member: Account
    ) -> None:
        bug = client.post(labels_url, json={"name": "Bug"}, headers=member.headers).json()
        client.put(
            f"{tasks_url}/{task['id']}/labels",
            json={"label_ids": [bug["id"]]},
            headers=member.headers,
        )

        events = client.get(f"{tasks_url}/{task['id']}/activity", headers=member.headers)

        assert [event["type"] for event in events.json()] == ["TASK_CREATED"]

    def test_hides_the_task_from_a_non_member(
        self, client: TestClient, tasks_url: str, task: dict, outsider: Account
    ) -> None:
        response = client.put(
            f"{tasks_url}/{task['id']}/labels",
            json={"label_ids": []},
            headers=outsider.headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
