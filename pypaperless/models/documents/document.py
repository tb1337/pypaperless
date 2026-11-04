"""Provide `Document` related models."""

import datetime as dt
import json
from collections.abc import Iterator
from enum import StrEnum
from typing import Any, ClassVar, Self, cast, overload

from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    RootModel,
    ValidationInfo,
    model_validator,
)

from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.exceptions import ItemNotFoundError
from pypaperless.models import mixins
from pypaperless.models.base import IdentifiedModel, PaperlessModel
from pypaperless.models.custom_fields import (
    AnyCustomFieldValue,
    CustomField,
    CustomFieldValue,
    CustomFieldValueT,
)
from pypaperless.models.documents.notes import DocumentNote
from pypaperless.models.documents.versions import DocumentVersionInfo
from pypaperless.services.documents.ai_suggestions import DocumentAISuggestionsService
from pypaperless.services.documents.history import DocumentHistoryService
from pypaperless.services.documents.notes import DocumentNoteService
from pypaperless.services.documents.share_links import DocumentShareLinkService
from pypaperless.services.documents.versions import DocumentRootService, DocumentVersionService


class DocumentMetaEntry(BaseModel):
    """Represent a subtype of `DocumentMeta`."""

    namespace: str | None = None
    prefix: str | None = None
    key: str | None = None
    value: str | None = None


class DocumentSearchHit(BaseModel):
    """Represent a subtype of `Document`."""

    score: float | None = None
    highlights: str | None = None
    note_highlights: str | None = None
    rank: int | None = None


class DuplicateDocumentSummary(BaseModel):
    """Represent a subtype of `Document`."""

    id: int | None = None
    title: str | None = None
    deleted_at: dt.datetime | None = None


class FileRetrieveMode(StrEnum):
    """Represent a subtype of `DownloadedDocument`."""

    DOWNLOAD = "download"
    PREVIEW = "preview"
    THUMBNAIL = "thumb"


class DocumentCustomFieldList(RootModel[list[AnyCustomFieldValue]]):
    """Represent a list of Paperless custom field instances typically on documents.

    Items are validated into their typed :class:`CustomFieldValue` subclass via
    the ``data_type`` discriminator. Raw API payloads carry only ``field`` and
    ``value`` - when the custom-fields cache is populated, each item is
    enriched with ``name``, ``data_type``, and ``extra_data`` before validation.
    """

    root: list[AnyCustomFieldValue] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _enrich_from_cache(cls, data: Any, info: ValidationInfo) -> Any:
        """Merge cached CustomField metadata into raw items so the discriminator resolves."""
        context = info.context if isinstance(info.context, dict) else {}
        runtime = context.get("runtime")
        cache = runtime.cache.custom_fields if runtime is not None else None
        if not isinstance(data, list) or not cache:
            return data
        enriched: list[Any] = []
        for item in data:
            if isinstance(item, dict) and (field := cache.get(item.get("field"))):
                enriched.append(
                    {
                        **item,
                        "name": field.name,
                        "data_type": field.data_type,
                        "extra_data": field.extra_data,
                    }
                )
            else:
                enriched.append(item)
        return enriched

    @classmethod
    def from_data(cls, runtime: Any, data: list[Any]) -> Self:
        """Return a new instance from raw API data, enriching from *runtime*'s cache."""
        return cls.model_validate(data, context={"runtime": runtime})

    def __contains__(self, field: int | CustomField) -> bool:
        """Check if the given `CustomField` or its id is present in `DocumentCustomFieldList`."""
        item_id = field.id if isinstance(field, CustomField) else field
        return any(item.field == item_id for item in self.root)

    def __iter__(self) -> Iterator[CustomFieldValue]:  # type: ignore[override]
        """Iterate over custom fields.

        This intentionally behaves like a container iterator (yielding
        ``CustomFieldValue`` items) instead of Pydantic's field-pair iterator.

        Example::

            for item in document.custom_fields:
                print(item.field, item.value)

        """
        yield from self.root

    def __iadd__(self, field: CustomFieldValue) -> Self:
        """Add a new `CustomFieldValue` to a document."""
        return self.add(field)

    def add(self, field: CustomFieldValue) -> Self:
        """Add a new `CustomFieldValue` to a document."""
        self.root.append(field)
        return self

    def __isub__(self, field: CustomFieldValue | CustomField | int) -> Self:
        """Remove a `CustomFieldValue` from a document."""
        return self.remove(field)

    def remove(self, field: CustomFieldValue | CustomField | int) -> Self:
        """Remove a `CustomFieldValue` from a document."""
        item_id = (
            field.id
            if isinstance(field, CustomField)
            else field.field
            if isinstance(field, CustomFieldValue)
            else field
        )
        self.root = [field for field in self.root if field.field != item_id]
        return self

    @overload
    def default(self, field: int | CustomField) -> CustomFieldValue | None: ...

    @overload
    def default(
        self, field: int | CustomField, expected_type: type[CustomFieldValueT]
    ) -> CustomFieldValueT | None: ...

    def default(
        self, field: int | CustomField, expected_type: type[CustomFieldValueT] | None = None
    ) -> CustomFieldValue | CustomFieldValueT | None:
        """Access and return a (typed) `CustomFieldValue`, or `None`."""
        try:
            value = self.get(field)
        except ItemNotFoundError:
            return None

        if expected_type is not None and not isinstance(value, expected_type):
            msg = f"Expected {expected_type.__name__}, got {type(value).__name__}"
            raise TypeError(msg)

        return value

    @overload
    def get(self, field: int | CustomField) -> CustomFieldValue: ...

    @overload
    def get(
        self, field: int | CustomField, expected_type: type[CustomFieldValueT]
    ) -> CustomFieldValueT: ...

    def get(
        self, field: int | CustomField, expected_type: type[CustomFieldValueT] | None = None
    ) -> CustomFieldValue | CustomFieldValueT:
        """Access and return a (typed) `CustomFieldValue` from the list."""
        item_id = field.id if isinstance(field, CustomField) else field
        for item in self.root:
            if item.field == item_id:
                if expected_type is not None and not isinstance(item, expected_type):
                    msg = f"Expected {expected_type.__name__}, got {type(item).__name__}"
                    raise TypeError(msg)
                return item
        raise ItemNotFoundError

    def serialize(self) -> list[dict[str, Any]]:
        """Return the JSON-safe ``[{"field": ..., "value": ...}]`` payload for the API."""
        return cast("list[dict[str, Any]]", self.model_dump(mode="json"))


