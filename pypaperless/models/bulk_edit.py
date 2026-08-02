"""Models and types for bulk-edit operations."""

from typing import Any, Literal, TypedDict

type BulkEditObjectType = Literal["tags", "correspondents", "document_types", "storage_paths"]
type SourceMode = Literal["latest_version", "explicit_selection"]
type CustomFieldsInput = list[int] | dict[int, Any]


class _EditPdfOperationRequired(TypedDict):
    page: int


class EditPdfOperation(_EditPdfOperationRequired, total=False):
    """Represent one page operation for the edit_pdf bulk action."""

    rotate: int
    doc: int
