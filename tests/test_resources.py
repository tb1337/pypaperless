"""Tests for resource services: Config, Version, Profile, Statistics, Status, Tasks, Trash."""

import json
import re

import pytest
from pytest_httpx import HTTPXMock

from pypaperless import PaperlessClient
from pypaperless.builders import SearchQuery
from pypaperless.const import EndpointPath
from pypaperless.exceptions import BulkEditError, NotFoundError, TaskNotFoundError
from pypaperless.models import (
    Config,
    Document,
    Profile,
    SearchResult,
    ShareLinkBundle,
    Status,
    Task,
)
from pypaperless.models.mixins.securable import Permissions
from pypaperless.models.tasks import TaskStatusCounts, TaskSummary
from pypaperless.models.types import (
    StatisticDocumentFileTypeCount,
    StatusDatabase,
    StatusStorage,
    StatusTasks,
)
from pypaperless.services.workflows import WorkflowActionService, WorkflowTriggerService

from .const import PAPERLESS_TEST_URL
from .data import (
    DATA_BULK_EDIT_OBJECTS,
    DATA_CONFIG,
    DATA_DOCUMENTS_BULK_EDIT,
    DATA_PROFILE,
    DATA_REMOTE_VERSION,
    DATA_SEARCH,
    DATA_SHARE_LINK_BUNDLES,
    DATA_STATISTICS,
    DATA_STATUS,
    DATA_TASKS,
    DATA_TASKS_ACTIVE,
    DATA_TASKS_STATUS_COUNTS,
    DATA_TASKS_SUMMARY,
    DATA_TRASH,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


async def test_config_call(httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
    """config() fetches the singleton Config without requiring a pk."""
    httpx_mock.add_response(
        method="GET",
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.CONFIG_SINGLE}".format(pk=1),
        status_code=200,
        json=DATA_CONFIG[0],
    )
    item = await paperless.config()
    assert item
    assert isinstance(item, Config)


# ---------------------------------------------------------------------------
# Remote version
# ---------------------------------------------------------------------------


async def test_remote_version_call(httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
    """remote_version() returns version string and update_available flag."""
    httpx_mock.add_response(
        method="GET",
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.REMOTE_VERSION}",
        status_code=200,
        json=DATA_REMOTE_VERSION,
    )
    remote_version = await paperless.remote_version()
    assert remote_version
    assert isinstance(remote_version.version, str)
    assert isinstance(remote_version.update_available, bool)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


async def test_profile_call(httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
    """profile() returns a Profile with expected field types."""
    httpx_mock.add_response(
        method="GET",
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.PROFILE}",
        status_code=200,
        json=DATA_PROFILE,
    )
    profile = await paperless.profile()
    assert profile
    assert isinstance(profile, Profile)
    assert isinstance(profile.email, str)
    assert isinstance(profile.auth_token, str)
    assert isinstance(profile.has_usable_password, bool)
    assert isinstance(profile.is_mfa_enabled, bool)
    assert isinstance(profile.social_accounts, list)


async def test_profile_update(httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
    """profile.update() PATCHes the profile and returns the updated model."""
    updated = {**DATA_PROFILE, "first_name": "Patched", "last_name": "User"}
    httpx_mock.add_response(
        method="PATCH",
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.PROFILE}",
        status_code=200,
        json=updated,
    )
    profile = await paperless.profile.update(first_name="Patched", last_name="User")
    assert isinstance(profile, Profile)
    assert profile.first_name == "Patched"
    assert profile.last_name == "User"

    body = json.loads(httpx_mock.get_requests()[-1].content)
    assert body == {"first_name": "Patched", "last_name": "User"}


async def test_profile_update_email(httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
    """profile.update(email=) PATCHes only the email field."""
    updated = {**DATA_PROFILE, "email": "new@example.com"}
    httpx_mock.add_response(
        method="PATCH",
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.PROFILE}",
        status_code=200,
        json=updated,
    )
    profile = await paperless.profile.update(email="new@example.com")
    assert isinstance(profile, Profile)
    assert profile.email == "new@example.com"

    body = json.loads(httpx_mock.get_requests()[-1].content)
    assert body == {"email": "new@example.com"}


async def test_profile_update_password(httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
    """profile.update(password=) PATCHes only the password field."""
    httpx_mock.add_response(
        method="PATCH",
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.PROFILE}",
        status_code=200,
        json=DATA_PROFILE,
    )
    profile = await paperless.profile.update(password="s3cr3t")  # noqa: S106
    assert isinstance(profile, Profile)

    body = json.loads(httpx_mock.get_requests()[-1].content)
    assert body == {"password": "s3cr3t"}


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


async def test_statistics_call(httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
    """statistics() returns typed statistics with document file type counts."""
    httpx_mock.add_response(
        method="GET",
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.STATISTICS}",
        status_code=200,
        json=DATA_STATISTICS,
    )
    stats = await paperless.statistics()
    assert stats
    assert isinstance(stats.character_count, int)
    assert isinstance(stats.document_file_type_counts, list)
    for item in stats.document_file_type_counts:
        assert isinstance(item, StatisticDocumentFileTypeCount)


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------


async def test_status_call(httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
    """status() returns a Status with typed sub-objects."""
    httpx_mock.add_response(
        method="GET",
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.STATUS}",
        status_code=200,
        json=DATA_STATUS,
    )
    status = await paperless.status()
    assert status
    assert isinstance(status, Status)
    assert isinstance(status.storage, StatusStorage)
    assert isinstance(status.database, StatusDatabase)
    assert isinstance(status.tasks, StatusTasks)


async def test_status_has_errors(paperless: PaperlessClient) -> None:
    """Status.has_errors is True when any component is in ERROR state."""
    data = {
        "database": {"status": "OK"},
        "tasks": {
            "redis_status": "OK",
            "celery_status": "OK",
            "classifier_status": "OK",
        },
    }
    status = Status.from_data(paperless.runtime, data=data)
    assert status.has_errors is False

    data["database"]["status"] = "ERROR"
    status = Status.from_data(paperless.runtime, data=data)
    assert status.has_errors is True

    # None values are treated as no errors
    del data["database"]["status"]
    status = Status.from_data(paperless.runtime, data=data)
    assert status.has_errors is False


def test_status_has_errors_no_tasks(paperless: PaperlessClient) -> None:
    """has_errors must work when tasks is None (skips the tasks extend, L91->100)."""
    status = Status.from_data(paperless.runtime, data={"database": {"status": "OK"}})
    assert status.tasks is None
    assert status.has_errors is False

    status_err = Status.from_data(paperless.runtime, data={"database": {"status": "ERROR"}})
    assert status_err.has_errors is True


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


class TestTasks:
    """Task service: iteration, filter, single fetch by pk and uuid."""

    async def test_iter(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """Iterating over tasks yields Task instances from paginated response."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.TASKS}" + r".*$"),
            status_code=200,
            json=DATA_TASKS,
        )
        async for item in paperless.tasks:
            assert isinstance(item, Task)

    async def test_filter(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """tasks.filter() is a context manager passing kwargs as query params."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.TASKS}" + r"\?.*status.*$"),
            status_code=200,
            json=DATA_TASKS,
        )
        async with paperless.tasks.filter(status=["pending"]) as filtered:
            async for item in filtered:
                assert isinstance(item, Task)

    async def test_call_by_pk(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """tasks(pk) fetches by primary key."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.TASKS_SINGLE}".format(pk=1),
            status_code=200,
            json=DATA_TASKS["results"][0],
        )
        item = await paperless.tasks(1)
        assert item
        assert isinstance(item, Task)

    async def test_call_by_uuid(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """tasks(uuid) fetches by task UUID via paginated list filter."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.TASKS}" + r"\?task_id.*$"),
            status_code=200,
            json=DATA_TASKS,
        )
        item = await paperless.tasks("dummy-found")
        assert item
        assert isinstance(item, Task)

    async def test_call_pk_not_found(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """tasks(unknown_pk) raises NotFoundError."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.TASKS_SINGLE}".format(pk=1337),
            status_code=404,
        )
        with pytest.raises(NotFoundError):
            await paperless.tasks(1337)

    async def test_call_uuid_not_found(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """tasks(unknown_uuid) raises TaskNotFoundError on empty paginated result."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.TASKS}" + r"\?task_id.*$"),
            status_code=200,
            json={"count": 0, "next": None, "previous": None, "results": []},
        )
        with pytest.raises(TaskNotFoundError):
            await paperless.tasks("dummy-not-found")

    async def test_active(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """tasks.active() returns an async iterator of Task instances."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.TASKS_ACTIVE}",
            status_code=200,
            json=DATA_TASKS_ACTIVE,
        )
        items = []
        async for item in paperless.tasks.active():
            assert isinstance(item, Task)
            items.append(item)
        assert len(items) == len(DATA_TASKS_ACTIVE)

    async def test_acknowledge(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """tasks.acknowledge([...]) POSTs and returns acknowledged count."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.TASKS_ACKNOWLEDGE}",
            status_code=200,
            json={"result": 1},
        )
        result = await paperless.tasks.acknowledge([1])
        assert result == 1
        assert json.loads(httpx_mock.get_requests()[-1].content) == {"tasks": [1]}

    async def test_summary(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """tasks.summary() returns a list of TaskSummary instances."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.TASKS_SUMMARY}",
            status_code=200,
            json=DATA_TASKS_SUMMARY,
        )
        result = await paperless.tasks.summary()
        assert isinstance(result, list)
        assert len(result) == len(DATA_TASKS_SUMMARY)
        assert all(isinstance(s, TaskSummary) for s in result)

    async def test_status_counts(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """tasks.status_counts() returns a single TaskStatusCounts instance."""
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.TASKS_STATUS_COUNTS}",
            status_code=200,
            json=DATA_TASKS_STATUS_COUNTS,
        )
        result = await paperless.tasks.status_counts()
        assert isinstance(result, TaskStatusCounts)
        assert result.all == DATA_TASKS_STATUS_COUNTS["all"]
        assert result.needs_attention == DATA_TASKS_STATUS_COUNTS["needs_attention"]

    async def test_run(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """tasks.run(task_type) POSTs and returns the Celery UUID string."""
        task_uuid = "11112222-aaaa-bbbb-cccc-333344445555"
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.TASKS_RUN}",
            status_code=200,
            json={"task_id": task_uuid},
        )
        result = await paperless.tasks.run("sanity_check")
        assert isinstance(result, str)
        assert result == task_uuid
        assert json.loads(httpx_mock.get_requests()[-1].content) == {"task_type": "sanity_check"}


# ---------------------------------------------------------------------------
# Mail Accounts
# ---------------------------------------------------------------------------


class TestMailAccounts:
    """Mail account service action endpoints."""

    async def test_test(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """mail_accounts.test() POSTs to the endpoint and returns JSON."""
        payload = {"success": True}
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.MAIL_ACCOUNTS_TEST}",
            status_code=200,
            json=payload,
        )
        response = await paperless.mail_accounts.test()
        assert response == payload

    async def test_process(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """mail_accounts.process(pk) POSTs to the account process endpoint."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.MAIL_ACCOUNTS_PROCESS}".format(pk=1),
            status_code=200,
            json={"result": "ok"},
        )
        await paperless.mail_accounts.process(1)

        request = httpx_mock.get_requests()[-1]
        assert request.url.path.endswith("/1/process/")
        assert json.loads(request.content) == {}


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


