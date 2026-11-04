"""Provide `ShareLink` related models."""

import datetime as dt
from enum import StrEnum
from typing import ClassVar, Self

from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.models import mixins
from pypaperless.models.base import IdentifiedModel, PaperlessModel


class ShareLinkFileVersion(StrEnum):
    """Represent a subtype of `ShareLink`."""

    ARCHIVE = "archive"
    ORIGINAL = "original"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, *_: object) -> Self:
        """Return the UNKNOWN member for any unrecognised value."""
        return cls["UNKNOWN"]


class ShareLink(
    IdentifiedModel,
):
    """Represent a Paperless `ShareLink`."""

    _api_path: ClassVar[str] = EndpointPath.SHARE_LINKS_SINGLE
    _resource: ClassVar[PaperlessResource] = PaperlessResource.SHARE_LINKS

    created: dt.datetime | None = None
    expiration: dt.datetime | None = None
    slug: str | None = None
    document: int | None = None
    file_version: ShareLinkFileVersion | None = None


class ShareLinkDraft(PaperlessModel, mixins.CreatableModel):
    """Represent a new Paperless `ShareLink`, which is not stored in Paperless."""

    _api_path: ClassVar[str] = EndpointPath.SHARE_LINKS
    _resource: ClassVar[PaperlessResource] = PaperlessResource.SHARE_LINKS

    _create_required_fields: ClassVar[set[str]] = {"document", "file_version"}

    expiration: dt.datetime | None = None
    document: int | None = None
    file_version: ShareLinkFileVersion | None = None
