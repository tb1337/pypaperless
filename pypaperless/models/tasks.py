"""Provide `Task` related models."""

import datetime as dt
from enum import StrEnum
from typing import Any, ClassVar, Self

from pydantic import BaseModel, Field

from pypaperless.const import EndpointPath

from .base import IdentifiedModel


class TaskType(StrEnum):
    """Represent the type of work a ``Task`` performs."""

    CONSUME_FILE = "consume_file"
    TRAIN_CLASSIFIER = "train_classifier"
    SANITY_CHECK = "sanity_check"
    INDEX_OPTIMIZE = "index_optimize"
    MAIL_FETCH = "mail_fetch"
    LLM_INDEX = "llm_index"
    EMPTY_TRASH = "empty_trash"
    CHECK_WORKFLOWS = "check_workflows"
    BULK_UPDATE = "bulk_update"
    REPROCESS_DOCUMENT = "reprocess_document"
    BUILD_SHARE_LINK = "build_share_link"
    BULK_DELETE = "bulk_delete"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, *_: object) -> Self:
        """Return the UNKNOWN member for any unrecognised value."""
        return cls["UNKNOWN"]


class TaskStatus(StrEnum):
    """Represent the execution status of a ``Task``."""

    FAILURE = "failure"
    PENDING = "pending"
    REVOKED = "revoked"
    STARTED = "started"
    SUCCESS = "success"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, *_: object) -> Self:
        """Return the UNKNOWN member for any unrecognised value."""
        return cls["UNKNOWN"]


class TaskTriggerSource(StrEnum):
    """Represent what initiated a ``Task``."""

    SCHEDULED = "scheduled"
    WEB_UI = "web_ui"
    API_UPLOAD = "api_upload"
    FOLDER_CONSUME = "folder_consume"
    EMAIL_CONSUME = "email_consume"
    SYSTEM = "system"
    MANUAL = "manual"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, *_: object) -> Self:
        """Return the UNKNOWN member for any unrecognised value."""
        return cls["UNKNOWN"]


class Task(IdentifiedModel):
    """Represent a Paperless ``Task``."""

    _api_path: ClassVar[str] = EndpointPath.TASKS_SINGLE

    task_id: str | None = None
    task_type: TaskType | None = None
    task_type_display: str | None = None
    trigger_source: TaskTriggerSource | None = None
    trigger_source_display: str | None = None
    status: TaskStatus | None = None
    status_display: str | None = None
    date_created: dt.datetime | None = None
    date_started: dt.datetime | None = None
    date_done: dt.datetime | None = None
    duration_seconds: float | None = None
    wait_time_seconds: float | None = None
    input_data: Any = None
    result_data: Any = None
    related_document_ids: list[int] = Field(default_factory=list)
    acknowledged: bool | None = None
    owner: int | None = None


class TaskSummary(BaseModel):
    """Represent aggregated statistics for a single task type.

    Returned by :meth:`~pypaperless.services.tasks.TaskService.summary`.

    Example::

        summaries = await paperless.tasks.summary(days=7)
        for s in summaries:
            print(s.task_type, s.success_count, s.failure_count)

    """

    task_type: str
    total_count: int = 0
    pending_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_duration_seconds: float | None = None
    avg_wait_time_seconds: float | None = None
    last_run: dt.datetime | None = None
    last_success: dt.datetime | None = None
    last_failure: dt.datetime | None = None


class TaskStatusCounts(BaseModel):
    """Represent aggregated task counts for the task UI sections.

    Returned by :meth:`~pypaperless.services.tasks.TaskService.status_counts`.

    Example::

        counts = await paperless.tasks.status_counts()
        print(counts.all, counts.needs_attention)

    """

    all: int = 0
    needs_attention: int = 0
    in_progress: int = 0
    completed: int = 0