async def test_workflow_sub_services(paperless: PaperlessClient) -> None:
    """workflows.actions and workflows.triggers are the expected service types."""
    assert isinstance(paperless.workflows.actions, WorkflowActionService)
    assert isinstance(paperless.workflows.triggers, WorkflowTriggerService)


# ---------------------------------------------------------------------------
# Trash
# ---------------------------------------------------------------------------


class TestTrash:
    """Trash service: iteration, restore, and empty operations."""

    async def test_iter(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """Iterating over trash yields Document instances with deleted_at set."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.TRASH}" + r"\?.*$"),
            status_code=200,
            json=DATA_TRASH,
        )
        items = [item async for item in paperless.trash]
        assert len(items) == len(DATA_TRASH["results"])
        for item in items:
            assert isinstance(item, Document)
            assert item.deleted_at is not None

    async def test_restore(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """restore() POSTs the restore action — never the destructive empty action."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.TRASH}",
            status_code=200,
            json={"result": "restored"},
        )
        await paperless.trash.restore([100, 101])

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {"action": "restore", "documents": [100, 101]}

    async def test_empty(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """empty() empties all or specific documents from the trash."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.TRASH}",
            status_code=200,
            json={"result": "emptied"},
        )
        await paperless.trash.empty()

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {"action": "empty"}

        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.TRASH}",
            status_code=200,
            json={"result": "emptied"},
        )
        await paperless.trash.empty([100])

        body = json.loads(httpx_mock.get_requests()[-1].content)
        assert body == {"action": "empty", "documents": [100]}


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


class TestSearch:
    """Global search service: query and db_only flag."""

    async def test_call(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """search('query') returns a SearchResult with documents."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.SEARCH}" + r".*$"),
            status_code=200,
            json=DATA_SEARCH,
        )
        result = await paperless.search("invoice")
        assert isinstance(result, SearchResult)
        assert result.total == DATA_SEARCH["total"]
        assert result.documents is not None
        assert len(result.documents) == len(DATA_SEARCH["documents"])

        params = httpx_mock.get_requests()[-1].url.params
        assert params["query"] == "invoice"
        assert "db_only" not in params

    async def test_call_with_db_only(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """search('query', db_only=True) passes db_only param and returns SearchResult."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.SEARCH}" + r".*db_only.*$"),
            status_code=200,
            json=DATA_SEARCH,
        )
        result = await paperless.search("invoice", db_only=True)
        assert isinstance(result, SearchResult)
        assert result.total == DATA_SEARCH["total"]

        params = httpx_mock.get_requests()[-1].url.params
        assert params["query"] == "invoice"
        assert params["db_only"] == "true"

    async def test_call_with_builder(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """search(SearchQuery(...)) converts the builder to a string automatically."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath.SEARCH}" + r".*$"),
            status_code=200,
            json=DATA_SEARCH,
        )
        q = SearchQuery("invoice") & SearchQuery.field("tag", "unpaid")
        result = await paperless.search(q)
        assert isinstance(result, SearchResult)
        assert result.total == DATA_SEARCH["total"]

        assert httpx_mock.get_requests()[-1].url.params["query"] == str(q)


