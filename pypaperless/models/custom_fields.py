"""Provide `CustomField` related models."""

import contextlib
import datetime as dt
import re
from enum import StrEnum
from typing import Annotated, Any, ClassVar, Literal, Self, TypeVar, overload

from pydantic import BaseModel, Field, TypeAdapter, field_validator

from pypaperless.const import EndpointPath, PaperlessResource

from . import mixins
from .base import IdentifiedModel, PaperlessModel


class CustomFieldSelectOptions(BaseModel):
    """Represent the `extra_data.select_options` field of a `CustomField`."""

    id: str | None = None
    label: str | None = None


class CustomFieldExtraData(BaseModel):
    """Represent the `extra_data` field of a `CustomField`."""

    default_currency: str | None = None
    select_options: list[CustomFieldSelectOptions | None] = Field(default_factory=list)


class CustomFieldType(StrEnum):
    """Represent a subtype of `CustomField`."""

    STRING = "string"
    URL = "url"
    DATE = "date"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    MONETARY = "monetary"
    DOCUMENT_LINK = "documentlink"
    SELECT = "select"
    LONGTEXT = "longtext"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, *_: object) -> Self:
        """Return the UNKNOWN member for any unrecognised value."""
        return cls["UNKNOWN"]


class CustomFieldValue(BaseModel):
    """Represent a subtype of `CustomField`.

    ``name``, ``data_type``, and ``extra_data`` are enriched client-side from
    the custom-fields cache and excluded from serialization - the API only
    accepts ``field`` and ``value``.
    """

    field: int | None = None
    value: Any | None = None
    name: str | None = Field(default=None, exclude=True)
    data_type: CustomFieldType | None = Field(default=None, exclude=True)
    extra_data: CustomFieldExtraData | None = Field(default=None, exclude=True)


CustomFieldValueT = TypeVar("CustomFieldValueT", bound=CustomFieldValue)


class CustomFieldBooleanValue(CustomFieldValue):
    """Represent a boolean `CustomFieldValue`."""

    value: bool | None = None
    data_type: Literal[CustomFieldType.BOOLEAN] = Field(
        default=CustomFieldType.BOOLEAN, exclude=True
    )


class CustomFieldDateValue(CustomFieldValue):
    """Represent a date `CustomFieldValue`."""

    value: dt.date | str | None = None
    data_type: Literal[CustomFieldType.DATE] = Field(default=CustomFieldType.DATE, exclude=True)

    @field_validator("value", mode="before")
    @classmethod
    def _parse_date(cls, v: dt.date | str | None) -> dt.date | str | None:
        """Convert the value to a date."""
        if isinstance(v, str):
            with contextlib.suppress(ValueError):
                return dt.datetime.fromisoformat(v).date()
        return v


class CustomFieldDocumentLinkValue(CustomFieldValue):
    """Represent a document link `CustomFieldValue`."""

    value: list[int] | int | None = None
    data_type: Literal[CustomFieldType.DOCUMENT_LINK] = Field(
        default=CustomFieldType.DOCUMENT_LINK, exclude=True
    )


class CustomFieldFloatValue(CustomFieldValue):
    """Represent a float `CustomFieldValue`."""

    value: float | None = None
    data_type: Literal[CustomFieldType.FLOAT] = Field(default=CustomFieldType.FLOAT, exclude=True)


class CustomFieldIntegerValue(CustomFieldValue):
    """Represent an integer `CustomFieldValue`."""

    value: int | None = None
    data_type: Literal[CustomFieldType.INTEGER] = Field(
        default=CustomFieldType.INTEGER, exclude=True
    )


class CustomFieldMonetaryValue(CustomFieldValue):
    """Represent a monetary `CustomFieldValue`."""

    value: str | None = None
    data_type: Literal[CustomFieldType.MONETARY] = Field(
        default=CustomFieldType.MONETARY, exclude=True
    )

    @field_validator("value", mode="before")
    @classmethod
    def _coerce_value_to_str(cls, v: Any) -> str | None:
        """Coerce a non-string monetary value to a string."""
        if v is None:
            return None
        return str(v)

    @property
    def currency(self) -> str | None:
        """Return the currency of the `value` field."""
        if self.value and (match := re.match(r"^([a-zA-Z]{3})", self.value)):
            return match.group(1)
        if self.extra_data and self.extra_data.default_currency:
            return self.extra_data.default_currency
        return ""

    @currency.setter
    def currency(self, new_currency: str) -> None:
        """Override the currency of the field."""
        value = self.value or ""
        value = re.sub(r"^[a-zA-Z]{3}", "", value)

        if new_currency and re.match(r"^[A-Z]{3}$", new_currency):
            self.value = f"{new_currency}{value}"
        else:
            self.value = value

    @property
    def amount(self) -> float | None:
        """Return the amount without currentcy of the `value` field."""
        if self.value:
            numeric = re.sub(r"[^\d.]", "", self.value)
            return float(numeric)
        return None

    @amount.setter
    def amount(self, new_amount: float) -> None:
        """Set a new amount and construct the internal needed value."""
        self.value = f"{self.currency}{new_amount:.2f}"


