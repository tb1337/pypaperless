"""PyPaperless exceptions."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import httpx


class PaperlessError(Exception):
    """Base exception for PyPaperless."""


# Session / transport


class InitializationError(PaperlessError):
    """Raised when initializing a `Paperless` instance without valid url or token."""


class PaperlessConnectionError(InitializationError):
    """Raised when connection to Paperless is not possible."""


class PaperlessTimeoutError(PaperlessConnectionError):
    """Raised when a request to Paperless times out.

    The host is reachable but did not respond in time — retrying, or using a
    custom :class:`httpx.AsyncClient` with a higher timeout, may help.
    """


class AuthError(InitializationError):
    """Raised when response is 401 code."""


class InvalidTokenError(AuthError):
    """Raised when response is 401 due invalid access token."""


class InactiveOrDeletedError(AuthError):
    """Raised when response is 401 code due user is inactive or deleted."""


class ForbiddenError(InitializationError):
    """Raised when response is 403 code."""


# Response parsing


class ResponseError(PaperlessError):
    """Raised when the API returns an unexpected or error response."""


class BadJsonResponseError(ResponseError):
    """Raised when response is no valid json."""


class JsonResponseWithError(ResponseError):
    """Raised when Paperless accepted the request, but responded with an error payload."""

    def __init__(self, payload: Any) -> None:
        """Initialize a `JsonResponseWithError` instance."""

        def _parse_payload(payload: Any, key: list[str] | None = None) -> tuple[list[str], str]:
            """Parse first suitable error from payload without mutating it."""
            if key is None:
                key = []

            if isinstance(payload, list) and payload:
                return _parse_payload(payload[0], key)
            if isinstance(payload, dict) and payload:
                if "error" in payload:
                    key.append("error")
                    return _parse_payload(payload["error"], key)

                new_key = next(iter(payload))
                key.append(new_key)

                return _parse_payload(payload[new_key], key)
            if isinstance(payload, list | dict):
                return key, "unknown error"

            return key, payload

        key, message = _parse_payload(payload)

        if not key:
            key.append("error")
        key_chain = " -> ".join(key)

        super().__init__(f"Paperless [{key_chain}]: {message}")


class NotFoundError(ResponseError):
    """Raised when the requested resource does not exist (HTTP 404)."""

    def __init__(self, response: "httpx.Response") -> None:
        """Initialize a `NotFoundError` instance."""
        self.response = response
        super().__init__(f"Requested resource does not exist: {response.request.url}")


class UnexpectedStatusError(ResponseError):
    """Raised when Paperless responds with an unhandled non-2xx status code."""

    def __init__(self, response: "httpx.Response") -> None:
        """Initialize an `UnexpectedStatusError` instance."""
        self.response = response
        super().__init__(
            f"Paperless responded with HTTP {response.status_code} ({response.reason_phrase})."
        )


class BulkEditError(ResponseError):
    """Raised when a bulk edit operation returned a non-OK result."""

    def __init__(self, result: str) -> None:
        """Initialize a `BulkEditError` instance."""
        super().__init__(f"Bulk edit operation returned a non-OK result: {result!r}")


# Draft lifecycle


class DraftError(PaperlessError):
    """Raised when a draft lifecycle operation fails."""


class DraftFieldRequiredError(DraftError):
    """Raised when trying to save models with missing required fields."""


class DraftNotSupportedError(DraftError):
    """Raised when trying to draft unsupported models."""


# Dispatch


class DispatchError(PaperlessError):
    """Raised when a model dispatch operation cannot be completed."""


# Resource access


class ResourceError(PaperlessError):
    """Raised when a resource access or lookup operation fails."""


class DeletionError(ResourceError):
    """Raised when a delete operation fails (non-2xx HTTP response)."""


class ItemNotFoundError(ResourceError):
    """Raised when trying to access non-existing items in DocumentCustomFieldList classes."""


class PrimaryKeyRequiredError(ResourceError):
    """Raised when trying to access model data without supplying a pk."""


class TaskNotFoundError(ResourceError):
    """Raised when trying to access a task by non-existing uuid."""

    def __init__(self, task_id: str) -> None:
        """Initialize a `TaskNotFound` instance."""
        super().__init__(f"Task with UUID {task_id} not found.")


# Document operations


class DocumentError(PaperlessError):
    """Raised when a document-specific service operation fails."""


class AsnRequestError(DocumentError):
    """Raised when getting an error during requesting the next asn."""


class SendEmailError(DocumentError):
    """Raised when sending email for a document fails."""


class BulkEditPagesError(DocumentError, ValueError):
    """Raised when a page selection for a PDF page operation cannot be applied.

    Also a :class:`ValueError`, so callers may catch either that or
    :class:`PaperlessError`.
    """
