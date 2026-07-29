"""Raw data constants."""

import json
from pathlib import Path

from .bulk_edit_objects import DATA_BULK_EDIT_OBJECTS
from .config import DATA_CONFIG
from .correspondents import DATA_CORRESPONDENTS
from .custom_fields import DATA_CUSTOM_FIELDS
from .document_ai_suggestions import DATA_DOCUMENT_AI_SUGGESTIONS
from .document_chat import DATA_DOCUMENT_CHAT
from .document_history import DATA_DOCUMENT_HISTORY
from .document_metadata import DATA_DOCUMENT_METADATA
from .document_notes import DATA_DOCUMENT_NOTES
from .document_root import DATA_DOCUMENT_ROOT
from .document_share_links import DATA_DOCUMENT_SHARE_LINKS
from .document_suggestions import DATA_DOCUMENT_SUGGESTIONS
from .document_types import DATA_DOCUMENT_TYPES
from .document_version_info import DATA_DOCUMENT_VERSION_INFO
from .documents import DATA_DOCUMENTS
from .documents_bulk_edit import DATA_DOCUMENTS_BULK_EDIT
from .documents_search import DATA_DOCUMENTS_SEARCH
from .groups import DATA_GROUPS
from .mails import DATA_MAIL_ACCOUNTS, DATA_MAIL_RULES, DATA_PROCESSED_MAIL
from .object_permissions import DATA_OBJECT_PERMISSIONS
from .paths import DATA_PATHS
from .profile import DATA_PROFILE
from .remote_version import DATA_REMOTE_VERSION
from .saved_views import DATA_SAVED_VIEWS
from .search import DATA_SEARCH
from .share_link_bundles import DATA_SHARE_LINK_BUNDLES
from .share_links import DATA_SHARE_LINKS
from .statistics import DATA_STATISTICS
from .status import DATA_STATUS
from .storage_paths import DATA_STORAGE_PATHS
from .tags import DATA_TAGS
from .tasks import (
    DATA_TASKS,
    DATA_TASKS_ACTIVE,
    DATA_TASKS_STATUS_COUNTS,
    DATA_TASKS_SUMMARY,
)
from .token import DATA_TOKEN
from .trash import DATA_TRASH
from .users import DATA_USERS
from .workflows import DATA_WORKFLOW_ACTIONS, DATA_WORKFLOW_TRIGGERS, DATA_WORKFLOWS


def _read_schema() -> dict:
    filepath = Path(__file__).parent / "schema.json"
    with Path.open(filepath, mode="r", encoding="utf-8") as file:
        return json.load(file)


DATA_SCHEMA = _read_schema()


__all__ = (
    "DATA_BULK_EDIT_OBJECTS",
    "DATA_CONFIG",
    "DATA_CORRESPONDENTS",
    "DATA_CUSTOM_FIELDS",
    "DATA_DOCUMENTS",
    "DATA_DOCUMENTS_BULK_EDIT",
    "DATA_DOCUMENTS_SEARCH",
    "DATA_DOCUMENT_AI_SUGGESTIONS",
    "DATA_DOCUMENT_CHAT",
    "DATA_DOCUMENT_HISTORY",
    "DATA_DOCUMENT_METADATA",
    "DATA_DOCUMENT_NOTES",
    "DATA_DOCUMENT_ROOT",
    "DATA_DOCUMENT_SHARE_LINKS",
    "DATA_DOCUMENT_SUGGESTIONS",
    "DATA_DOCUMENT_TYPES",
    "DATA_DOCUMENT_VERSION_INFO",
    "DATA_GROUPS",
    "DATA_MAIL_ACCOUNTS",
    "DATA_MAIL_RULES",
    "DATA_OBJECT_PERMISSIONS",
    "DATA_PATHS",
    "DATA_PROCESSED_MAIL",
    "DATA_PROFILE",
    "DATA_REMOTE_VERSION",
    "DATA_SAVED_VIEWS",
    "DATA_SCHEMA",
    "DATA_SEARCH",
    "DATA_SHARE_LINKS",
    "DATA_SHARE_LINK_BUNDLES",
    "DATA_STATISTICS",
    "DATA_STATUS",
    "DATA_STORAGE_PATHS",
    "DATA_TAGS",
    "DATA_TASKS",
    "DATA_TASKS_ACTIVE",
    "DATA_TASKS_STATUS_COUNTS",
    "DATA_TASKS_SUMMARY",
    "DATA_TOKEN",
    "DATA_TRASH",
    "DATA_USERS",
    "DATA_WORKFLOWS",
    "DATA_WORKFLOW_ACTIONS",
    "DATA_WORKFLOW_TRIGGERS",
)
