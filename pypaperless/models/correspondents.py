"""Provide `Correspondent` related models."""

import datetime as dt
from typing import ClassVar

from pypaperless.const import EndpointPath, PaperlessResource

from . import mixins
from .base import IdentifiedModel, PaperlessModel


class Correspondent(
    IdentifiedModel,
    mixins.MatchingFieldsModel,
    mixins.SecurableModel,
):
    """Represent a Paperless `Correspondent`."""

    _api_path: ClassVar[str] = EndpointPath.CORRESPONDENTS_SINGLE
    _resource: ClassVar[PaperlessResource] = PaperlessResource.CORRESPONDENTS

    slug: str | None = None
    name: str | None = None
    document_count: int | None = None
    last_correspondence: dt.date | None = None


class CorrespondentDraft(
    PaperlessModel,
    mixins.MatchingFieldsModel,
    mixins.SecurableDraftModel,
    mixins.CreatableModel,
):
    """Represent a new `Correspondent`, which is not yet stored in Paperless."""

    _api_path: ClassVar[str] = EndpointPath.CORRESPONDENTS
    _resource: ClassVar[PaperlessResource] = PaperlessResource.CORRESPONDENTS

    _create_required_fields: ClassVar[set[str]] = {
        "name",
        "match",
        "matching_algorithm",
        "is_insensitive",
    }

    name: str | None = None
