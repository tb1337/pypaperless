"""Tests for filter TypedDicts and typed service .filter() methods."""

import re
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from pypaperless import PaperlessClient
from pypaperless.const import EndpointPath

from .const import PAPERLESS_TEST_URL
from .data import (
    DATA_CORRESPONDENTS,
    DATA_CUSTOM_FIELDS,
    DATA_DOCUMENT_TYPES,
    DATA_DOCUMENTS,
    DATA_GROUPS,
    DATA_SHARE_LINK_BUNDLES,
    DATA_SHARE_LINKS,
    DATA_STORAGE_PATHS,
    DATA_TAGS,
    DATA_TASKS,
    DATA_TRASH,
    DATA_USERS,
)


def _expected_param(value: Any) -> str:
    """Return the query string form Paperless receives for a filter value."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(map(str, value))
    return str(value)


@pytest.mark.parametrize(
    ("api_key", "service_attr", "filter_kwargs", "mock_data"),
    [
        (
            "documents",
            "documents",
            {"title__icontains": "invoice", "is_tagged": True, "id__in": [1, 2]},
            DATA_DOCUMENTS,
        ),
        ("correspondents", "correspondents", {"name__icontains": "acme"}, DATA_CORRESPONDENTS),
        ("tags", "tags", {"is_root": True}, DATA_TAGS),
        ("storage_paths", "storage_paths", {"path__icontains": "/invoices"}, DATA_STORAGE_PATHS),
        ("trash", "trash", {"title__icontains": "old"}, DATA_TRASH),
        ("groups", "groups", {"name__icontains": "admin"}, DATA_GROUPS),
        ("users", "users", {"username__icontains": "admin"}, DATA_USERS),
        (
            "share_link_bundles",
            "share_link_bundles",
            {"status": "ready", "documents": 1},
            DATA_SHARE_LINK_BUNDLES,
        ),
        (
            "custom_fields",
            "custom_fields",
            {"name__icontains": "project"},
            DATA_CUSTOM_FIELDS,
        ),
        (
            "document_types",
            "document_types",
            {"name__icontains": "invoice"},
            DATA_DOCUMENT_TYPES,
        ),
        (
            "share_links",
            "share_links",
            {"expiration__year": 2025},
            DATA_SHARE_LINKS,
        ),
        (
            "tasks",
            "tasks",
            {"status": "pending"},
            DATA_TASKS,
        ),
    ],
    ids=[
        "documents",
        "correspondents",
        "tags",
        "storage_paths",
        "trash",
        "groups",
        "users",
        "share_link_bundles",
        "custom_fields",
        "document_types",
        "share_links",
        "tasks",
    ],
)
async def test_service_filter_forwards_typed_kwargs(
    *,
    httpx_mock: HTTPXMock,
    paperless: PaperlessClient,
    api_key: str,
    service_attr: str,
    filter_kwargs: dict,
    mock_data: dict,
) -> None:
    """service.filter() forwards every typed filter kwarg into the query string."""
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"^" + f"{PAPERLESS_TEST_URL}{EndpointPath[api_key.upper()]}" + r"\?.*$"),
        status_code=200,
        json=mock_data,
    )
    async with getattr(paperless, service_attr).filter(**filter_kwargs) as q:
        items = [item async for item in q]

    assert len(items) == len(mock_data["results"])

    params = httpx_mock.get_requests()[-1].url.params
    for key, value in filter_kwargs.items():
        assert params[key] == _expected_param(value)
