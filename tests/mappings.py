"""Resource test mappings for parameterized tests."""

from dataclasses import dataclass
from typing import Any

from pypaperless import models
from pypaperless.const import PaperlessResource
from pypaperless.models import types

from .data import (
    DATA_CORRESPONDENTS,
    DATA_CUSTOM_FIELDS,
    DATA_DOCUMENT_TYPES,
    DATA_DOCUMENTS,
    DATA_GROUPS,
    DATA_MAIL_ACCOUNTS,
    DATA_MAIL_RULES,
    DATA_PROCESSED_MAIL,
    DATA_SAVED_VIEWS,
    DATA_SHARE_LINK_BUNDLES,
    DATA_SHARE_LINKS,
    DATA_STORAGE_PATHS,
    DATA_TAGS,
    DATA_USERS,
    DATA_WORKFLOWS,
)


@dataclass
class ResourceTestMapping:
    """Mapping for parameterized resource test cases."""

    resource: str
    data: dict[str, Any] | list[dict[str, Any]]
    model_cls: type
    draft_cls: type | None = None
    draft_defaults: dict[str, Any] | None = None
    # field name to blank-out for DraftFieldRequiredError check; None = skip
    required_field: str | None = "name"
    # field and value used by test_update
    update_field: str = "name"
    update_value: Any = "Name Updated"


CORRESPONDENT_MAP = ResourceTestMapping(
    PaperlessResource.CORRESPONDENTS,
    DATA_CORRESPONDENTS,
    models.Correspondent,
    models.CorrespondentDraft,
    {
        "name": "New Correspondent",
        "match": "",
        "matching_algorithm": types.MatchingAlgorithm.ANY,
        "is_insensitive": True,
    },
)

CUSTOM_FIELD_MAP = ResourceTestMapping(
    PaperlessResource.CUSTOM_FIELDS,
    DATA_CUSTOM_FIELDS,
    models.CustomField,
    models.CustomFieldDraft,
    {
        "name": "New Custom Field",
        "data_type": types.CustomFieldType.BOOLEAN,
    },
    required_field=None,
)

DOCUMENT_MAP = ResourceTestMapping(
    PaperlessResource.DOCUMENTS,
    DATA_DOCUMENTS,
    models.Document,
    models.DocumentDraft,
    {
        "document": b"...example...content...",
        "tags": [1, 2, 3],
        "correspondent": 1,
        "document_type": 1,
        "storage_path": 1,
        "title": "New Document",
        "created": None,
        "archive_serial_number": 1,
    },
    update_field="title",
    update_value="Updated Title",
)

DOCUMENT_TYPE_MAP = ResourceTestMapping(
    PaperlessResource.DOCUMENT_TYPES,
    DATA_DOCUMENT_TYPES,
    models.DocumentType,
    models.DocumentTypeDraft,
    {
        "name": "New Document Type",
        "match": "",
        "matching_algorithm": types.MatchingAlgorithm.ANY,
        "is_insensitive": True,
    },
)

GROUP_MAP = ResourceTestMapping(
    PaperlessResource.GROUPS,
    DATA_GROUPS,
    models.Group,
)

MAIL_ACCOUNT_MAP = ResourceTestMapping(
    PaperlessResource.MAIL_ACCOUNTS,
    DATA_MAIL_ACCOUNTS,
    models.MailAccount,
)

MAIL_RULE_MAP = ResourceTestMapping(
    PaperlessResource.MAIL_RULES,
    DATA_MAIL_RULES,
    models.MailRule,
)

PROCESSED_MAIL_MAP = ResourceTestMapping(
    PaperlessResource.PROCESSED_MAIL,
    DATA_PROCESSED_MAIL,
    models.ProcessedMail,
)

SAVED_VIEW_MAP = ResourceTestMapping(
    PaperlessResource.SAVED_VIEWS,
    DATA_SAVED_VIEWS,
    models.SavedView,
)

SHARE_LINK_MAP = ResourceTestMapping(
    PaperlessResource.SHARE_LINKS,
    DATA_SHARE_LINKS,
    models.ShareLink,
    models.ShareLinkDraft,
    {
        "expiration": None,
        "document": 1,
        "file_version": types.ShareLinkFileVersion.ORIGINAL,
    },
    required_field=None,
    update_field="document",
    update_value=2,
)

SHARE_LINK_BUNDLE_MAP = ResourceTestMapping(
    PaperlessResource.SHARE_LINK_BUNDLES,
    DATA_SHARE_LINK_BUNDLES,
    models.ShareLinkBundle,
    models.ShareLinkBundleDraft,
    {
        "document_ids": [1, 2],
        "file_version": types.ShareLinkFileVersion.ARCHIVE,
    },
    required_field=None,
    update_field="document_count",
    update_value=5,
)


STORAGE_PATH_MAP = ResourceTestMapping(
    PaperlessResource.STORAGE_PATHS,
    DATA_STORAGE_PATHS,
    models.StoragePath,
    models.StoragePathDraft,
    {
        "name": "New Storage Path",
        "path": "path/to/test",
        "match": "",
        "matching_algorithm": types.MatchingAlgorithm.ANY,
        "is_insensitive": True,
    },
)

TAG_MAP = ResourceTestMapping(
    PaperlessResource.TAGS,
    DATA_TAGS,
    models.Tag,
    models.TagDraft,
    {
        "name": "New Tag",
        "color": "#012345",
        "text_color": "#987654",
        "is_inbox_tag": False,
        "match": "",
        "matching_algorithm": types.MatchingAlgorithm.ANY,
        "is_insensitive": True,
    },
)


USER_MAP = ResourceTestMapping(
    PaperlessResource.USERS,
    DATA_USERS,
    models.User,
)

WORKFLOW_MAP = ResourceTestMapping(
    PaperlessResource.WORKFLOWS,
    DATA_WORKFLOWS,
    models.Workflow,
)
