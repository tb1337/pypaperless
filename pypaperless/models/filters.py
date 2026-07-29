"""Query filter TypedDicts for pypaperless services.

Each TypedDict reflects the server-side ``FilterSet`` class for the corresponding
Paperless-ngx resource, so IDEs can offer autocomplete and type-checking when
using :meth:`~pypaperless.services.mixins.IterableService.filter`.

Usage::

    async with paperless.documents.filter(
        title__icontains="invoice",
        correspondent__id=3,
        is_tagged=True,
    ) as docs:
        async for doc in docs:
            ...

All fields are optional (``total=False``).  Pagination parameters (``page``,
``page_size``) are intentionally excluded — pass them directly as kwargs.
"""

from typing import TypedDict

from pypaperless.builders import CustomFieldQuery, SearchQuery
from pypaperless.models.share_links import ShareLinkBundleStatus
from pypaperless.models.tasks import TaskStatus, TaskTriggerSource, TaskType


class _CreatedFilters(TypedDict, total=False):
    """Common created-date filter fields."""

    created__date__gt: str  # backwards-compat alias
    created__date__gte: str
    created__date__lt: str
    created__date__lte: str
    created__day: int
    created__gt: str
    created__gte: str
    created__lt: str
    created__lte: str
    created__month: int
    created__year: int


class _IdFilters(TypedDict, total=False):
    """Common id filter fields shared across multiple resources."""

    id: int
    id__in: str  # comma-separated PKs


class _ExpirationFilters(TypedDict, total=False):
    """Common expiration-date filter fields."""

    expiration__date__gt: str
    expiration__date__gte: str
    expiration__date__lt: str
    expiration__date__lte: str
    expiration__day: int
    expiration__gt: str
    expiration__gte: str
    expiration__lt: str
    expiration__lte: str
    expiration__month: int
    expiration__year: int


class _NameFilters(TypedDict, total=False):
    """Common name filter fields for named resources."""

    name__icontains: str
    name__iendswith: str
    name__iexact: str
    name__istartswith: str


class _NameIdFilters(_IdFilters, _NameFilters, total=False):
    """Common name and id filter fields for classifier resources.

    ``/api/groups/`` is name-filterable but exposes no ``id`` filters, so it
    inherits :class:`_NameFilters` directly instead.
    """


class CorrespondentFilters(_NameIdFilters, total=False):
    """Filters for :attr:`PaperlessClient.correspondents`."""


class CustomFieldFilters(_NameIdFilters, total=False):
    """Filters for :attr:`PaperlessClient.custom_fields`."""


