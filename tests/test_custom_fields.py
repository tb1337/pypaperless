"""Tests for custom field value types and the CustomFieldQuery DSL builder."""

import json
import operator as _op
import re
from datetime import date
from typing import Any

import pytest
from pytest_httpx import HTTPXMock

from pypaperless import PaperlessClient
from pypaperless.builders.custom_fields import (
    CustomFieldQuery,
    _CustomFieldQueryAnd,
    _CustomFieldQueryNot,
    _CustomFieldQueryOr,
)
from pypaperless.const import EndpointPath
from pypaperless.models import CustomField
from pypaperless.models.types import (
    CustomFieldBooleanValue,
    CustomFieldDateValue,
    CustomFieldExtraData,
    CustomFieldIntegerValue,
    CustomFieldMonetaryValue,
    CustomFieldSelectValue,
    CustomFieldType,
    CustomFieldValue,
)

from .const import PAPERLESS_TEST_URL
from .data import DATA_CUSTOM_FIELDS


async def test_draft_value_without_cache(paperless: PaperlessClient) -> None:
    """draft_value() returns a plain object when the custom field cache is empty."""
    custom_field = CustomField.from_data(
        paperless.runtime,
        data={"id": 1337, "name": "Test", "data_type": CustomFieldType.INTEGER},
    )
    field_value = custom_field.draft_value(1337)
    assert type(field_value) is CustomFieldValue
    assert field_value.field == custom_field.id
    assert field_value.value == 1337


async def test_draft_value_with_cache(httpx_mock: HTTPXMock, paperless: PaperlessClient) -> None:
    """draft_value() returns a typed value when the custom field cache is populated."""
    httpx_mock.add_response(
        url=re.compile(
            r"^" + re.escape(f"{PAPERLESS_TEST_URL}{EndpointPath.CUSTOM_FIELDS}") + r"\?.*$"
        ),
        method="GET",
        status_code=200,
        json=DATA_CUSTOM_FIELDS,
    )
    paperless.runtime.cache.custom_fields = await paperless.custom_fields.as_dict()

    custom_field = CustomField.from_data(
        runtime=paperless.runtime,
        data=DATA_CUSTOM_FIELDS["results"][5],
    )
    field_value = custom_field.draft_value(1337, expected_type=CustomFieldIntegerValue)
    assert field_value.field == custom_field.id
    assert field_value.value == 1337


@pytest.mark.parametrize(
    "value_str",
    ["1900-01-02", "1900-01-02T03:04:05.133337Z"],
    ids=["date_string", "datetime_string"],
)
def test_date_value_parses_to_date(value_str: str) -> None:
    """CustomFieldDateValue accepts both ISO date strings and datetime strings, returning a date."""
    assert CustomFieldDateValue(value=value_str).value == date(1900, 1, 2)


def test_monetary_value_parsing() -> None:
    """CustomFieldMonetaryValue correctly parses and formats currency/amount."""
    field = CustomFieldMonetaryValue(value=None)
    assert field.value is None

    field = CustomFieldMonetaryValue(value="EUR1337.00")
    assert field.currency == "EUR"
    assert field.amount == 1337

    field.amount = 123.45678
    assert field.amount == 123.46  # rounded to cents

    field.extra_data = CustomFieldExtraData(default_currency="USD")
    assert field.value == "EUR123.46"

    field.value = "123.45"  # no explicit currency
    assert field.currency == "USD"  # falls back to default

    field.extra_data = CustomFieldExtraData()
    assert field.currency == ""

    field.currency = "EUR"
    assert field.value == "EUR123.45"

    field.currency = ""
    assert field.value == "123.45"

    field.value = None
    assert field.amount is None


def test_select_value_labels() -> None:
    """CustomFieldSelectValue resolves labels from select_options; returns None for missing data."""
    test = CustomFieldSelectValue(
        value="id2",
        extra_data={
            "select_options": [
                {"id": "id1", "label": "label1"},
                {"id": "id2", "label": "label2"},
            ]
        },
    )
    assert [option.label for option in test.labels] == ["label1", "label2"]
    assert test.label == "label2"
    test.extra_data = None
    assert test.label is None


