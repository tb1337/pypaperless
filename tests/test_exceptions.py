"""Tests for exception classes: formatting."""

import re

import pytest

from pypaperless.exceptions import (
    JsonResponseWithError,
)


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        (
            "sample string",
            "Paperless [error]: sample string",
        ),
        (
            {"failure": "something failed"},
            "Paperless [failure]: something failed",
        ),
        (
            {"error": ["that", "should", "have", "been", "never", "happened"]},
            "Paperless [error]: that",
        ),
        (
            [{"some": [[{"weird": {"error": ["occurred"]}}]]}],
            "Paperless [some -> weird -> error]: occurred",
        ),
        (
            {},
            "Paperless [error]: unknown error",
        ),
        (
            [],
            "Paperless [error]: unknown error",
        ),
        (
            {"detail": []},
            "Paperless [detail]: unknown error",
        ),
        # "error" wins over the plain first-key branch even when it is not first
        (
            {"detail": "ignored", "error": "the real one"},
            "Paperless [error]: the real one",
        ),
        # …and the generic branch picks the first key when no "error" is present
        (
            {"detail": "the real one", "warning": "ignored"},
            "Paperless [detail]: the real one",
        ),
    ],
    ids=[
        "plain_string",
        "single_key_dict",
        "error_key_list_value",
        "deeply_nested",
        "empty_dict",
        "empty_list",
        "empty_nested_value",
        "error_key_takes_priority",
        "first_key_without_error",
    ],
)
def test_json_response_with_error_formatting(payload: object, expected_message: str) -> None:
    """JsonResponseWithError must format its message correctly for every payload shape."""
    with pytest.raises(JsonResponseWithError, match=rf"^{re.escape(expected_message)}$"):
        raise JsonResponseWithError(payload)


def test_json_response_with_error_does_not_mutate_payload() -> None:
    """JsonResponseWithError must not consume list entries while parsing the payload."""
    payload = [{"some": ["deep", "error"]}]
    with pytest.raises(JsonResponseWithError):
        raise JsonResponseWithError(payload)
    assert payload == [{"some": ["deep", "error"]}]
