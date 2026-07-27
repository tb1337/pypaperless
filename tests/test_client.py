"""Tests for the PaperlessClient client: init, context, requests, URL, token, Page model."""

import datetime
import re
from io import BytesIO
from typing import Any

import httpx
import pytest
from pydantic import BaseModel, Field, ValidationError
from pytest_httpx import HTTPXMock

from pypaperless import PaperlessClient, PaperlessSettings, generate_api_token
from pypaperless.const import API_VERSION, EndpointPath
from pypaperless.exceptions import (
    BadJsonResponseError,
    DeletionError,
    DraftNotSupportedError,
    ForbiddenError,
    InactiveOrDeletedError,
    InitializationError,
    InvalidTokenError,
    JsonResponseWithError,
    NotFoundError,
    PaperlessConnectionError,
    PaperlessTimeoutError,
    UnexpectedStatusError,
)
from pypaperless.models import Page
from pypaperless.models.base import PaperlessModel
from pypaperless.pagination import PageGenerator
from pypaperless.services import mixins as service_mixins
from pypaperless.services.base import ResourceService
from pypaperless.transport import PaperlessTransport
from pypaperless.utils import normalize_base_url, process_form_data
from tests.const import (
    PAPERLESS_TEST_API_VERSION,
    PAPERLESS_TEST_PASSWORD,
    PAPERLESS_TEST_TOKEN,
    PAPERLESS_TEST_URL,
    PAPERLESS_TEST_USER,
    PAPERLESS_TEST_VERSION,
)

from .data import DATA_PATHS, DATA_TOKEN


def _multipart_parts(body: str) -> dict[str, list[str]]:
    """Return ``{field name: [value, ...]}`` for a multipart/form-data body."""
    parts: dict[str, list[str]] = {}
    for match in re.finditer(r'name="([^"]+)"[^\r\n]*\r\n(?:[^\r\n]+\r\n)*\r\n(.*?)\r\n--', body):
        parts.setdefault(match.group(1), []).append(match.group(2))
    return parts


async def test_init(httpx_mock: HTTPXMock, api: PaperlessClient) -> None:
    """Test initialization."""
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.INDEX}",
        method="GET",
        status_code=200,
        json=DATA_PATHS,
    )
    await api.initialize()
    assert api.is_initialized
    await api.close()


async def test_init_reads_version_headers(httpx_mock: HTTPXMock, api: PaperlessClient) -> None:
    """initialize() picks host_api_version / host_version up from the response headers."""
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.INDEX}",
        method="GET",
        status_code=200,
        json=DATA_PATHS,
        headers={
            "x-api-version": str(PAPERLESS_TEST_API_VERSION),
            "x-version": PAPERLESS_TEST_VERSION,
        },
    )
    await api.initialize()
    assert api.host_api_version == PAPERLESS_TEST_API_VERSION
    assert api.host_version == PAPERLESS_TEST_VERSION
    assert api.runtime.api_version == PAPERLESS_TEST_API_VERSION
    await api.close()


async def test_init_without_version_headers(httpx_mock: HTTPXMock, api: PaperlessClient) -> None:
    """A host that sends no version headers falls back to the compiled-in API version."""
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.INDEX}",
        method="GET",
        status_code=200,
        json=DATA_PATHS,
    )
    await api.initialize()
    assert api.host_api_version == API_VERSION
    assert api.host_version is None
    await api.close()


async def test_context(httpx_mock: HTTPXMock, api: PaperlessClient) -> None:
    """Test async context manager initializes the client."""
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.INDEX}",
        method="GET",
        status_code=200,
        json=DATA_PATHS,
    )
    async with api:
        assert api.is_initialized


async def test_init_error(httpx_mock: HTTPXMock, api: PaperlessClient) -> None:
    """Test that initialization raises the correct errors for each failure mode."""
    # connection error
    httpx_mock.add_exception(httpx.ConnectError("Connection refused"))
    with pytest.raises(PaperlessConnectionError):
        await api.initialize()

    # timeout
    httpx_mock.add_exception(httpx.ReadTimeout("Read timed out"))
    with pytest.raises(PaperlessTimeoutError):
        await api.initialize()

    # any other transport error
    httpx_mock.add_exception(httpx.RemoteProtocolError("Server disconnected"))
    with pytest.raises(PaperlessConnectionError):
        await api.initialize()

    # HTTP 401 - wrong token
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.INDEX}",
        method="GET",
        status_code=401,
        text="any html",
    )
    with pytest.raises(InvalidTokenError):
        await api.initialize()

    # HTTP 401 - inactive / deleted user
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.INDEX}",
        method="GET",
        status_code=401,
        json={"detail": "User is inactive"},
    )
    with pytest.raises(InactiveOrDeletedError):
        await api.initialize()

    # HTTP 403 - forbidden
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.INDEX}",
        method="GET",
        status_code=403,
        text="any html",
    )
    with pytest.raises(ForbiddenError):
        await api.initialize()

    # HTTP 200 with non-JSON body
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.INDEX}",
        method="GET",
        status_code=200,
        text="any html",
    )
    with pytest.raises(InitializationError):
        await api.initialize()


