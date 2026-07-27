"""Parameterized service mixin tests: ReadOnly, ReadWrite, SecurableService."""

import asyncio
import json as json_mod
import re

import httpx
import pytest
from pytest_httpx import HTTPXMock

from pypaperless import PaperlessClient
from pypaperless.const import EndpointPath
from pypaperless.exceptions import DeletionError, DraftFieldRequiredError, NotFoundError
from pypaperless.models import Page
from pypaperless.models.base import PaperlessModel
from pypaperless.models.types import Permissions
from pypaperless.services import mixins as svc_mixins
from pypaperless.services.base import ResourceService

from .const import PAPERLESS_TEST_URL
from .data import DATA_OBJECT_PERMISSIONS
from .mappings import (
    CORRESPONDENT_MAP,
    CUSTOM_FIELD_MAP,
    DOCUMENT_MAP,
    DOCUMENT_TYPE_MAP,
    GROUP_MAP,
    MAIL_ACCOUNT_MAP,
    MAIL_RULE_MAP,
    PROCESSED_MAIL_MAP,
    SAVED_VIEW_MAP,
    SHARE_LINK_BUNDLE_MAP,
    SHARE_LINK_MAP,
    STORAGE_PATH_MAP,
    TAG_MAP,
    USER_MAP,
    WORKFLOW_MAP,
    ResourceTestMapping,
)


class _SharedServiceTests:
    """Shared read-only test methods inherited by TestReadOnly and TestReadWrite."""

    async def test_pages(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """Test pages."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                f"{PAPERLESS_TEST_URL}{EndpointPath[mapping.resource.upper()]}"
                r"\?.*$"
            ),
            status_code=200,
            json=mapping.data,
        )
        page = await anext(aiter(getattr(paperless, mapping.resource).pages(1)))
        assert isinstance(page, Page)
        assert isinstance(page.items, list)
        for item in page.items:
            assert isinstance(item, mapping.model_cls)

    async def test_iter(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """Test iter."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                f"{PAPERLESS_TEST_URL}{EndpointPath[mapping.resource.upper()]}"
                r"\?.*$"
            ),
            status_code=200,
            json=mapping.data,
        )
        async for item in getattr(paperless, mapping.resource):
            assert isinstance(item, mapping.model_cls)

    async def test_call(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """Test call."""
        httpx_mock.add_response(
            method="GET",
            url=(
                f"{PAPERLESS_TEST_URL}{EndpointPath[(mapping.resource + '_single').upper()]}"
            ).format(pk=1),
            status_code=200,
            json=mapping.data["results"][0],
        )
        item = await getattr(paperless, mapping.resource)(1)
        assert item
        assert isinstance(item, mapping.model_cls)
        # must raise as 1337 doesn't exist
        httpx_mock.add_response(
            method="GET",
            url=(
                f"{PAPERLESS_TEST_URL}{EndpointPath[(mapping.resource + '_single').upper()]}"
            ).format(pk=1337),
            status_code=404,
        )
        with pytest.raises(NotFoundError):
            await getattr(paperless, mapping.resource)(1337)


@pytest.mark.parametrize(
    "mapping",
    [
        DOCUMENT_MAP,
        DOCUMENT_TYPE_MAP,
        CORRESPONDENT_MAP,
        CUSTOM_FIELD_MAP,
        GROUP_MAP,
        MAIL_ACCOUNT_MAP,
        MAIL_RULE_MAP,
        PROCESSED_MAIL_MAP,
        SAVED_VIEW_MAP,
        SHARE_LINK_BUNDLE_MAP,
        SHARE_LINK_MAP,
        STORAGE_PATH_MAP,
        TAG_MAP,
        USER_MAP,
        WORKFLOW_MAP,
    ],
    scope="class",
)
class TestReadOnly(_SharedServiceTests):
    """Read-only service operations: pages, iteration, dict/list helpers, single fetch."""

    async def test_as_dict(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """Test as_dict."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                f"{PAPERLESS_TEST_URL}{EndpointPath[mapping.resource.upper()]}"
                r"\?.*$"
            ),
            status_code=200,
            json=mapping.data,
        )
        items = await getattr(paperless, mapping.resource).as_dict()
        for pk, obj in items.items():
            assert isinstance(pk, int)
            assert isinstance(obj, mapping.model_cls)

    async def test_as_list(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """Test as_list."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                f"{PAPERLESS_TEST_URL}{EndpointPath[mapping.resource.upper()]}"
                r"\?.*$"
            ),
            status_code=200,
            json=mapping.data,
        )
        items = await getattr(paperless, mapping.resource).as_list()
        for obj in items:
            assert isinstance(obj, mapping.model_cls)


