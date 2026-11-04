"""Provide `DocumentHistory` related models."""

import datetime as dt
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from pypaperless.const import EndpointPath
from pypaperless.models.base import IdentifiedModel


class DocumentHistoryAction(StrEnum):
    """Represent the action type of a `DocumentHistory` entry."""

    CREATE = "create"
    UPDATE = "update"


class DocumentHistoryActor(BaseModel):
    """Represent the actor field of a `DocumentHistory` entry."""

    id: int | None = None
    username: str | None = None


class DocumentHistory(IdentifiedModel):
    """Represent a single Paperless document history (audit-log) entry."""

    _api_path: ClassVar[str] = EndpointPath.DOCUMENTS_HISTORY

    document: int | None = None
    timestamp: dt.datetime | None = None
    action: DocumentHistoryAction | None = None
    changes: dict[str, Any] = Field(default_factory=dict)
    actor: DocumentHistoryActor | None = None