async def test_request(httpx_mock: HTTPXMock) -> None:
    """Test request_raw, including form data encoding."""
    # use uninitialised client to bypass session setup
    api = PaperlessClient(PAPERLESS_TEST_URL, PAPERLESS_TEST_TOKEN)

    httpx_mock.add_response(url=PAPERLESS_TEST_URL, method="GET", status_code=200)
    res = await api._runtime.transport.request_raw("get", PAPERLESS_TEST_URL)
    assert res.status_code == 200

    form_data = {
        "none_field": None,
        "str_field": "Hello Bytes!",
        "bytes_field": b"Hello String!",
        "tuple_field": (b"Document Content", "filename.pdf"),
        "int_field": 23,
        "float_field": 13.37,
        "int_list": [1, 1, 2, 3, 5, 8, 13],
        "dict_field": {"dict_str_field": "str", "dict_int_field": 2},
    }
    httpx_mock.add_response(url=PAPERLESS_TEST_URL, method="POST", status_code=200)
    res = await api._runtime.transport.request_raw("post", PAPERLESS_TEST_URL, form=form_data)
    assert res.status_code == 200

    body = httpx_mock.get_requests()[-1].content.decode()
    parts = _multipart_parts(body)

    # None is dropped entirely
    assert "none_field" not in parts
    # scalars are stringified
    assert parts["str_field"] == ["Hello Bytes!"]
    assert parts["int_field"] == ["23"]
    assert parts["float_field"] == ["13.37"]
    # lists become repeated values under the same name
    assert parts["int_list"] == ["1", "1", "2", "3", "5", "8", "13"]
    # dicts are flattened, the outer key disappears
    assert "dict_field" not in parts
    assert parts["dict_str_field"] == ["str"]
    assert parts["dict_int_field"] == ["2"]
    # bytes become an unnamed file, 2-tuples carry the filename
    assert 'name="bytes_field"; filename=' in body
    assert parts["bytes_field"] == ["Hello String!"]
    assert 'name="tuple_field"; filename="filename.pdf"' in body
    assert parts["tuple_field"] == ["Document Content"]

    await api.close()


async def test_request_json(httpx_mock: HTTPXMock, api: PaperlessClient) -> None:
    """Test get() raises on bad content-type or non-JSON body."""
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}/400-json-error-payload",
        method="GET",
        status_code=400,
        headers={"Content-Type": "application/json"},
        json={"error": "sample message"},
    )
    url_400 = f"{PAPERLESS_TEST_URL}/400-json-error-payload"
    with pytest.raises(JsonResponseWithError):
        await api._runtime.transport.get(url_400)

    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}/200-text-error-payload",
        method="GET",
        status_code=200,
        headers={"Content-Type": "text/plain"},
        text='{"error": "sample message"}',
    )
    url_200_text = f"{PAPERLESS_TEST_URL}/200-text-error-payload"
    with pytest.raises(BadJsonResponseError):
        await api._runtime.transport.get(url_200_text)

    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}/200-json-text-body",
        method="GET",
        status_code=200,
        headers={"Content-Type": "application/json"},
        text="test 5 23 42 1337",
    )
    url_200_json = f"{PAPERLESS_TEST_URL}/200-json-text-body"
    with pytest.raises(BadJsonResponseError):
        await api._runtime.transport.get(url_200_json)


@pytest.mark.parametrize(
    ("input_url", "expected"),
    [
        ("hostname", "https://hostname"),
        ("http://hostname", "http://hostname"),
        ("ftp://hostname", "https://ftp://hostname"),
        ("hostname:80", "https://hostname:80"),
        ("hostname/api/api/", "https://hostname/api/api"),
        ("hostname/api/endpoint///", "https://hostname/api/endpoint"),
    ],
)
def test_create_url(input_url: str, expected: str) -> None:
    """normalize_base_url handles all URL edge cases correctly."""
    assert normalize_base_url(input_url) == expected


