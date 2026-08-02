"""PyPaperless constants."""

from enum import StrEnum
from typing import Self

API_VERSION = 10

ENV_PREFIX = "PYPAPERLESS_"
ENV_URL = f"{ENV_PREFIX}URL"
ENV_TOKEN = f"{ENV_PREFIX}TOKEN"


class EndpointPath(StrEnum):
    """URL paths for all Paperless-ngx REST API endpoints.

    Members are plain :class:`str` values, so ``.format(pk=42)`` works
    directly on any member that contains a ``{pk}`` placeholder::

        url = EndpointPath.DOCUMENTS_SINGLE.format(pk=42)
        # → "/api/documents/42/"

    """

    INDEX = "/api/schema/"
    TOKEN = "/api/token/"

    BULK_EDIT_OBJECTS = "/api/bulk_edit_objects/"

    CONFIG = "/api/config/"
    CONFIG_SINGLE = "/api/config/{pk}/"

    CORRESPONDENTS = "/api/correspondents/"
    CORRESPONDENTS_SINGLE = "/api/correspondents/{pk}/"

    CUSTOM_FIELDS = "/api/custom_fields/"
    CUSTOM_FIELDS_SINGLE = "/api/custom_fields/{pk}/"

    DOCUMENT_TYPES = "/api/document_types/"
    DOCUMENT_TYPES_SINGLE = "/api/document_types/{pk}/"

    DOCUMENTS = "/api/documents/"
    DOCUMENTS_AI_SUGGESTIONS = "/api/documents/{pk}/ai_suggestions/"
    DOCUMENTS_BULK_EDIT = "/api/documents/bulk_edit/"
    DOCUMENTS_CHAT = "/api/documents/chat/"
    DOCUMENTS_DELETE = "/api/documents/delete/"
    DOCUMENTS_DOWNLOAD = "/api/documents/{pk}/download/"
    DOCUMENTS_EDIT_PDF = "/api/documents/edit_pdf/"
    DOCUMENTS_EMAIL = "/api/documents/email/"
    DOCUMENTS_HISTORY = "/api/documents/{pk}/history/"
    DOCUMENTS_MERGE = "/api/documents/merge/"
    DOCUMENTS_META = "/api/documents/{pk}/metadata/"
    DOCUMENTS_NEXT_ASN = "/api/documents/next_asn/"
    DOCUMENTS_NOTES = "/api/documents/{pk}/notes/"
    DOCUMENTS_POST = "/api/documents/post_document/"
    DOCUMENTS_PREVIEW = "/api/documents/{pk}/preview/"
    DOCUMENTS_REMOVE_PASSWORD = "/api/documents/remove_password/"
    DOCUMENTS_REPROCESS = "/api/documents/reprocess/"
    DOCUMENTS_ROTATE = "/api/documents/rotate/"
    DOCUMENTS_ROOT = "/api/documents/{pk}/root/"
    DOCUMENTS_SHARE_LINKS = "/api/documents/{pk}/share_links/"
    DOCUMENTS_SINGLE = "/api/documents/{pk}/"
    DOCUMENTS_SUGGESTIONS = "/api/documents/{pk}/suggestions/"
    DOCUMENTS_THUMBNAIL = "/api/documents/{pk}/thumb/"
    DOCUMENTS_UPDATE_VERSION = "/api/documents/{pk}/update_version/"
    DOCUMENTS_VERSION = "/api/documents/{pk}/versions/{version_id}/"

    GROUPS = "/api/groups/"
    GROUPS_SINGLE = "/api/groups/{pk}/"

    MAIL_ACCOUNTS = "/api/mail_accounts/"
    MAIL_ACCOUNTS_PROCESS = "/api/mail_accounts/{pk}/process/"
    MAIL_ACCOUNTS_SINGLE = "/api/mail_accounts/{pk}/"
    MAIL_ACCOUNTS_TEST = "/api/mail_accounts/test/"

    MAIL_RULES = "/api/mail_rules/"
    MAIL_RULES_SINGLE = "/api/mail_rules/{pk}/"

    PROCESSED_MAIL = "/api/processed_mail/"
    PROCESSED_MAIL_SINGLE = "/api/processed_mail/{pk}/"

    PROFILE = "/api/profile/"

    REMOTE_VERSION = "/api/remote_version/"

    SAVED_VIEWS = "/api/saved_views/"
    SAVED_VIEWS_SINGLE = "/api/saved_views/{pk}/"

    SEARCH = "/api/search/"
    SEARCH_AUTOCOMPLETE = "/api/search/autocomplete/"

    SHARE_LINKS = "/api/share_links/"
    SHARE_LINKS_SINGLE = "/api/share_links/{pk}/"

    SHARE_LINK_BUNDLES = "/api/share_link_bundles/"
    SHARE_LINK_BUNDLES_REBUILD = "/api/share_link_bundles/{pk}/rebuild/"
    SHARE_LINK_BUNDLES_SINGLE = "/api/share_link_bundles/{pk}/"

    STATISTICS = "/api/statistics/"

    STATUS = "/api/status/"

    STORAGE_PATHS = "/api/storage_paths/"
    STORAGE_PATHS_SINGLE = "/api/storage_paths/{pk}/"

    TAGS = "/api/tags/"
    TAGS_SINGLE = "/api/tags/{pk}/"

    TASKS = "/api/tasks/"
    TASKS_ACKNOWLEDGE = "/api/tasks/acknowledge/"
    TASKS_ACTIVE = "/api/tasks/active/"
    TASKS_RUN = "/api/tasks/run/"
    TASKS_SINGLE = "/api/tasks/{pk}/"
    TASKS_STATUS_COUNTS = "/api/tasks/status_counts/"
    TASKS_SUMMARY = "/api/tasks/summary/"

    TRASH = "/api/trash/"

    USERS = "/api/users/"
    USERS_SINGLE = "/api/users/{pk}/"

    WORKFLOW_ACTIONS = "/api/workflow_actions/"
    WORKFLOW_ACTIONS_SINGLE = "/api/workflow_actions/{pk}/"

    WORKFLOW_TRIGGERS = "/api/workflow_triggers/"
    WORKFLOW_TRIGGERS_SINGLE = "/api/workflow_triggers/{pk}/"

    WORKFLOWS = "/api/workflows/"
    WORKFLOWS_SINGLE = "/api/workflows/{pk}/"


