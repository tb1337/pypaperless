"""Provide `DocumentNote` related models."""

import datetime as dt
from typing import Any, ClassVar

from pydantic import field_validator

from pypaperless.const import EndpointPath
from pypaperless.models import mixins
from pypaperless.models.base import IdentifiedModel, PaperlessModel


class DocumentNote(IdentifiedModel):
    """Represent a Paperless `DocumentNote`."""

    _api_path: ClassVar[str] = EndpointPath.DOCUMENTS_NOTES
    _pk_field: ClassVar[str] = "document"

    note: str | None = None
    created: dt.datetime | None = None
    document: int | None = None
    user: int | None = None

    @field_validator("user", mode="before")
    @classmethod
    def _coerce_user(cls, v: Any) -> Any:
        """Normalize a user dict from the API to its id."""
        if isinstance(v, dict):
            return v["id"]
        return v


class DocumentNoteDraft(PaperlessModel, mixins.CreatableModel):
    """Represent a new Paperless `DocumentNote`, which is not stored in Paperless."""

    _api_path: ClassVar[str] = EndpointPath.DOCUMENTS_NOTES
    _pk_field: ClassVar[str] = "document"

    _create_required_fields: ClassVar[set[str]] = {"note", "document"}

    note: str | None = None
    document: int | None = None