async def test_generate_api_token(httpx_mock: HTTPXMock) -> None:
    """Test token generation success and failure modes."""
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.TOKEN}",
        method="POST",
        status_code=200,
        json=DATA_TOKEN,
    )
    token = await generate_api_token(
        PAPERLESS_TEST_URL,
        PAPERLESS_TEST_USER,
        PAPERLESS_TEST_PASSWORD,
    )
    assert token == PAPERLESS_TEST_TOKEN

    # scheme-less URLs are normalized like in PaperlessClient
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.TOKEN}",
        method="POST",
        status_code=200,
        json=DATA_TOKEN,
    )
    token = await generate_api_token(
        PAPERLESS_TEST_URL.removeprefix("https://"),
        PAPERLESS_TEST_USER,
        PAPERLESS_TEST_PASSWORD,
    )
    assert token == PAPERLESS_TEST_TOKEN

    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.TOKEN}",
        method="POST",
        status_code=200,
        json={"blah": "any string"},
    )
    with pytest.raises(BadJsonResponseError):
        await generate_api_token(
            PAPERLESS_TEST_URL,
            PAPERLESS_TEST_USER,
            PAPERLESS_TEST_PASSWORD,
        )

    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.TOKEN}",
        method="POST",
        status_code=400,
        json={"non_field_errors": ["Unable to log in."]},
    )
    with pytest.raises(JsonResponseWithError):
        await generate_api_token(
            PAPERLESS_TEST_URL,
            PAPERLESS_TEST_USER,
            PAPERLESS_TEST_PASSWORD,
        )

    httpx_mock.add_exception(
        ValueError(),
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.TOKEN}",
        method="POST",
    )
    with pytest.raises(ValueError):  # noqa: PT011
        await generate_api_token(
            PAPERLESS_TEST_URL,
            PAPERLESS_TEST_USER,
            PAPERLESS_TEST_PASSWORD,
        )

    # transport errors are wrapped like in PaperlessTransport
    httpx_mock.add_exception(
        httpx.ConnectTimeout("Connect timed out"),
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.TOKEN}",
        method="POST",
    )
    with pytest.raises(PaperlessTimeoutError):
        await generate_api_token(
            PAPERLESS_TEST_URL,
            PAPERLESS_TEST_USER,
            PAPERLESS_TEST_PASSWORD,
        )

    httpx_mock.add_exception(
        httpx.ConnectError("Connection refused"),
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.TOKEN}",
        method="POST",
    )
    with pytest.raises(PaperlessConnectionError):
        await generate_api_token(
            PAPERLESS_TEST_URL,
            PAPERLESS_TEST_USER,
            PAPERLESS_TEST_PASSWORD,
        )

    # passing an explicit httpx client still returns the correct token
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.TOKEN}",
        method="POST",
        status_code=200,
        json=DATA_TOKEN,
    )
    token = await generate_api_token(
        PAPERLESS_TEST_URL,
        PAPERLESS_TEST_USER,
        PAPERLESS_TEST_PASSWORD,
        client=httpx.AsyncClient(),
    )
    assert token == PAPERLESS_TEST_TOKEN


async def test_pages_object(api: PaperlessClient) -> None:
    """Test Page model construction, iteration, and navigation helpers."""

    class TestResource(PaperlessModel):
        id: int | None = None

    data: dict = {
        "count": 0,
        "next": "any.url",
        "previous": None,
        "all": [],
        "results": [],
    }
    for i in range(1, 101):
        data["count"] += 1
        data["all"].append(i)
        data["results"].append({"id": i})

    page = Page.from_data(
        api._runtime, data, resource_cls=TestResource, current_page=1, page_size=25
    )

    assert isinstance(page, Page)
    assert page.current_count == 100
    for item in page:
        assert isinstance(item, TestResource)

    # first page
    assert not page.has_previous_page
    assert page.has_next_page
    assert not page.is_last_page
    assert page.last_page == 4
    assert page.next_page == 2
    assert page.previous_page is None

    # inner page
    page.previous = "any.url"
    page._current_page = 3
    assert page.previous_page is not None
    assert page.next_page is not None
    assert not page.is_last_page

    # last page
    page.next = None
    page._current_page = 4
    assert page.next_page is None
    assert page.is_last_page