# ---------------------------------------------------------------------------
# BulkEditObjects
# ---------------------------------------------------------------------------


class TestBulkEditObjects:
    """BulkEditObjects service: set_permissions and delete operations."""

    async def test_set_permissions(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """set_permissions() POSTs the correct payload and returns None."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.BULK_EDIT_OBJECTS}",
            status_code=200,
            json=DATA_BULK_EDIT_OBJECTS,
        )
        perms = Permissions(view_users=[2], change_users=[1])
        result = await paperless.bulk_edit_objects.set_permissions(
            "tags",
            [1, 2, 3],
            owner=1,
            permissions=perms,
        )
        assert result is None

        request = httpx_mock.get_requests()[-1]
        body = __import__("json").loads(request.content)
        assert body["object_type"] == "tags"
        assert body["operation"] == "set_permissions"
        assert body["objects"] == [1, 2, 3]
        assert body["owner"] == 1
        assert "permissions" in body

    async def test_set_permissions_no_optional_fields(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """set_permissions() without owner/permissions omits those keys."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.BULK_EDIT_OBJECTS}",
            status_code=200,
            json=DATA_BULK_EDIT_OBJECTS,
        )
        await paperless.bulk_edit_objects.set_permissions("correspondents", [7])

        request = httpx_mock.get_requests()[-1]
        body = __import__("json").loads(request.content)
        assert "owner" not in body
        assert "permissions" not in body
        assert body["merge"] is False

    async def test_delete(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """delete() POSTs the correct payload and returns None."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.BULK_EDIT_OBJECTS}",
            status_code=200,
            json=DATA_BULK_EDIT_OBJECTS,
        )
        result = await paperless.bulk_edit_objects.delete("document_types", [10, 11])
        assert result is None

        request = httpx_mock.get_requests()[-1]
        body = __import__("json").loads(request.content)
        assert body["object_type"] == "document_types"
        assert body["operation"] == "delete"
        assert body["objects"] == [10, 11]


# ---------------------------------------------------------------------------
# DocumentsBulkEdit
# ---------------------------------------------------------------------------


class TestDocumentsBulkEdit:
    """DocumentBulkEditService: all 14 bulk operations."""

    async def test_set_correspondent(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """set_correspondent() POSTs the correct payload."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_BULK_EDIT}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.set_correspondent([1, 2], 5)
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["method"] == "set_correspondent"
        assert body["documents"] == [1, 2]
        assert body["parameters"]["correspondent"] == 5

    async def test_set_document_type(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """set_document_type() POSTs the correct payload."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_BULK_EDIT}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.set_document_type([3], 7)
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["method"] == "set_document_type"
        assert body["parameters"]["document_type"] == 7

    async def test_set_storage_path(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """set_storage_path() POSTs the correct payload."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_BULK_EDIT}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.set_storage_path([4, 5], 2)
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["method"] == "set_storage_path"
        assert body["parameters"]["storage_path"] == 2

    async def test_add_tag(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """add_tag() POSTs the correct payload."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_BULK_EDIT}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.add_tag([1], 10)
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["method"] == "add_tag"
        assert body["parameters"]["tag"] == 10

    async def test_remove_tag(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """remove_tag() POSTs the correct payload."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_BULK_EDIT}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.remove_tag([1], 10)
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["method"] == "remove_tag"
        assert body["parameters"]["tag"] == 10

    async def test_modify_tags(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """modify_tags() POSTs both add/remove lists."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_BULK_EDIT}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.modify_tags([1], add_tags=[3, 4], remove_tags=[5])
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["method"] == "modify_tags"
        assert body["parameters"]["add_tags"] == [3, 4]
        assert body["parameters"]["remove_tags"] == [5]

    async def test_modify_custom_fields(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """modify_custom_fields() POSTs dict-style custom field input."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_BULK_EDIT}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.modify_custom_fields(
            [1], add_custom_fields={1: "value"}, remove_custom_fields=[2]
        )
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["method"] == "modify_custom_fields"
        assert body["parameters"]["add_custom_fields"] == {"1": "value"}
        assert body["parameters"]["remove_custom_fields"] == [2]

    async def test_set_permissions(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """set_permissions() includes owner and set_permissions key in parameters."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_BULK_EDIT}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        perms = Permissions(view_users=[2], change_users=[1])
        await paperless.documents.bulk_edit.set_permissions(
            [1, 2], owner=5, permissions=perms, merge=True
        )
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["method"] == "set_permissions"
        assert body["parameters"]["owner"] == 5
        assert body["parameters"]["merge"] is True
        assert "set_permissions" in body["parameters"]

    async def test_delete(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """delete() POSTs to the dedicated delete endpoint."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_DELETE}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.delete([1, 2])
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["documents"] == [1, 2]

    async def test_reprocess(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """reprocess() POSTs to the dedicated reprocess endpoint."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_REPROCESS}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.reprocess([1])
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["documents"] == [1]

    async def test_rotate(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """rotate() POSTs degrees and source_mode."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_ROTATE}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.rotate([1, 2], 90)
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["degrees"] == 90
        assert body["source_mode"] == "latest_version"

    async def test_merge(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """merge() POSTs optional metadata_document_id when provided."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_MERGE}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.merge(
            [1, 2], metadata_document_id=1, delete_originals=True
        )
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["documents"] == [1, 2]
        assert body["metadata_document_id"] == 1
        assert body["delete_originals"] is True

    async def test_edit_pdf(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """edit_pdf() wraps the single document in a list."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_EDIT_PDF}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        ops = [{"page": 1, "rotate": 90}]
        await paperless.documents.bulk_edit.edit_pdf(42, ops)
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["documents"] == [42]
        assert body["operations"] == ops
        assert body["include_metadata"] is True

    async def test_remove_password(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """remove_password() POSTs password and source flags."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_REMOVE_PASSWORD}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.remove_password([5], "s3cr3t")
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["documents"] == [5]
        assert body["password"] == "s3cr3t"
        assert body["source_mode"] == "latest_version"

    async def test_set_permissions_no_owner_no_permissions(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """set_permissions() omits owner/set_permissions when not given (L235->237, L237->239)."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_BULK_EDIT}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.set_permissions([1, 2], merge=False)
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["method"] == "set_permissions"
        assert "owner" not in body["parameters"]
        assert "set_permissions" not in body["parameters"]

    async def test_merge_no_metadata_document_id(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """merge() must omit metadata_document_id when not provided (L336->338)."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_MERGE}",
            status_code=200,
            json=DATA_DOCUMENTS_BULK_EDIT,
        )
        await paperless.documents.bulk_edit.merge([1, 2])
        body = __import__("json").loads(httpx_mock.get_requests()[-1].content)
        assert body["documents"] == [1, 2]
        assert "metadata_document_id" not in body

    async def test_error_result_raises(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """A non-OK result field (e.g. 'ERROR') raises BulkEditError on HTTP 200."""
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS_BULK_EDIT}",
            status_code=200,
            json={"result": "ERROR"},
        )
        with pytest.raises(BulkEditError):
            await paperless.documents.bulk_edit.modify_tags([1], add_tags=[3], remove_tags=[])


# ---------------------------------------------------------------------------
# ShareLinkBundles
# ---------------------------------------------------------------------------


class TestShareLinkBundleRebuild:
    """ShareLinkBundleService.rebuild() triggers a rebuild and returns a bundle."""

    async def test_rebuild(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """rebuild() POSTs to the rebuild endpoint and returns a ShareLinkBundle."""
        bundle_data = DATA_SHARE_LINK_BUNDLES["results"][0]
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.SHARE_LINK_BUNDLES_REBUILD}".format(
                pk=bundle_data["id"]
            ),
            status_code=200,
            json={**bundle_data, "status": "pending"},
        )
        result = await paperless.share_link_bundles.rebuild(bundle_data["id"])
        assert isinstance(result, ShareLinkBundle)
        assert result.id == bundle_data["id"]
