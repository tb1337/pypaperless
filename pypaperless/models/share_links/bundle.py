"""Provide `ShareLinkBundle` related models."""

import datetime as dt
from enum import StrEnum
from typing import Any, ClassVar, Self

from pydantic import Field

from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.models import mixins
from pypaperless.models.base import IdentifiedModel, PaperlessModel

from .share_link import ShareLinkFileVersion


class ShareLinkBundleStatus(StrEnum):
    """Represent the processing status of a ``ShareLinkBundle``."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, *_: object) -> Self:
        """Return the UNKNOWN member for any unrecognised value."""
        return cls["UNKNOWN"]


class ShareLinkBundle(IdentifiedModel):
    """Represent a Paperless ``ShareLinkBundle``."""

    _api_path: ClassVar[str] = EndpointPath.SHARE_LINK_BUNDLES_SINGLE
    _resource: ClassVar[PaperlessResource] = PaperlessResource.SHARE_LINK_BUNDLES

    created: dt.datetime | None = None
    expiration: dt.datetime | None = None
    slug: str | None = None
    file_version: ShareLinkFileVersion | None = None
    status: ShareLinkBundleStatus | None = None
    size_bytes: int | None = None
    last_error: Any = None
    built_at: dt.datetime | None = None
    documents: list[int] = Field(default_factory=list)
    document_count: int | None = None


class ShareLinkBundleDraft(PaperlessModel, mixins.CreatableModel):
    """Represent a new Paperless ``ShareLinkBundle``, which is not stored in Paperless."""

    _api_path: ClassVar[str] = EndpointPath.SHARE_LINK_BUNDLES
    _resource: ClassVar[PaperlessResource] = PaperlessResource.SHARE_LINK_BUNDLES

    _create_required_fields: ClassVar[set[str]] = {"document_ids"}

    document_ids: list[int] = Field(default_factory=list)
    expiration_days: int | None = None
    file_version: ShareLinkFileVersion | None = None
