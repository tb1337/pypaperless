"""Self-checks for the snapshot fixtures in tests/data."""

from typing import Any

import pytest

import tests.data as fixture_data


def _paginated_fixtures() -> list[tuple[str, dict[str, Any]]]:
    """Return every ``(name, payload)`` fixture shaped like a DRF paginated response."""
    return [
        (name, obj)
        for name in sorted(fixture_data.__all__)
        if isinstance(obj := getattr(fixture_data, name), dict)
        and {"count", "results"} <= obj.keys()
    ]


def test_paginated_fixtures_discovered() -> None:
    """The discovery must actually find fixtures, otherwise the check below is vacuous."""
    assert len(_paginated_fixtures()) >= 15


@pytest.mark.parametrize(
    ("name", "payload"), _paginated_fixtures(), ids=[name for name, _ in _paginated_fixtures()]
)
def test_paginated_fixture_count_matches_results(name: str, payload: dict[str, Any]) -> None:
    """A single-page fixture must report a count equal to the number of results it carries.

    Tests assert item counts against ``len(results)``; a fixture whose ``count`` disagrees
    would make ``Page.last_page`` claim pages that the fixture cannot serve.
    """
    assert payload["next"] is None, f"{name} is not a single-page fixture"
    assert payload["count"] == len(payload["results"])