@pytest.mark.parametrize(
    "mapping",
    [
        CORRESPONDENT_MAP,
        CUSTOM_FIELD_MAP,
        DOCUMENT_TYPE_MAP,
        SHARE_LINK_BUNDLE_MAP,
        SHARE_LINK_MAP,
        STORAGE_PATH_MAP,
        TAG_MAP,
    ],
    scope="class",
)
class TestReadWrite(_SharedServiceTests):
    """R/W service operations: filter, create, update, delete (in addition to read)."""

    async def test_filter(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """Test iter with filter."""
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                f"{PAPERLESS_TEST_URL}{EndpointPath[mapping.resource.upper()]}"
                r"\?.*$"
            ),
            status_code=200,
            json=mapping.data,
        )
        async with getattr(paperless, mapping.resource).filter(
            any_filter_param="1",
            any_filter_list__in=["1", "2"],
            any_filter_no_list__in="1",
        ) as q:
            async for item in q:
                assert isinstance(item, mapping.model_cls)

    async def test_create(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """Test create."""
        service = getattr(paperless, mapping.resource)
        draft = service.create(**mapping.draft_defaults)
        assert isinstance(draft, mapping.draft_cls)
        # test that blanking out the required field raises DraftFieldRequiredError
        if mapping.required_field is not None:
            backup = getattr(draft, mapping.required_field)
            setattr(draft, mapping.required_field, None)
            with pytest.raises(DraftFieldRequiredError):
                await service.save(draft)
            setattr(draft, mapping.required_field, backup)
        # actually call the create endpoint
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath[mapping.resource.upper()]}",
            status_code=200,
            json={
                "id": len(mapping.data["results"]),
                **draft.serialize(),
            },
        )
        new_pk = await service.save(draft)
        assert new_pk >= 1

    async def test_update(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """Test update."""
        update_field = mapping.update_field
        update_value = mapping.update_value
        pk = mapping.data["results"][0]["id"]
        service = getattr(paperless, mapping.resource)
        single_url = (
            f"{PAPERLESS_TEST_URL}{EndpointPath[(mapping.resource + '_single').upper()]}"
        ).format(pk=pk)
        httpx_mock.add_response(
            method="GET",
            url=single_url,
            status_code=200,
            json=mapping.data["results"][0],
        )
        to_update = await service(pk)
        setattr(to_update, update_field, update_value)
        httpx_mock.add_response(
            method="PATCH",
            url=single_url,
            status_code=200,
            json={**to_update.snapshot, update_field: update_value},
        )
        assert await service.update(to_update) is True
        assert json_mod.loads(httpx_mock.get_requests()[-1].content) == {update_field: update_value}
        # no-op update must not hit the API at all
        sent = len(httpx_mock.get_requests())
        assert await service.update(to_update) is False
        assert len(httpx_mock.get_requests()) == sent
        # force full update
        setattr(to_update, update_field, update_value)
        httpx_mock.add_response(
            method="PUT",
            url=single_url,
            status_code=200,
            json={**to_update.snapshot, update_field: update_value},
        )
        expected_full = to_update.api_dump()
        assert await service.update(to_update, only_changed=False) is True
        assert json_mod.loads(httpx_mock.get_requests()[-1].content) == expected_full
        assert getattr(to_update, update_field) == update_value

    async def test_delete(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """Test delete."""
        pk = mapping.data["results"][0]["id"]
        service = getattr(paperless, mapping.resource)
        httpx_mock.add_response(
            method="GET",
            url=(
                f"{PAPERLESS_TEST_URL}{EndpointPath[(mapping.resource + '_single').upper()]}"
            ).format(pk=pk),
            status_code=200,
            json=mapping.data["results"][0],
        )
        to_delete = await service(pk)
        httpx_mock.add_response(
            method="DELETE",
            url=(
                f"{PAPERLESS_TEST_URL}{EndpointPath[(mapping.resource + '_single').upper()]}"
            ).format(pk=pk),
            status_code=204,
        )
        await service.delete(to_delete)
        # failed deletion raises DeletionError
        httpx_mock.add_response(
            method="DELETE",
            url=(
                f"{PAPERLESS_TEST_URL}{EndpointPath[(mapping.resource + '_single').upper()]}"
            ).format(pk=pk),
            status_code=404,
        )
        with pytest.raises(DeletionError):
            await service.delete(to_delete)
        # silent_fail=True suppresses DeletionError
        httpx_mock.add_response(
            method="DELETE",
            url=(
                f"{PAPERLESS_TEST_URL}{EndpointPath[(mapping.resource + '_single').upper()]}"
            ).format(pk=pk),
            status_code=404,
        )
        await service.delete(to_delete, silent_fail=True)


@pytest.mark.parametrize(
    "mapping",
    [
        CORRESPONDENT_MAP,
        DOCUMENT_MAP,
        DOCUMENT_TYPE_MAP,
        STORAGE_PATH_MAP,
        TAG_MAP,
    ],
    scope="class",
)
class TestSecurableService:
    """SecurableService: request_permissions flag, with_permissions() context manager."""

    async def test_permissions(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """Test permissions."""
        getattr(paperless, mapping.resource).request_permissions = True
        assert getattr(paperless, mapping.resource).request_permissions
        # single object with permissions
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                + (
                    f"{PAPERLESS_TEST_URL}{EndpointPath[(mapping.resource + '_single').upper()]}"
                ).format(pk=1)
                + r"\?.*$"
            ),
            status_code=200,
            json={**mapping.data["results"][0], "permissions": DATA_OBJECT_PERMISSIONS},
        )
        item = await getattr(paperless, mapping.resource)(1)
        assert httpx_mock.get_requests()[-1].url.params["full_perms"] == "true"
        assert item.has_permissions
        assert isinstance(item.permissions, Permissions)
        # iterator with permissions
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                f"{PAPERLESS_TEST_URL}{EndpointPath[mapping.resource.upper()]}"
                r"\?.*$"
            ),
            status_code=200,
            json={
                **mapping.data,
                "results": [
                    {**item, "permissions": DATA_OBJECT_PERMISSIONS}
                    for item in mapping.data["results"]
                ],
            },
        )
        items = [item async for item in getattr(paperless, mapping.resource)]
        assert httpx_mock.get_requests()[-1].url.params["full_perms"] == "true"
        assert len(items) == len(mapping.data["results"])
        for item in items:
            assert isinstance(item, mapping.model_cls)
            assert item.has_permissions
            assert isinstance(item.permissions, Permissions)

    async def test_permission_change(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """Test permission mutation is serialised in the PATCH request."""
        pk = mapping.data["results"][0]["id"]
        getattr(paperless, mapping.resource).request_permissions = True
        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                + (
                    f"{PAPERLESS_TEST_URL}{EndpointPath[(mapping.resource + '_single').upper()]}"
                ).format(pk=pk)
                + r"\?.*$"
            ),
            status_code=200,
            json={**mapping.data["results"][0], "permissions": DATA_OBJECT_PERMISSIONS},
        )
        item = await getattr(paperless, mapping.resource)(pk)
        item.permissions.view.users.append(23)

        def _lookup_set_permissions(request: httpx.Request) -> httpx.Response:
            assert request.url
            json_data = json_mod.loads(request.content)
            assert "set_permissions" in json_data
            return httpx.Response(status_code=200, json=item.snapshot)

        httpx_mock.add_callback(
            _lookup_set_permissions,
            url=re.compile(
                r"^"
                + re.escape(
                    (
                        f"{PAPERLESS_TEST_URL}"
                        f"{EndpointPath[(mapping.resource + '_single').upper()]}"
                    ).format(pk=pk)
                )
                + r"\?.*$"
            ),
            method="PATCH",
        )
        await getattr(paperless, mapping.resource).update(item)

    async def test_with_permissions_context_manager(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient, mapping: ResourceTestMapping
    ) -> None:
        """with_permissions() enables the flag task-locally and resets it on exit."""
        service = getattr(paperless, mapping.resource)
        assert not service.request_permissions

        httpx_mock.add_response(
            method="GET",
            url=re.compile(
                r"^"
                + (
                    f"{PAPERLESS_TEST_URL}{EndpointPath[(mapping.resource + '_single').upper()]}"
                ).format(pk=1)
                + r"\?.*$"
            ),
            status_code=200,
            json={**mapping.data["results"][0], "permissions": DATA_OBJECT_PERMISSIONS},
        )

        async with service.with_permissions() as scoped:
            assert scoped.request_permissions
            item = await scoped(1)
            assert item.has_permissions
            assert isinstance(item.permissions, Permissions)

        assert not service.request_permissions


