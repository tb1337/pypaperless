"""Tests for the model operation dispatcher."""

from collections.abc import Generator
from typing import ClassVar

import pytest
from pytest_httpx import HTTPXMock

from pypaperless import PaperlessClient
from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.dispatch import (
    _MODEL_TO_PROP_NAME,
    DispatchableCachedProperty,
    dispatchable_cached_property,
)
from pypaperless.exceptions import DispatchError
from pypaperless.models import DocumentNote, DocumentNoteDraft
from pypaperless.models.base import PaperlessModel
from pypaperless.models.tasks import Task
from pypaperless.services.base import PaperlessService, ResourceService
from pypaperless.services.mixins import DeletableService

from .const import PAPERLESS_TEST_URL
from .data import DATA_CORRESPONDENTS

# The helpers below cover DispatchableCachedProperty.__set_name__ edge cases via an
# annotation mutation trick: declare a return annotation mypy can check, then replace
# __annotations__["return"] with an unresolvable string so get_type_hints() raises at
# runtime. That reaches the defensive branches without any suppression comment.


def _factory_bad_type_hint(self: object) -> PaperlessService:
    """Provide a runtime-unresolvable return annotation."""
    raise NotImplementedError


# Overwrite the return annotation with an undefined name so get_type_hints raises.
_factory_bad_type_hint.__annotations__["return"] = "_UndefinedTypeAtRuntime_XYZABC"


def _factory_no_return_annotation(self: object) -> PaperlessService:
    """Remove return annotation so hints.get('return') is None."""
    raise NotImplementedError


# Removing the annotation makes hints.get("return") → None → not a PaperlessService.
del _factory_no_return_annotation.__annotations__["return"]


def _factory_base_service_return(self: object) -> PaperlessService:
    """Return the PaperlessService base, which has neither _resource_cls nor _draft_cls."""
    raise NotImplementedError


class _FakeDispatchTestModel(PaperlessModel):
    """Minimal PaperlessModel used only for dispatch coverage tests."""

    _api_path: ClassVar[str] = "/api/dispatch-fake/"


class _FakeWritableSubSvc(
    ResourceService,
    DeletableService[_FakeDispatchTestModel],
):
    """Writable sub-service with _resource_cls but no _draft_cls."""

    _api_path = "/api/dispatch-fake/"
    _resource = PaperlessResource.DOCUMENTS

    _resource_cls = _FakeDispatchTestModel
    # _draft_cls is deliberately omitted so the registration loop skips the draft branch.


def _bad_sub_fget(self: object) -> PaperlessService:
    """Property getter for bad_sub; its annotation is made unresolvable below."""
    raise NotImplementedError


# Overwrite return annotation with an undefined name so get_type_hints raises.
_bad_sub_fget.__annotations__["return"] = "_UndefinedSubTypeAtRuntime_XYZABC"


class _FakeSvcWithSubProps(PaperlessService):
    """Service with sub-properties exercising __set_name__ sub-discovery edge cases."""

    # bad_sub: annotation is an unresolvable string → get_type_hints raises.
    bad_sub: property = property(_bad_sub_fget)

    @property
    def str_sub(self) -> str:
        """Sub-property returning str — not a PaperlessService subclass."""
        return ""

    @property
    def writable_sub(self) -> _FakeWritableSubSvc:
        """Writable sub-service without _draft_cls."""
        raise NotImplementedError


def _factory_fake_with_sub_props(self: object) -> _FakeSvcWithSubProps:
    """Return _FakeSvcWithSubProps for __set_name__ sub-discovery edge cases."""
    raise NotImplementedError


@pytest.fixture(name="restore_registry")
def restore_registry_fixture() -> Generator[None]:
    """Undo registry writes made by __set_name__ so later tests see a clean registry."""
    before = dict(_MODEL_TO_PROP_NAME)
    try:
        yield
    finally:
        _MODEL_TO_PROP_NAME.clear()
        _MODEL_TO_PROP_NAME.update(before)


class TestDispatcherInit:
    """Verify ModelDispatcher construction."""

    def test_unknown_model_type_raises(self, api: PaperlessClient) -> None:
        """Dispatching a model type with no registered service raises DispatchError."""
        task = Task.model_construct()
        with pytest.raises(DispatchError, match="No service registered"):
            api._dispatcher._get_service(type(task))


class TestDispatchUpdate:
    """Verify that update() delegates to the correct service."""

    async def test_update_dispatches(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """update() on a Correspondent must call CorrespondentService.update."""
        pk = DATA_CORRESPONDENTS["results"][0]["id"]
        # fetch the model via the service
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.CORRESPONDENTS_SINGLE}".format(pk=pk),
            status_code=200,
            json=DATA_CORRESPONDENTS["results"][0],
        )
        corr = await paperless.correspondents(pk)

        # mutate and mock the PATCH
        corr.name = "Dispatcher Updated"
        httpx_mock.add_response(
            method="PATCH",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.CORRESPONDENTS_SINGLE}".format(pk=pk),
            status_code=200,
            json={**corr.snapshot, "name": "Dispatcher Updated"},
        )
        result = await paperless.update(corr)
        assert result is True
        assert corr.name == "Dispatcher Updated"

    async def test_update_no_change_returns_false(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """update() without any mutations must return False (no request sent)."""
        pk = DATA_CORRESPONDENTS["results"][0]["id"]
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.CORRESPONDENTS_SINGLE}".format(pk=pk),
            status_code=200,
            json=DATA_CORRESPONDENTS["results"][0],
        )
        corr = await paperless.correspondents(pk)
        result = await paperless.update(corr)
        assert result is False


