"""Tests for enum types: UNKNOWN fallback values."""

import importlib
import inspect
import pkgutil
from enum import Enum

import pytest
from pydantic import TypeAdapter, ValidationError

import pypaperless
from pypaperless.models.saved_views import _DisplayFieldValue
from pypaperless.models.types import (
    SavedViewCustomFieldDisplay,
    SavedViewDisplayField,
)

_NEVER_STR = "!never_existing_type!"
_NEVER_INT = 99952342


def _unknown_fallback_enums() -> list[type[Enum]]:
    """Collect every library enum that maps unrecognised values onto UNKNOWN.

    Discovered rather than hand-listed so a new enum cannot slip past this test.
    """
    found: dict[str, type[Enum]] = {}
    for module_info in pkgutil.walk_packages(pypaperless.__path__, f"{pypaperless.__name__}."):
        module = importlib.import_module(module_info.name)
        for obj in vars(module).values():
            if (
                inspect.isclass(obj)
                and issubclass(obj, Enum)
                and obj.__module__.startswith(pypaperless.__name__)
                and "UNKNOWN" in obj.__members__
                and "_missing_" in obj.__dict__
            ):
                found[f"{obj.__module__}.{obj.__qualname__}"] = obj
    return [found[key] for key in sorted(found)]


def test_unknown_fallback_enum_discovery() -> None:
    """The discovery helper must find enums across all model subpackages."""
    names = {enum_cls.__name__ for enum_cls in _unknown_fallback_enums()}
    assert {
        "ImapSecurity",
        "OcrMode",
        "PaperlessResource",
        "ShareLinkBundleStatus",
        "TaskTriggerSource",
        "WorkflowTriggerType",
    } <= names


@pytest.mark.parametrize(
    "enum_cls",
    _unknown_fallback_enums(),
    ids=lambda enum_cls: enum_cls.__name__,
)
@pytest.mark.parametrize("bad_value", [_NEVER_STR, _NEVER_INT], ids=["str", "int"])
def test_enum_unknown_fallback(enum_cls: type[Enum], bad_value: object) -> None:
    """Every custom enum must return UNKNOWN for unrecognised values instead of raising."""
    assert enum_cls(bad_value) == enum_cls.UNKNOWN


@pytest.mark.parametrize(
    ("raw", "expected_pk"),
    [
        ("custom_field_1", 1),
        ("custom_field_8", 8),
        ("custom_field_100", 100),
    ],
    ids=["pk_1", "pk_8", "pk_100"],
)
def test_saved_view_custom_field_display_valid(raw: str, expected_pk: int) -> None:
    """SavedViewCustomFieldDisplay accepts valid custom_field_<pk> strings and exposes the PK."""
    obj = SavedViewCustomFieldDisplay(raw)
    assert obj == raw
    assert isinstance(obj, str)
    assert obj.pk == expected_pk


@pytest.mark.parametrize(
    "bad",
    ["custom_field_", "custom_field_foo", "title", "", "custom_field_1_extra"],
    ids=["no_digits", "alpha_pk", "known_field", "empty", "trailing_garbage"],
)
def test_saved_view_custom_field_display_invalid(bad: str) -> None:
    """SavedViewCustomFieldDisplay raises ValueError for strings that are not custom_field_<pk>."""
    with pytest.raises(ValueError, match="Not a custom field display value"):
        SavedViewCustomFieldDisplay(bad)


_ta: TypeAdapter[SavedViewDisplayField | SavedViewCustomFieldDisplay] = TypeAdapter(
    _DisplayFieldValue
)


@pytest.mark.parametrize(
    ("raw", "expected_type", "expected_value"),
    [
        ("title", SavedViewDisplayField, SavedViewDisplayField.TITLE),
        ("created", SavedViewDisplayField, SavedViewDisplayField.CREATED),
        ("correspondent", SavedViewDisplayField, SavedViewDisplayField.CORRESPONDENT),
        ("custom_field_1", SavedViewCustomFieldDisplay, "custom_field_1"),
        ("custom_field_8", SavedViewCustomFieldDisplay, "custom_field_8"),
    ],
    ids=["title", "created", "correspondent", "cf_1", "cf_8"],
)
def test_display_field_value_coercion(
    raw: str, expected_type: type, expected_value: object
) -> None:
    """SavedViewDisplayField coerces strings to DisplayField or CustomFieldDisplay."""
    result = _ta.validate_python(raw)
    assert isinstance(result, expected_type)
    assert result == expected_value


def test_display_field_value_invalid() -> None:
    """SavedViewDisplayField raises ValidationError for unrecognised strings."""
    with pytest.raises(ValidationError):
        _ta.validate_python("unknown_field_xyz")


def test_display_field_value_passthrough_enum() -> None:
    """SavedViewDisplayField accepts an already-coerced DisplayField without re-wrapping."""
    result = _ta.validate_python(SavedViewDisplayField.TITLE)
    assert result is SavedViewDisplayField.TITLE


def test_display_field_value_passthrough_custom() -> None:
    """SavedViewCustomFieldDisplay accepts an already-coerced custom field without re-wrapping."""
    cfd = SavedViewCustomFieldDisplay("custom_field_42")
    result = _ta.validate_python(cfd)
    assert result is cfd


def test_display_field_value_serialises_to_str() -> None:
    """SavedViewCustomFieldDisplay round-trips through JSON as a plain string."""
    result = _ta.validate_python("custom_field_8")
    assert _ta.dump_json(result) == b'"custom_field_8"'


def test_display_field_value_non_string_raises() -> None:
    """SavedViewDisplayField raises ValidationError for non-string inputs."""
    with pytest.raises(ValidationError):
        _ta.validate_python(42)
