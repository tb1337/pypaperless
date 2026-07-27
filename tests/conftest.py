"""Setup pytest."""

from collections.abc import AsyncGenerator
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from pypaperless import PaperlessClient
from pypaperless.const import EndpointPath

from .const import (
    PAPERLESS_TEST_API_VERSION,
    PAPERLESS_TEST_TOKEN,
    PAPERLESS_TEST_URL,
    PAPERLESS_TEST_VERSION,
)
from .data import DATA_SCHEMA


@pytest.fixture(name="api")
def api_obj_fixture() -> PaperlessClient:
    """Return PaperlessClient."""
    return PaperlessClient(
        PAPERLESS_TEST_URL,
        PAPERLESS_TEST_TOKEN,
    )


@pytest.fixture(name="paperless")
async def paperless_fixture(
    httpx_mock: HTTPXMock,
    api: PaperlessClient,
) -> AsyncGenerator[PaperlessClient, Any]:
    """Return a PaperlessClient object with given version."""
    httpx_mock.add_response(
        url=f"{PAPERLESS_TEST_URL}{EndpointPath.INDEX}",
        method="GET",
        status_code=200,
        json=DATA_SCHEMA,
        headers={
            "x-api-version": str(PAPERLESS_TEST_API_VERSION),
            "x-version": PAPERLESS_TEST_VERSION,
        },
    )
    async with api:
        yield api