class DocumentFilters(_IdFilters, _CreatedFilters, total=False):
    """Filters for :attr:`PaperlessClient.documents`.

    These map 1-to-1 to the ``DocumentFilterSet`` in paperless-ngx.
    """

    added__date__gt: str
    added__date__gte: str
    added__date__lt: str
    added__date__lte: str
    added__day: int
    added__gt: str
    added__gte: str
    added__lt: str
    added__lte: str
    added__month: int
    added__year: int
    archive_serial_number: int
    archive_serial_number__gt: int
    archive_serial_number__gte: int
    archive_serial_number__isnull: bool
    archive_serial_number__lt: int
    archive_serial_number__lte: int
    checksum__icontains: str
    checksum__iendswith: str
    checksum__iexact: str
    checksum__istartswith: str
    content__icontains: str
    content__iendswith: str
    content__iexact: str
    content__istartswith: str
    correspondent__id: int
    correspondent__id__in: str
    correspondent__id__none: str  # comma-separated PKs to exclude
    correspondent__isnull: bool
    correspondent__name__icontains: str
    correspondent__name__iendswith: str
    correspondent__name__iexact: str
    correspondent__name__istartswith: str
    custom_field_query: str | CustomFieldQuery
    custom_fields__icontains: str
    custom_fields__id__all: str
    custom_fields__id__in: str
    custom_fields__id__none: str
    document_type__id: int
    document_type__id__in: str
    document_type__id__none: str
    document_type__isnull: bool
    document_type__name__icontains: str
    document_type__name__iendswith: str
    document_type__name__iexact: str
    document_type__name__istartswith: str
    has_custom_fields: bool
    is_in_inbox: bool  # True → document has an inbox tag
    is_tagged: bool  # True → document has at least one tag
    mime_type: str
    modified__date__gt: str
    modified__date__gte: str
    modified__date__lt: str
    modified__date__lte: str
    modified__day: int
    modified__gt: str
    modified__gte: str
    modified__lt: str
    modified__lte: str
    modified__month: int
    modified__year: int
    more_like_id: int  # semantic more-like-this search by document pk
    original_filename__icontains: str
    original_filename__iendswith: str
    original_filename__iexact: str
    original_filename__istartswith: str
    owner__id: int
    owner__id__in: str
    owner__id__none: str
    owner__isnull: bool
    query: str | SearchQuery
    search: str
    shared_by__id: int
    storage_path__id: int
    storage_path__id__in: str
    storage_path__id__none: str
    storage_path__isnull: bool
    storage_path__name__icontains: str
    storage_path__name__iendswith: str
    storage_path__name__iexact: str
    storage_path__name__istartswith: str
    tags__id: int
    tags__id__all: str  # document must have ALL listed tag ids
    tags__id__in: str
    tags__id__none: str  # document must have NONE of the listed tag ids
    tags__name__icontains: str
    tags__name__iendswith: str
    tags__name__iexact: str
    tags__name__istartswith: str
    text: str
    title__icontains: str
    title__iendswith: str
    title__iexact: str
    title__istartswith: str
    title_content: str  # searches title AND content simultaneously
    title_search: str


class DocumentTypeFilters(_NameIdFilters, total=False):
    """Filters for :attr:`PaperlessClient.document_types`."""


class GroupFilters(_NameFilters, total=False):
    """Filters for :attr:`PaperlessClient.groups`."""


class ProcessedMailFilters(TypedDict, total=False):
    """Filters for :attr:`PaperlessClient.processed_mail`."""

    rule: int  # must be an existing mail rule pk, the API rejects unknown ones with 400
    status: str  # free CharField upstream, values are upper-case: "SUCCESS", "FAILED", …


class ShareLinkFilters(_CreatedFilters, _ExpirationFilters, total=False):
    """Filters for :attr:`PaperlessClient.share_links`."""


class ShareLinkBundleFilters(_CreatedFilters, _ExpirationFilters, total=False):
    """Filters for :attr:`PaperlessClient.share_link_bundles`."""

    documents: int
    status: ShareLinkBundleStatus | str


class StoragePathFilters(_NameIdFilters, total=False):
    """Filters for :attr:`PaperlessClient.storage_paths`."""

    path__icontains: str
    path__iendswith: str
    path__iexact: str
    path__istartswith: str


class TagFilters(_NameIdFilters, total=False):
    """Filters for :attr:`PaperlessClient.tags`."""

    is_root: bool


class TaskFilters(TypedDict, total=False):
    """Filters for :attr:`PaperlessClient.tasks` and :meth:`TaskService.active`."""

    acknowledged: bool
    date_created_after: str
    date_created_before: str
    is_complete: bool
    name: str  # free-text over input filename, task type and trigger source labels
    owner: int
    result: str  # free-text over result reason, error message and document id
    status: TaskStatus | str | list[TaskStatus | str]
    task_id: str
    task_type: TaskType | str | list[TaskType | str]
    trigger_source: TaskTriggerSource | str | list[TaskTriggerSource | str]


class TaskSummaryFilters(TaskFilters, total=False):
    """Additional filters for :meth:`~pypaperless.services.tasks.TaskService.summary`."""

    days: int


class UserFilters(TypedDict, total=False):
    """Filters for :attr:`PaperlessClient.users`."""

    username__icontains: str
    username__iendswith: str
    username__iexact: str
    username__istartswith: str