async def test_draft_not_supported(api: PaperlessClient) -> None:
    """Test that CreatableService.create() raises when no draft_cls is configured."""

    class TestResource(PaperlessModel):
        pass

    class TestService(ResourceService, service_mixins.CreatableService):
        _api_path = "any.url"
        _resource = "test"
        _resource_cls = TestResource

    service = TestService(api)
    with pytest.raises(DraftNotSupportedError):
        service.create()


async def test_draft_rejects_unknown_fields(api: PaperlessClient) -> None:
    """Draft models forbid unknown kwargs, so typos fail at create() time."""
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        api.tags.create(tag_name="typo")  # wrong keyword for 'name'

    # valid field names still work
    draft = api.tags.create(name="valid")
    assert draft.name == "valid"


async def test_validate_assignment(api: PaperlessClient) -> None:
    """Field assignments are validated and coerced in place."""

    class AssignModel(PaperlessModel):
        id: int | None = None
        created: datetime.date | None = None
        tags: list[int] | None = None

    model = AssignModel.from_data(api.runtime, {"id": 1})

    iso_string: Any = "2024-01-15"
    model.created = iso_string  # coerced by pydantic
    assert model.created == datetime.date(2024, 1, 15)

    bad_date: Any = "not a date"
    with pytest.raises(ValidationError):
        model.created = bad_date

    bad_tags: Any = "3,7"
    with pytest.raises(ValidationError):
        model.tags = bad_tags


async def test_snapshot_lazy(api: PaperlessClient) -> None:
    """Snapshot derives from the raw API payload even when first read after a mutation."""

    class LazyModel(PaperlessModel):
        id: int | None = None
        title: str | None = None

    model = LazyModel.from_data(api.runtime, {"id": 1, "title": "before"})
    model.title = "after"
    assert model.snapshot["title"] == "before"
    # cached: repeated access returns the same dict instance
    assert model.snapshot is model.snapshot

    # direct construction without an API payload freezes the state eagerly
    direct = LazyModel(id=1, title="x")
    direct.title = "y"
    assert direct.snapshot["title"] == "x"


async def test_api_dump(api: PaperlessClient) -> None:
    """api_dump() serializes by alias, honors exclude markers and JSON-mode conversion."""

    class SubModel(BaseModel):
        name: str

    class DumpModel(PaperlessModel):
        id: int | None = None
        created: datetime.date | None = None
        sub: SubModel | None = None
        notes_: list[int] | None = Field(default=None, alias="notes", exclude=True)
        hit_: str | None = Field(default=None, alias="__hit__")

    model = DumpModel.from_data(
        api.runtime,
        {"id": 1, "created": "2024-01-15", "sub": {"name": "x"}, "notes": [1], "__hit__": "y"},
    )
    dump = model.api_dump()

    assert dump == {
        "id": 1,
        "created": "2024-01-15",
        "sub": {"name": "x"},
        "__hit__": "y",
    }
    # the snapshot uses the exact same representation
    assert model.snapshot == dump


async def test_request_merges_custom_headers(httpx_mock: HTTPXMock) -> None:
    """request_raw() lets caller-supplied headers win and never mutates the caller's dict."""
    api = PaperlessClient(PAPERLESS_TEST_URL, PAPERLESS_TEST_TOKEN)
    httpx_mock.add_response(url=PAPERLESS_TEST_URL, method="GET", status_code=200)
    transport = api._runtime.transport
    caller_headers = {"X-Custom": "value", "Accept": "application/json; version=1"}
    res = await transport.request_raw("get", PAPERLESS_TEST_URL, headers=caller_headers)
    assert res.status_code == 200

    request = httpx_mock.get_requests()[-1]
    assert request.headers["X-Custom"] == "value"
    assert request.headers["Accept"] == "application/json; version=1"
    assert request.headers["Authorization"] == f"Token {PAPERLESS_TEST_TOKEN}"
    assert caller_headers == {"X-Custom": "value", "Accept": "application/json; version=1"}
    await api.close()


async def test_request_json_400_body_not_json(httpx_mock: HTTPXMock, api: PaperlessClient) -> None:
    """get() raises BadJsonResponseError when a 400 body is not valid JSON."""
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}/400-bad-json",
        method="GET",
        status_code=400,
        headers={"Content-Type": "application/json"},
        text="not valid json {{{}}}",
    )
    with pytest.raises(BadJsonResponseError):
        await api._runtime.transport.get(f"{PAPERLESS_TEST_URL}/400-bad-json")