# ---------------------------------------------------------------------------
# Standalone model / mixin unit tests
# ---------------------------------------------------------------------------


def test_permissions_from_existing_instance() -> None:
    """Permissions._accept_flat passes through non-dict input (e.g. an existing instance)."""
    # Call _accept_flat directly with a non-dict value — it must return it unchanged
    non_dict_input = [1, 2, 3]
    result = Permissions._accept_flat(non_dict_input)
    assert result is non_dict_input


async def test_iterable_filter_base_method(paperless: PaperlessClient) -> None:
    """IterableService.filter() applies filters for the context duration and clears them after."""

    class _MinimalModel(PaperlessModel):
        id: int | None = None

    class _MinimalService(ResourceService, svc_mixins.IterableService[_MinimalModel]):
        _api_path = EndpointPath.CORRESPONDENTS
        _resource = "correspondents"
        _resource_cls = _MinimalModel

    svc = _MinimalService(paperless)
    async with svc.filter(title__icontains="test") as ctx:
        assert ctx is svc
        generator = ctx.pages()
        assert generator.params["title__icontains"] == "test"
    generator = svc.pages()
    assert "title__icontains" not in generator.params


async def test_filter_contexts_are_isolated(
    httpx_mock: HTTPXMock, paperless: PaperlessClient
) -> None:
    """Overlapping filter() contexts on the same service must not clobber each other."""
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"^" f"{PAPERLESS_TEST_URL}{EndpointPath.CORRESPONDENTS}" r"\?.*$"),
        status_code=200,
        json={"count": 0, "next": None, "previous": None, "results": []},
        is_reusable=True,
    )
    async with paperless.correspondents.filter(name__icontains="acme") as ctx_a:
        async with paperless.correspondents.filter(name__icontains="globex") as ctx_b:
            await ctx_b.as_list()
        # ctx_b has exited — ctx_a must still carry its own filters
        await ctx_a.as_list()

    requests = httpx_mock.get_requests()
    assert requests[-2].url.params["name__icontains"] == "globex"
    assert requests[-1].url.params["name__icontains"] == "acme"