class TestDispatchDelete:
    """Verify that delete() delegates to the correct service."""

    async def test_delete_dispatches(
        self, httpx_mock: HTTPXMock, paperless: PaperlessClient
    ) -> None:
        """delete() on a Correspondent must call CorrespondentService.delete."""
        pk = DATA_CORRESPONDENTS["results"][0]["id"]
        httpx_mock.add_response(
            method="GET",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.CORRESPONDENTS_SINGLE}".format(pk=pk),
            status_code=200,
            json=DATA_CORRESPONDENTS["results"][0],
        )
        corr = await paperless.correspondents(pk)

        httpx_mock.add_response(
            method="DELETE",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.CORRESPONDENTS_SINGLE}".format(pk=pk),
            status_code=204,
        )
        await paperless.delete(corr)  # must not raise


class TestDispatchSave:
    """Verify that save() delegates to the correct service."""

    async def test_save_dispatches(self, httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
        """save() on a CorrespondentDraft must call CorrespondentService.save."""
        draft = paperless.correspondents.create(
            name="New via Dispatcher",
            match="",
            matching_algorithm=1,
            is_insensitive=True,
        )
        httpx_mock.add_response(
            method="POST",
            url=f"{PAPERLESS_TEST_URL}{EndpointPath.CORRESPONDENTS}",
            status_code=200,
            json={"id": 99, "name": "New via Dispatcher"},
        )
        new_id = await paperless.save(draft)
        assert new_id == 99


class TestDispatchableCachedPropertyBehavior:
    """Verify DispatchableCachedProperty descriptor behaviour and __set_name__ edge cases."""

    def test_class_level_access_returns_descriptor(self) -> None:
        """Accessing the property on the class (obj=None) must return the descriptor itself."""
        result = PaperlessClient.correspondents
        assert isinstance(result, dispatchable_cached_property)

    def test_set_name_silences_type_hints_error(self) -> None:
        """__set_name__ must return silently when get_type_hints raises."""
        prop = DispatchableCachedProperty(_factory_bad_type_hint)
        prop.__set_name__(object, "bad_hint_prop")
        assert prop._attr_name == "bad_hint_prop"

    @pytest.mark.usefixtures("restore_registry")
    def test_set_name_skips_non_service_return(self) -> None:
        """__set_name__ must not touch the registry when the return type is not a service."""
        prop = DispatchableCachedProperty(_factory_no_return_annotation)
        before = dict(_MODEL_TO_PROP_NAME)
        prop.__set_name__(object, "no_return_prop")
        assert before == _MODEL_TO_PROP_NAME

    @pytest.mark.usefixtures("restore_registry")
    def test_set_name_handles_service_without_model_cls(self) -> None:
        """__set_name__ must not crash when _resource_cls/_draft_cls are absent."""
        prop = DispatchableCachedProperty(_factory_base_service_return)
        before = dict(_MODEL_TO_PROP_NAME)
        prop.__set_name__(object, "base_svc_prop")
        assert before == _MODEL_TO_PROP_NAME

    @pytest.mark.usefixtures("restore_registry")
    def test_set_name_sub_prop_discovery(self) -> None:
        """Sub-property discovery registers only the writable sub-service.

        ``bad_sub`` has an unresolvable annotation and ``str_sub`` does not return a
        PaperlessService, so both are skipped; ``writable_sub`` is registered under its
        _resource_cls even though it has no _draft_cls.
        """
        prop = DispatchableCachedProperty(_factory_fake_with_sub_props)
        prop.__set_name__(object, "fake_sub_prop")

        assert prop._attr_name == "fake_sub_prop"
        assert _MODEL_TO_PROP_NAME[_FakeDispatchTestModel] == ("fake_sub_prop", "writable_sub")
        # the skipped sub-properties contributed no entry of their own
        registered = [
            key for key, value in _MODEL_TO_PROP_NAME.items() if value[0] == prop._attr_name
        ]
        assert registered == [_FakeDispatchTestModel]


class TestDispatchGuards:
    """Verify DispatchError is raised when a service lacks a required operation."""

    async def test_update_raises_for_non_updatable_service(self, api: PaperlessClient) -> None:
        """update() must raise DispatchError when the resolved service is not UpdatableService."""
        note = DocumentNote.model_construct(id=1, document=42)
        with pytest.raises(DispatchError, match="does not support 'update'"):
            await api._dispatcher.update(note)

    async def test_delete_raises_for_non_deletable_service(
        self, api: PaperlessClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """delete() must raise DispatchError when the resolved service is not DeletableService."""
        monkeypatch.setitem(_MODEL_TO_PROP_NAME, DocumentNote, ("profile",))
        note = DocumentNote.model_construct(id=1, document=42)
        with pytest.raises(DispatchError, match="does not support 'delete'"):
            await api._dispatcher.delete(note)

    async def test_save_raises_for_non_creatable_service(
        self, api: PaperlessClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """save() must raise DispatchError when the resolved service is not CreatableService."""
        monkeypatch.setitem(_MODEL_TO_PROP_NAME, DocumentNoteDraft, ("profile",))
        draft = DocumentNoteDraft.model_construct(note="x", document=42)
        with pytest.raises(DispatchError, match="does not support 'save'"):
            await api._dispatcher.save(draft)