class CustomFieldSelectValue(CustomFieldValue):
    """Represent a select `CustomFieldValue`."""

    value: int | str | None = None
    data_type: Literal[CustomFieldType.SELECT] = Field(default=CustomFieldType.SELECT, exclude=True)

    @property
    def labels(self) -> list[CustomFieldSelectOptions | None]:
        """Return the list of labels of the `CustomField`."""
        if not self.extra_data:
            return []
        return self.extra_data.select_options

    @property
    def label(self) -> str | None:
        """Return the label for `value` or fall back to `None`."""
        for opt in self.labels:
            if opt and opt.id == self.value:
                return opt.label
        return None


class CustomFieldStringValue(CustomFieldValue):
    """Represent a string or longtext `CustomFieldValue`."""

    value: str | None = None
    data_type: Literal[CustomFieldType.STRING, CustomFieldType.LONGTEXT] = Field(
        default=CustomFieldType.STRING, exclude=True
    )


class CustomFieldURLValue(CustomFieldValue):
    """Represent an url `CustomFieldValue`."""

    value: str | None = None
    data_type: Literal[CustomFieldType.URL] = Field(default=CustomFieldType.URL, exclude=True)


# Discriminated union resolving a value payload to its typed class via ``data_type``.
TypedCustomFieldValue = Annotated[
    CustomFieldBooleanValue
    | CustomFieldDateValue
    | CustomFieldDocumentLinkValue
    | CustomFieldFloatValue
    | CustomFieldIntegerValue
    | CustomFieldMonetaryValue
    | CustomFieldSelectValue
    | CustomFieldStringValue
    | CustomFieldURLValue,
    Field(discriminator="data_type"),
]

# A typed value when ``data_type`` is known, a plain ``CustomFieldValue`` otherwise.
AnyCustomFieldValue = Annotated[
    TypedCustomFieldValue | CustomFieldValue,
    Field(union_mode="left_to_right"),
]

_ANY_VALUE_ADAPTER = TypeAdapter[CustomFieldValue](AnyCustomFieldValue)


class CustomField(
    IdentifiedModel,
):
    """Represent a Paperless `CustomField`."""

    _api_path: ClassVar[str] = EndpointPath.CUSTOM_FIELDS_SINGLE
    _resource: ClassVar[PaperlessResource] = PaperlessResource.CUSTOM_FIELDS

    name: str | None = None
    data_type: CustomFieldType | None = None
    extra_data: CustomFieldExtraData | None = None
    document_count: int | None = None

    @overload
    def draft_value(self, value: Any) -> CustomFieldValue: ...

    @overload
    def draft_value(
        self, value: Any, expected_type: type[CustomFieldValueT]
    ) -> CustomFieldValueT: ...

    def draft_value(
        self,
        value: Any,
        expected_type: type[CustomFieldValueT] | None = None,
    ) -> CustomFieldValue | CustomFieldValueT:
        """Draft a new `CustomFieldValue` instance."""
        cache = self._runtime.cache.custom_fields

        if cache and self.id in cache:
            result: CustomFieldValue = _ANY_VALUE_ADAPTER.validate_python(
                {
                    "field": self.id,
                    "value": value,
                    "name": self.name,
                    "data_type": self.data_type,
                    "extra_data": self.extra_data,
                }
            )
        else:
            result = CustomFieldValue(field=self.id, value=value)

        if expected_type is not None and not isinstance(result, expected_type):
            msg = f"Expected {expected_type.__name__}, got {type(result).__name__}"
            raise TypeError(msg)

        return result


class CustomFieldDraft(PaperlessModel, mixins.CreatableModel):
    """Represent a new Paperless `CustomField`, which is not stored in Paperless."""

    _api_path: ClassVar[str] = EndpointPath.CUSTOM_FIELDS
    _resource: ClassVar[PaperlessResource] = PaperlessResource.CUSTOM_FIELDS

    _create_required_fields: ClassVar[set[str]] = {"name", "data_type"}

    name: str | None = None
    data_type: CustomFieldType | None = None
    extra_data: CustomFieldExtraData | None = None