async def test_filter_joins_in_and_all_lists(
    httpx_mock: HTTPXMock, paperless: PaperlessClient
) -> None:
    """List values for __in and __all filters are sent comma-separated, not repeated."""
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"^" f"{PAPERLESS_TEST_URL}{EndpointPath.DOCUMENTS}" r"\?.*$"),
        status_code=200,
        json={"count": 0, "next": None, "previous": None, "results": []},
    )
    async with paperless.documents.filter(
        id__in=[1, 2],
        tags__id__all=[3, 7],
    ) as filtered:
        await filtered.as_list()

    request = httpx_mock.get_requests()[-1]
    assert request.url.params["id__in"] == "1,2"
    assert request.url.params["tags__id__all"] == "3,7"


async def test_filter_contexts_isolated_across_tasks(
    httpx_mock: HTTPXMock, paperless: PaperlessClient
) -> None:
    """Concurrent tasks filtering the same service must each keep their own filters."""
    httpx_mock.add_response(
        method="GET",
        url=re.compile(r"^" f"{PAPERLESS_TEST_URL}{EndpointPath.CORRESPONDENTS}" r"\?.*$"),
        status_code=200,
        json={"count": 0, "next": None, "previous": None, "results": []},
        is_reusable=True,
    )

    async def fetch(name: str) -> None:
        async with paperless.correspondents.filter(name__icontains=name) as filtered:
            await asyncio.sleep(0)
            await filtered.as_list()

    await asyncio.gather(fetch("acme"), fetch("globex"))

    sent = {req.url.params["name__icontains"] for req in httpx_mock.get_requests()[-2:]}
    assert sent == {"acme", "globex"}