async def test_transport_delete_raises_deletion_error(
    httpx_mock: HTTPXMock, api: PaperlessClient
) -> None:
    """transport.delete() raises DeletionError on non-2xx status."""
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}/api/documents/42/",
        method="DELETE",
        status_code=404,
    )
    with pytest.raises(DeletionError):
        await api._runtime.transport.delete(f"{PAPERLESS_TEST_URL}/api/documents/42/")


async def test_request_json_typed_status_errors(
    httpx_mock: HTTPXMock, api: PaperlessClient
) -> None:
    """get() raises NotFoundError on 404 and UnexpectedStatusError on other non-2xx codes."""
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}/missing",
        method="GET",
        status_code=404,
        json={"detail": "Not found."},
    )
    with pytest.raises(NotFoundError):
        await api._runtime.transport.get(f"{PAPERLESS_TEST_URL}/missing")

    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}/boom",
        method="GET",
        status_code=502,
        text="Bad Gateway",
    )
    with pytest.raises(UnexpectedStatusError):
        await api._runtime.transport.get(f"{PAPERLESS_TEST_URL}/boom")


async def test_external_client_stays_open(httpx_mock: HTTPXMock) -> None:
    """close() must not close a caller-supplied httpx.AsyncClient."""
    external = httpx.AsyncClient()
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.INDEX}",
        method="GET",
        status_code=200,
        json=DATA_PATHS,
    )
    async with PaperlessClient(
        PAPERLESS_TEST_URL, PAPERLESS_TEST_TOKEN, client=external
    ) as paperless:
        assert paperless.is_initialized

    assert not external.is_closed
    await external.aclose()


async def test_owned_client_closed_on_close(httpx_mock: HTTPXMock) -> None:
    """close() closes the lazily created internal httpx client."""
    transport = PaperlessTransport(PAPERLESS_TEST_URL, PAPERLESS_TEST_TOKEN)
    httpx_mock.add_response(url=PAPERLESS_TEST_URL, method="GET", status_code=200)
    await transport.request_raw("get", PAPERLESS_TEST_URL)
    await transport.close()
    assert transport._httpx_client is not None
    assert transport._httpx_client.is_closed


async def test_service_base_api_path(api: PaperlessClient) -> None:
    """ResourceService.api_path property returns the configured _api_path."""

    class _TestService(ResourceService):
        _api_path = "/api/test/"

    svc = _TestService(api._runtime)
    assert svc.api_path == "/api/test/"


def test_process_form_data_tuple_len1() -> None:
    """process_form_data wraps a 1-tuple value as a plain BytesIO (no filename)."""
    _data, files = process_form_data({"doc": (b"raw bytes",)})
    assert len(files) == 1
    name, fobj = files[0]
    assert name == "doc"
    assert isinstance(fobj, BytesIO)
    assert fobj.read() == b"raw bytes"


# ---------------------------------------------------------------------------
# PaperlessSettings / multi-mode init tests
# ---------------------------------------------------------------------------


def test_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """PaperlessClient.from_env() reads PYPAPERLESS_URL / PYPAPERLESS_TOKEN from the environment."""
    monkeypatch.setenv("PYPAPERLESS_URL", PAPERLESS_TEST_URL)
    monkeypatch.setenv("PYPAPERLESS_TOKEN", PAPERLESS_TEST_TOKEN)
    api = PaperlessClient.from_env()
    assert api.base_url == PAPERLESS_TEST_URL
    assert api._runtime.transport._token == PAPERLESS_TEST_TOKEN


def test_config_from_env_missing_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """PaperlessClient.from_env() raises ValidationError when PYPAPERLESS_URL is not set."""
    monkeypatch.delenv("PYPAPERLESS_URL", raising=False)
    monkeypatch.delenv("PYPAPERLESS_TOKEN", raising=False)
    with pytest.raises(ValidationError):
        PaperlessClient.from_env()


