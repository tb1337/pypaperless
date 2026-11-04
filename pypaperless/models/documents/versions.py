"""Provide `DocumentVersionInfo` and `DocumentRoot` models."""

import datetime as dt
from typing import ClassVar

from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.models.base import IdentifiedModel, PaperlessModel


class DocumentVersionInfo(IdentifiedModel):
    """Represent version metadata for a Paperless `Document`."""

    _resource: ClassVar[PaperlessResource] = PaperlessResource.DOCUMENTS

    added: dt.datetime | None = None
    version_label: str | None = None
    checksum: str | None = None
    is_root: bool | None = None


class DocumentRoot(PaperlessModel):
    """Represent the root-document response for a Paperless `Document`."""

    _api_path: ClassVar[str] = EndpointPath.DOCUMENTS_ROOT
    _resource: ClassVar[PaperlessResource] = PaperlessResource.DOCUMENTS

    root_id: int | None = None
