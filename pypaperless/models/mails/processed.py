"""Provide `ProcessedMail` related models."""

import datetime as dt
from typing import ClassVar

from pypaperless.const import EndpointPath
from pypaperless.models.base import IdentifiedModel


class ProcessedMail(IdentifiedModel):
    """Represent a Paperless `ProcessedMail`."""

    _api_path: ClassVar[str] = EndpointPath.PROCESSED_MAIL_SINGLE

    owner: int | None = None
    rule: int | None = None
    folder: str | None = None
    uid: str | None = None
    subject: str | None = None
    received: dt.datetime | None = None
    processed: dt.datetime | None = None
    status: str | None = None
    error: str | None = None