def test_settings_token_is_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """The token never leaks through repr/str; from_config unwraps it for the transport."""
    # PaperlessSettings is a BaseSettings — a PYPAPERLESS_TOKEN in the developer's
    # environment would otherwise populate the deliberately anonymous config below
    monkeypatch.delenv("PYPAPERLESS_TOKEN", raising=False)

    cfg = PaperlessSettings(url=PAPERLESS_TEST_URL, token=PAPERLESS_TEST_TOKEN)
    assert PAPERLESS_TEST_TOKEN not in repr(cfg)
    assert PAPERLESS_TEST_TOKEN not in str(cfg)
    assert cfg.token is not None
    assert cfg.token.get_secret_value() == PAPERLESS_TEST_TOKEN

    api = PaperlessClient.from_config(cfg)
    assert api._runtime.transport._token == PAPERLESS_TEST_TOKEN

    # token=None still initializes an anonymous client
    cfg_anon = PaperlessSettings(url=PAPERLESS_TEST_URL)
    api_anon = PaperlessClient.from_config(cfg_anon)
    assert api_anon._runtime.transport._token is None


async def test_transport_close_without_prior_request() -> None:
    """transport.close() must be a no-op when no httpx client was ever created (L65->exit)."""
    transport = PaperlessTransport(PAPERLESS_TEST_URL, PAPERLESS_TEST_TOKEN)
    assert transport._httpx_client is None
    await transport.close()  # must not raise


async def test_request_without_token(httpx_mock: HTTPXMock) -> None:
    """_send must omit the Authorization header when token is None (L106->109)."""
    transport = PaperlessTransport(PAPERLESS_TEST_URL, token=None)
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}/api/",
        method="GET",
        status_code=200,
        json={"count": 0},
    )
    res = await transport.request_raw("get", "/api/")
    request = httpx_mock.get_requests()[-1]
    assert "Authorization" not in request.headers
    assert res.status_code == 200
    await transport.close()


def test_page_items_raises_without_resource_cls(api: PaperlessClient) -> None:
    """Page.items raises RuntimeError when no resource_cls was supplied at construction."""
    # from_data without resource_cls= → model_post_init skips L36 True-branch (L36->exit).
    page = Page.from_data(
        api._runtime,
        {"count": 1, "next": None, "previous": None, "all": [1], "results": [{"id": 1}]},
    )
    # Accessing .items triggers mapper; _resource_cls is None → L71-72.
    with pytest.raises(RuntimeError, match="resource_cls"):
        _ = page.items


async def test_page_generator_follows_next_and_prefetches(
    httpx_mock: HTTPXMock, api: PaperlessClient
) -> None:
    """PageGenerator follows the server-provided next URL across pages."""

    class PagedResource(PaperlessModel):
        id: int | None = None

    page1 = {
        "count": 3,
        "next": f"{PAPERLESS_TEST_URL}/api/things/?page=2",
        "previous": None,
        "results": [{"id": 1}, {"id": 2}],
    }
    page2 = {"count": 3, "next": None, "previous": "x", "results": [{"id": 3}]}
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}/api/things/?page=1&page_size=150", json=page1
    )
    httpx_mock.add_response(url=f"{PAPERLESS_TEST_URL}/api/things/?page=2", json=page2)

    gen = PageGenerator(api.runtime, "/api/things/", PagedResource)
    pages = [page async for page in gen]
    assert [page.current_page for page in pages] == [1, 2]
    assert pages[0].has_next_page
    assert pages[1].is_last_page
    assert pages[1].results == [{"id": 3}]


async def test_page_generator_aclose_cancels_prefetch(
    httpx_mock: HTTPXMock, api: PaperlessClient
) -> None:
    """Abandoning iteration early cancels the pending prefetch via aclose()."""

    class PagedResource(PaperlessModel):
        id: int | None = None

    page1 = {
        "count": 2,
        "next": f"{PAPERLESS_TEST_URL}/api/things/?page=2",
        "previous": None,
        "results": [{"id": 1}],
    }
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}/api/things/?page=1&page_size=150", json=page1
    )
    # the prefetch may or may not fire before the cancel wins the race
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}/api/things/?page=2",
        json={"count": 2, "next": None, "previous": "x", "results": [{"id": 2}]},
        is_optional=True,
    )

    gen = PageGenerator(api.runtime, "/api/things/", PagedResource)
    first = await anext(gen)
    assert first.current_page == 1
    await gen.aclose()
    with pytest.raises(StopAsyncIteration):
        await anext(gen)


def test_page_last_page_raises_without_pagination_context(api: PaperlessClient) -> None:
    """Page.last_page raises RuntimeError instead of ZeroDivisionError when page_size is 0."""
    page = Page.from_data(
        api._runtime,
        {"count": 42, "next": "http://x/?page=2", "previous": None, "results": [{"id": 1}]},
    )
    with pytest.raises(RuntimeError, match="pagination context"):
        _ = page.last_page