class Document(
    IdentifiedModel,
    mixins.SecurableModel,
):
    """Represent a Paperless `Document`."""

    _api_path: ClassVar[str] = EndpointPath.DOCUMENTS_SINGLE
    _resource: ClassVar[PaperlessResource] = PaperlessResource.DOCUMENTS

    _history: DocumentHistoryService | None = PrivateAttr(default=None)
    _ai_suggestions: DocumentAISuggestionsService | None = PrivateAttr(default=None)
    _notes: DocumentNoteService | None = PrivateAttr(default=None)
    _root: DocumentRootService | None = PrivateAttr(default=None)
    _share_links: DocumentShareLinkService | None = PrivateAttr(default=None)
    _versions: DocumentVersionService | None = PrivateAttr(default=None)

    correspondent: int | None = None
    document_type: int | None = None
    storage_path: int | None = None
    title: str | None = None
    content: str | None = None
    tags: list[int] | None = None
    created: dt.date | None = None
    modified: dt.datetime | None = None
    added: dt.datetime | None = None
    deleted_at: dt.datetime | None = None
    archive_serial_number: int | None = None
    original_file_name: str | None = None
    archived_file_name: str | None = None
    duplicate_documents: list[DuplicateDocumentSummary] | None = None
    is_shared_by_requester: bool | None = None
    custom_fields: DocumentCustomFieldList | None = None
    notes_: list[DocumentNote] | None = Field(default=None, alias="notes", exclude=True, repr=False)
    page_count: int | None = None
    mime_type: str | None = None
    root_document: int | None = None
    versions_: list[DocumentVersionInfo] | None = Field(
        default=None, alias="versions", exclude=True, repr=False
    )
    search_hit_: DocumentSearchHit | None = Field(default=None, alias="__search_hit__")

    @model_validator(mode="after")
    def _init_notes_cache(self) -> "Document":
        """Backfill note.document from self.id when the API omits it in the embedded payload."""
        if self.notes_ is not None and self.id is not None:
            for note in self.notes_:
                if note.document is None:
                    note.document = self.id
        return self

    @property
    def ai_suggestions(self) -> DocumentAISuggestionsService:
        """Return the AI suggestions service for this document."""
        if self._ai_suggestions is None:
            self._ai_suggestions = DocumentAISuggestionsService(self._runtime, self.id)
        return self._ai_suggestions

    @property
    def history(self) -> DocumentHistoryService:
        """Return the history service for this document."""
        if self._history is None:
            self._history = DocumentHistoryService(self._runtime, self.id)
        return self._history

    @property
    def notes(self) -> DocumentNoteService:
        """Return the notes service for this document."""
        if self._notes is None:
            self._notes = DocumentNoteService(self._runtime, document=self)
        return self._notes

    @property
    def root(self) -> DocumentRootService:
        """Return the root service for this document."""
        if self._root is None:
            self._root = DocumentRootService(self._runtime, self.id)
        return self._root

    @property
    def share_links(self) -> DocumentShareLinkService:
        """Return the share links service for this document."""
        if self._share_links is None:
            self._share_links = DocumentShareLinkService(self._runtime, self.id)
        return self._share_links

    @property
    def versions(self) -> DocumentVersionService:
        """Return the versions service for this document."""
        if self._versions is None:
            self._versions = DocumentVersionService(self._runtime, self.id)
        return self._versions

    @property
    def created_date(self) -> dt.date | None:
        """Backward compatibility for the removed `created_date` field."""
        return self.created

    @property
    def is_deleted(self) -> bool:
        """Return True if the document is in the trash."""
        return self.deleted_at is not None

    @property
    def has_search_hit(self) -> bool:
        """Return if the document has a search hit attached."""
        return self.search_hit_ is not None

    @property
    def search_hit(self) -> DocumentSearchHit | None:
        """Return the document search hit."""
        return self.search_hit_


