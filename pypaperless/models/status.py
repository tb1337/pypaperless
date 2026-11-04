"""Provide `Status` related models."""

import datetime as dt
from enum import StrEnum
from typing import ClassVar, Self

from pydantic import BaseModel, Field

from pypaperless.const import EndpointPath

from .base import PaperlessModel


class StatusType(StrEnum):
    """Represent a subtype of `Status`."""

    OK = "OK"
    ERROR = "ERROR"
    WARNING = "WARNING"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def _missing_(cls, *_: object) -> Self:
        """Return the UNKNOWN member for any unrecognised value."""
        return cls["UNKNOWN"]


class StatusDatabaseMigration(BaseModel):
    """Represent a subtype of `StatusDatabase`."""

    latest_migration: str | None = None
    unapplied_migrations: list[str] = Field(default_factory=list)


class StatusDatabase(BaseModel):
    """Represent a subtype of `Status`."""

    type: str | None = None
    url: str | None = None
    status: StatusType | None = None
    error: str | None = None
    migration_status: StatusDatabaseMigration | None = None


class StatusStorage(BaseModel):
    """Represent a subtype of `Status`."""

    total: int | None = None
    available: int | None = None


class StatusTasksSummary(BaseModel):
    """Represent a subtype of `StatusTasks`."""

    days: int | None = None
    total_count: int | None = None
    pending_count: int | None = None
    success_count: int | None = None
    failure_count: int | None = None


class StatusTasks(BaseModel):
    """Represent a subtype of `Status`."""

    redis_url: str | None = None
    redis_status: StatusType | None = None
    redis_error: str | None = None
    celery_status: StatusType | None = None
    celery_url: str | None = None
    celery_error: str | None = None
    index_status: StatusType | None = None
    index_last_modified: dt.datetime | None = None
    index_error: str | None = None
    classifier_status: StatusType | None = None
    classifier_last_trained: dt.datetime | None = None
    classifier_error: str | None = None
    sanity_check_status: StatusType | None = None
    sanity_check_last_run: dt.datetime | None = None
    sanity_check_error: str | None = None
    summary: StatusTasksSummary | None = None


class Status(PaperlessModel):
    """Represent a Paperless `Status`."""

    _api_path: ClassVar[str] = EndpointPath.STATUS

    pngx_version: str | None = None
    server_os: str | None = None
    install_type: str | None = None
    storage: StatusStorage | None = None
    database: StatusDatabase | None = None
    tasks: StatusTasks | None = None

    @property
    def has_errors(self) -> bool:
        """Return whether any status flag is `ERROR`."""
        statuses: list[StatusType] = [
            self.database.status if self.database and self.database.status else StatusType.OK,
        ]

        if self.tasks:
            statuses.extend(
                [
                    self.tasks.redis_status or StatusType.OK,
                    self.tasks.celery_status or StatusType.OK,
                    self.tasks.classifier_status or StatusType.OK,
                ]
            )

        return StatusType.ERROR in statuses