class PaperlessResource(StrEnum):
    """Represent resource names of Paperless-ngx API endpoints."""

    BULK_EDIT_OBJECTS = "bulk_edit_objects"
    CONFIG = "config"
    CORRESPONDENTS = "correspondents"
    CUSTOM_FIELDS = "custom_fields"
    DOCUMENTS = "documents"
    DOCUMENT_TYPES = "document_types"
    GROUPS = "groups"
    MAIL_ACCOUNTS = "mail_accounts"
    MAIL_RULES = "mail_rules"
    PROCESSED_MAIL = "processed_mail"
    PROFILE = "profile"
    SAVED_VIEWS = "saved_views"
    SEARCH = "search"
    SHARE_LINK_BUNDLES = "share_link_bundles"
    SHARE_LINKS = "share_links"
    STATISTICS = "statistics"
    REMOTE_VERSION = "remote_version"
    STATUS = "status"
    STORAGE_PATHS = "storage_paths"
    TAGS = "tags"
    TASKS = "tasks"
    TRASH = "trash"
    USERS = "users"
    WORKFLOWS = "workflows"
    WORKFLOW_ACTIONS = "workflow_actions"
    WORKFLOW_TRIGGERS = "workflow_triggers"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, *_: object) -> Self:
        """Set default member on unknown value."""
        return cls.UNKNOWN