class DocumentDraft(PaperlessModel, mixins.CreatableModel):
    """Represent a new Paperless `Document`, which is not stored in Paperless."""

    _api_path: ClassVar[str] = EndpointPath.DOCUMENTS_POST
    _resource: ClassVar[PaperlessResource] = PaperlessResource.DOCUMENTS

    _create_required_fields: ClassVar[set[str]] = {"document"}
    _dump_exclude: ClassVar[set[str]] = {"document"}

    document: bytes | None = None
    filename: str | None = None
    title: str | None = None
    created: dt.datetime | None = None
    correspondent: int | None = None
    document_type: int | None = None
    storage_path: int | None = None
    tags: int | list[int] | None = None
    archive_serial_number: int | None = None
    custom_fields: list[int] | DocumentCustomFieldList | None = None

    def serialize(self) -> dict[str, Any]:
        """Return the multipart form data payload for POSTing a new document."""
        data: dict[str, dict[str, Any]] = {
            "form": self.model_dump(
                mode="json",
                by_alias=True,
                exclude={"document", "filename", "custom_fields"},
            )
        }

        if self.custom_fields is not None:
            if isinstance(self.custom_fields, DocumentCustomFieldList):
                cf_map = {
                    str(item["field"]): item["value"] for item in self.custom_fields.serialize()
                }
                data["form"]["custom_fields"] = json.dumps(cf_map)
            else:
                data["form"]["custom_fields"] = self.custom_fields

        data["form"].update(
            {
                "document": (
                    (self.document, self.filename) if self.filename is not None else self.document
                )
            }
        )
        return data


class DocumentMeta(PaperlessModel):
    """Represent a Paperless `Document`'s metadata."""

    _api_path: ClassVar[str] = EndpointPath.DOCUMENTS_META

    id: int | None = None
    original_checksum: str | None = None
    original_size: int | None = None
    original_mime_type: str | None = None
    media_filename: str | None = None
    has_archive_version: bool | None = None
    original_metadata: list[DocumentMetaEntry] | None = None
    archive_checksum: str | None = None
    archive_media_filename: str | None = None
    original_filename: str | None = None
    lang: str | None = None
    archive_size: int | None = None
    archive_metadata: list[DocumentMetaEntry] | None = None


class DownloadedDocument(IdentifiedModel):
    """Represent a Paperless `Document`'s downloaded file."""

    _api_path: ClassVar[str] = EndpointPath.DOCUMENTS
    _dump_exclude: ClassVar[set[str]] = {"content"}

    mode: FileRetrieveMode | None = None
    original: bool | None = None
    content: bytes | None = None
    content_type: str | None = None
    disposition_filename: str | None = None
    disposition_type: str | None = None


class DocumentSuggestions(IdentifiedModel):
    """Represent a Paperless `Document`'s suggestions."""

    _api_path: ClassVar[str] = EndpointPath.DOCUMENTS_SUGGESTIONS

    correspondents: list[int] | None = None
    tags: list[int] | None = None
    document_types: list[int] | None = None
    storage_paths: list[int] | None = None
    dates: list[dt.date] | None = None