@pytest.mark.parametrize(
    ("field", "op", "value", "expected"),
    [
        ("Status", "exact", "open", ["Status", "exact", "open"]),
        ("Amount", "gte", 100, ["Amount", "gte", 100]),
        (42, "exists", True, [42, "exists", True]),
    ],
    ids=["str_field_str_value", "str_field_int_value", "int_field"],
)
def test_atom(field: Any, op: Any, value: Any, expected: Any) -> None:
    """Atom builds and serialises to the expected 3-element list for all field/value types."""
    q = CustomFieldQuery(field, op, value)
    assert q.build() == expected
    assert json.loads(str(q)) == expected


@pytest.mark.parametrize(
    ("combine", "expected_cls", "expected_tag", "expected_operands"),
    [
        (_op.and_, _CustomFieldQueryAnd, "AND", [["A", "exact", 1], ["B", "exact", 2]]),
        (_op.or_, _CustomFieldQueryOr, "OR", [["A", "exact", 1], ["B", "exact", 2]]),
    ],
    ids=["AND", "OR"],
)
def test_binary_operator(
    combine: Any, expected_cls: Any, expected_tag: Any, expected_operands: Any
) -> None:
    """& and | each produce the correct compound node with both operands."""
    q1 = CustomFieldQuery("A", "exact", 1)
    q2 = CustomFieldQuery("B", "exact", 2)
    combined = combine(q1, q2)
    assert isinstance(combined, expected_cls)
    assert combined.build() == [expected_tag, expected_operands]


@pytest.mark.parametrize(
    ("combine", "expected_cls", "expected_tag"),
    [
        (_op.and_, _CustomFieldQueryAnd, "AND"),
        (_op.or_, _CustomFieldQueryOr, "OR"),
    ],
    ids=["AND", "OR"],
)
def test_binary_operator_flattens(combine: Any, expected_cls: Any, expected_tag: Any) -> None:
    """Chaining the same operator three times flattens into a single node."""
    q1 = CustomFieldQuery("X", "exact", 1)
    q2 = CustomFieldQuery("X", "exact", 2)
    q3 = CustomFieldQuery("X", "exact", 3)
    combined = combine(combine(q1, q2), q3)
    assert isinstance(combined, expected_cls)
    result = combined.build()
    assert result[0] == expected_tag
    assert len(result[1]) == 3


def test_not_operator() -> None:
    """~ produces a _CustomFieldQueryNot wrapping the operand."""
    q = CustomFieldQuery("Archived", "exact", value=True)
    negated = ~q
    assert isinstance(negated, _CustomFieldQueryNot)
    assert negated.build() == ["NOT", ["Archived", "exact", True]]


def test_combined_expression() -> None:
    """Complex expression (AND + NOT) builds the correct nested structure."""
    q = CustomFieldQuery("Status", "exact", "open") & ~CustomFieldQuery(
        "Archived", "exact", value=True
    )
    result = q.build()
    assert result[0] == "AND"
    assert result[1][1] == ["NOT", ["Archived", "exact", True]]


def test_str_is_valid_json() -> None:
    """str() on any expression always produces valid JSON."""
    q = CustomFieldQuery("A", "gte", 0) | CustomFieldQuery("B", "icontains", "foo")
    parsed = json.loads(str(q))
    assert parsed[0] == "OR"


def test_repr() -> None:
    """repr() returns a human-readable string with the class name and serialised expression."""
    q = CustomFieldQuery("Status", "exact", "open")
    r = repr(q)
    assert r.startswith("CustomFieldQuery(")
    assert "Status" in r


def test_date_value_accepts_date_object() -> None:
    """CustomFieldDateValue passes through a value that is already a date object."""
    d = date(2024, 1, 15)
    field = CustomFieldDateValue(value=d)
    assert field.value == d


def test_draft_value_raises_for_wrong_expected_type(api: PaperlessClient) -> None:
    """draft_value() must raise TypeError when the result type mismatches expected_type."""
    # Build a CustomField with no cache so draft_value returns a plain CustomFieldValue.
    cf = CustomField.from_data(api._runtime, {"id": 99, "name": "test", "data_type": "integer"})
    # Without cache the result is CustomFieldValue, not CustomFieldBooleanValue.
    with pytest.raises(TypeError, match="Expected CustomFieldBooleanValue"):
        cf.draft_value(42, CustomFieldBooleanValue)

    # Passing expected_type=None must not raise (the guard is skipped).
    result = cf.draft_value(42)
    assert type(result) is CustomFieldValue
    assert result.field == 99
    assert result.value == 42
