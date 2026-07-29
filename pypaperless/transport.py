"""Provide the HTTP transport layer for PyPaperless."""

from json import JSONDecodeError
from typing import Any, NamedTuple

import httpx

from .const import API_VERSION, EndpointPath
from .exceptions import (
    BadJsonResponseError,
    DeletionError,
    ForbiddenError,
    InactiveOrDeletedError,
    InvalidTokenError,
    JsonResponseWithError,
    NotFoundError,
    PaperlessConnectionError,
    PaperlessTimeoutError,
    UnexpectedStatusError,
)
from .utils import normalize_base_url, process_form_data


class _HostInfo(NamedTuple):
    """Version metadata returned by :meth:`PaperlessTransport.probe`."""

    api_version: int
    version: str | None


class PaperlessTransport:
    """Handle all HTTP communication with a Paperless-ngx instance.

    Constructed by :class:`~pypaperless.client.PaperlessClient` and passed to
    :class:`~pypaperless.runtime.PaperlessRuntime`.  Not intended for direct
    instantiation by library consumers.

    Args:
        base_url: Hostname, IP-address, or full URL string.
        token:    API token, or ``None`` for anonymous access.
        client:   Optional :class:`httpx.AsyncClient` to reuse.

    Example::

        transport = PaperlessTransport("localhost:8000", "mytoken")
        data = await transport.get("/api/documents/")

    """

    def __init__(
        self,
        base_url: str,
        token: str | None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize a :class:`PaperlessTransport` instance."""
        self._base_url = normalize_base_url(base_url)
        self._token = token
        self._httpx_client = client
        self._owns_client = client is None

    @property
    def base_url(self) -> str:
        """Return the base URL of the Paperless API endpoint."""
        return self._base_url

    async def close(self) -> None:
        """Close the :class:`httpx.AsyncClient` if this transport created it.

        A client passed in by the caller is left open — its lifecycle belongs
        to the caller.
        """
        if self._owns_client and self._httpx_client:
            await self._httpx_client.aclose()

    async def probe(self) -> "_HostInfo":
        """Request the API index and return parsed host version info.

        Validates that the response is reachable, returns HTTP 2xx, and
        contains a JSON-parseable body.  Raises on any failure — the caller
        is responsible for wrapping exceptions.

        Example::

            info = await transport.probe()
            print(info.api_version, info.version)

        """
        res = await self.request_raw("get", EndpointPath.INDEX)
        res.raise_for_status()
        res.json()
        return _HostInfo(
            api_version=int(res.headers.get("x-api-version", API_VERSION)),
            version=res.headers.get("x-version"),
        )

    async def _send(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        form: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send an authenticated HTTP request; handle auth, transport errors, and 401/403."""
        if self._httpx_client is None:
            self._httpx_client = httpx.AsyncClient()

        headers: dict[str, str] = {
            "Accept": f"application/json; version={API_VERSION}",
        }
        if self._token:
            headers["Authorization"] = f"Token {self._token}"

        # caller-supplied headers win over the defaults; never mutate the caller's dict
        kwargs["headers"] = {**headers, **kwargs.get("headers", {})}

        files = None
        if isinstance(form, dict):
            data, files = process_form_data(form)

        url = f"{self._base_url}{path}" if not path.startswith("http") else path

        try:
            res = await self._httpx_client.request(
                method=method.upper(),
                url=url,
                json=json,
                data=data,
                files=files,
                params=params,
                **kwargs,
            )
        except httpx.TimeoutException as err:
            raise PaperlessTimeoutError from err
        except httpx.TransportError as err:
            raise PaperlessConnectionError from err

        if res.status_code == 401:
            try:
                error_data = res.json()
                detail = error_data.get("detail", "")
            except ValueError:
                detail = ""

            if "inactive" in detail.lower() or "deleted" in detail.lower():
                raise InactiveOrDeletedError(res)

            raise InvalidTokenError(res)

        if res.status_code == 403:
            raise ForbiddenError(res)

        return res

    @staticmethod
    def raise_for_status(res: httpx.Response) -> None:
        """Raise a typed pypaperless exception for any non-2xx response.

        Raises :exc:`~pypaperless.exceptions.NotFoundError` for HTTP 404 and
        :exc:`~pypaperless.exceptions.UnexpectedStatusError` for any other
        non-2xx status code.  Responses with a 2xx status pass silently.

        Args:
            res: The :class:`httpx.Response` to check.

        Example::

            res = await transport.request_raw("get", "/api/documents/42/download/")
            transport.raise_for_status(res)

        """
        if res.status_code == 404:
            raise NotFoundError(res)
        try:
            res.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise UnexpectedStatusError(res) from exc

    def _parse_json(self, res: httpx.Response) -> Any:
        """Parse a JSON response; raise on non-JSON, bad JSON, HTTP 400, or other errors."""
        if "application/json" not in res.headers.get("content-type", ""):
            self.raise_for_status(res)
            raise BadJsonResponseError(res)

        try:
            payload = res.json()
        except (ValueError, JSONDecodeError):
            raise BadJsonResponseError(res) from None

        if res.status_code == 400:
            raise JsonResponseWithError(payload)

        self.raise_for_status(res)
        return payload

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a GET request and return the parsed JSON response.

        Args:
            path:   API path relative to the base URL, or an absolute URL.
            params: Optional query string parameters.
            **kwargs: Forwarded to :meth:`_send`.

        Example::

            data = await transport.get("/api/documents/", params={"page": 1})

        """
        return self._parse_json(await self._send("get", path, params=params, **kwargs))

    async def post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        form: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a POST request and return the parsed JSON response.

        Args:
            path:   API path relative to the base URL, or an absolute URL.
            json:   Dict to send as JSON request body.
            data:   Dict to send as form-encoded body.
            form:   Dict converted to multipart form data.
            params: Optional query string parameters.
            **kwargs: Forwarded to :meth:`_send`.

        Example::

            data = await transport.post("/api/documents/", json={"title": "My Doc"})

        """
        return self._parse_json(
            await self._send("post", path, json=json, data=data, form=form, params=params, **kwargs)
        )

    async def patch(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a PATCH request and return the parsed JSON response.

        Args:
            path:   API path relative to the base URL, or an absolute URL.
            json:   Dict to send as JSON request body.
            params: Optional query string parameters.
            **kwargs: Forwarded to :meth:`_send`.

        Example::

            data = await transport.patch("/api/documents/42/", json={"title": "Updated"})

        """
        return self._parse_json(await self._send("patch", path, json=json, params=params, **kwargs))

    async def put(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Send a PUT request and return the parsed JSON response.

        Args:
            path:   API path relative to the base URL, or an absolute URL.
            json:   Dict to send as JSON request body.
            params: Optional query string parameters.
            **kwargs: Forwarded to :meth:`_send`.

        Example::

            data = await transport.put("/api/documents/42/", json={"title": "Replaced"})

        """
        return self._parse_json(await self._send("put", path, json=json, params=params, **kwargs))

    async def delete(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Send a DELETE request and raise on any non-2xx response.

        Args:
            path:   API path relative to the base URL, or an absolute URL.
            params: Optional query string parameters.
            **kwargs: Forwarded to :meth:`_send`.

        Example::

            await transport.delete("/api/documents/42/")

        """
        res = await self._send("delete", path, params=params, **kwargs)
        try:
            res.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise DeletionError(str(exc)) from exc

    async def request_raw(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send a request and return the raw :class:`httpx.Response`.

        Use for binary downloads, header-only checks, or other cases where
        the caller needs access to the full response object.

        Args:
            method: HTTP method string.
            path:   API path relative to the base URL, or an absolute URL.
            **kwargs: Forwarded to :meth:`_send`.

        Example::

            res = await transport.request_raw("get", "/api/documents/42/download/")
            content = res.content

        """
        return await self._send(method, path, **kwargs)


async def generate_api_token(
    url: str,
    username: str,
    password: str,
    client: httpx.AsyncClient | None = None,
) -> str:
    """Request Paperless to generate an API token for the given credentials.

    .. warning::

        The credentials are transmitted in the request body.  Make sure the
        URL points to an HTTPS endpoint when used on untrusted networks.

    Args:
        url:      Hostname, IP-address, or full URL of the Paperless instance.
                  Scheme-less values default to ``https://``.
        username: Paperless user name.
        password: Paperless user password.
        client:   Optional :class:`httpx.AsyncClient` to reuse.  A new client
                  is created and closed automatically when not provided.

    Example::

        token = await generate_api_token("example.com:8000", "api_user", "secret")
        async with PaperlessClient("example.com:8000", token) as paperless:
            ...

    """
    external_client = client is not None
    client = client or httpx.AsyncClient()
    try:
        url = normalize_base_url(url)
        json_data = {
            "username": username,
            "password": password,
        }
        res = await client.post(f"{url}{EndpointPath.TOKEN}", json=json_data)
        data = res.json()
        res.raise_for_status()
        return str(data["token"])
    except httpx.TimeoutException as exc:
        raise PaperlessTimeoutError from exc
    except httpx.TransportError as exc:
        raise PaperlessConnectionError from exc
    except (JSONDecodeError, KeyError) as exc:
        message = "Token is missing in response."
        raise BadJsonResponseError(message) from exc
    except httpx.HTTPStatusError as exc:
        raise JsonResponseWithError(payload={"error": data}) from exc
    finally:
        if not external_client:
            await client.aclose()
