# Code Patterns & Templates

All snippets below reflect the **current** code surface: `EndpointPath` (StrEnum) instead of an
`API_PATH` dict, `IdentifiedModel` (required `id: int`) as the base for API-identified read models,
`ResourceService` as the service base, `*Service` mixins, model-side `*Model` mixins,
`self._runtime.transport` for HTTP, `from_data(self._runtime, ...)`, and lazy `@cached_property`
registration on the client.

## Model Templates

### Standard paginated resource model

```python
# pypaperless/models/widgets.py
import datetime
from typing import ClassVar

from pypaperless.const import EndpointPath, PaperlessResource

from . import mixins
from .base import IdentifiedModel, PaperlessModel


class Widget(
    IdentifiedModel,  # provides a required, non-optional `id: int` — do not redeclare it
    mixins.SecurableModel,  # adds owner / user_can_change / permissions
):
    """Represent a Paperless `Widget`."""

    _api_path: ClassVar[str] = EndpointPath.WIDGETS_SINGLE
    _resource: ClassVar[PaperlessResource] = PaperlessResource.WIDGETS

    name: str | None = None
    created: datetime.datetime | None = None


class WidgetDraft(
    PaperlessModel,
    mixins.SecurableDraftModel,  # adds owner / set_permissions
    mixins.CreatableModel,  # adds serialize() + validate_draft()
):
    """Represent a new `Widget` not yet stored in Paperless."""

    _api_path: ClassVar[str] = EndpointPath.WIDGETS
    _resource: ClassVar[PaperlessResource] = PaperlessResource.WIDGETS

    _create_required_fields: ClassVar[set[str]] = {"name"}

    name: str | None = None
```

Do **not** list `owner` / `user_can_change` / `permissions` manually — `mixins.SecurableModel`
provides them (and `mixins.SecurableDraftModel` provides `owner` / `set_permissions` on the draft).
For resources with text-matching fields (`Correspondent`, `DocumentType`, `StoragePath`, `Tag`),
also mix in `mixins.MatchingFieldsModel`, which adds `match`, `matching_algorithm`
(`MatchingAlgorithm` enum), and `is_insensitive`.

### Sub-resource model (document-attached, flat list)

```python
import datetime
from typing import Any, ClassVar

from pydantic import Field

from pypaperless.const import EndpointPath

from .base import IdentifiedModel


class DocumentHistory(IdentifiedModel):
    """Represent a single Paperless document history (audit-log) entry."""

    _api_path: ClassVar[str] = EndpointPath.DOCUMENTS_HISTORY

    document: int | None = None  # injected by the service; not in the API payload
    timestamp: datetime.datetime | None = None
    action: DocumentHistoryAction | None = None
    changes: dict[str, Any] = Field(default_factory=dict)
    actor: DocumentHistoryActor | None = None
```

---

## Service Templates

Services reach the API through `self._runtime.transport`. `get` / `post` / `patch` / `put` parse
the JSON body and raise on error; `delete` returns `None` (raises on error, no body to parse).
Either way, no manual `raise_for_status()`.

### Full CRUD top-level service

```python
# pypaperless/services/widgets.py
from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.models.widgets import Widget, WidgetDraft

from . import mixins
from .base import ResourceService


class WidgetService(
    ResourceService,
    mixins.SecurableService,
    mixins.CallableService[Widget],
    mixins.CreatableService[WidgetDraft],
    mixins.IterableService[Widget],
    mixins.UpdatableService[Widget],
    mixins.DeletableService[Widget],
):
    """Represent a factory for Paperless `Widget` models."""

    _api_path = EndpointPath.WIDGETS
    _resource = PaperlessResource.WIDGETS

    _draft_cls = WidgetDraft
    _resource_cls = Widget
```

Add a typed `filter()` override only for resources that support server-side filtering (see the
`update-filters` skill for the exact pattern).

### Read-only top-level service (paginated, plus POST actions)

```python
from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.models.documents import Document

from . import mixins
from .base import ResourceService


class TrashService(ResourceService, mixins.IterableService[Document]):
    _api_path = EndpointPath.TRASH
    _resource = PaperlessResource.TRASH

    _resource_cls = Document

    async def restore(self, documents: list[int]) -> None:
        await self._runtime.transport.post(
            self._api_path, json={"action": "restore", "documents": documents}
        )

    async def empty(self, documents: list[int] | None = None) -> None:
        payload: dict = {"action": "empty"}
        if documents is not None:
            payload["documents"] = documents
        await self._runtime.transport.post(self._api_path, json=payload)
```

### Document sub-service (flat list, attached pk)

Inherit `DocumentScopedServiceBase` — it provides `__init__(runtime, attached_to=None)` and
`_get_document_pk()`; do **not** re-implement them.

```python
# pypaperless/services/documents/history.py
from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.models.documents.history import DocumentHistory

from .base import DocumentScopedServiceBase


class DocumentHistoryService(DocumentScopedServiceBase):
    """Represent a factory for Paperless `DocumentHistory` models."""

    _api_path = EndpointPath.DOCUMENTS_HISTORY
    _resource = PaperlessResource.DOCUMENTS

    _resource_cls = DocumentHistory

    async def __call__(self, pk: int | None = None) -> list[DocumentHistory]:
        doc_pk = self._get_document_pk(pk)
        res = await self._runtime.transport.get(self._api_path.format(pk=doc_pk))
        return [
            self._resource_cls.from_data(self._runtime, {**item, "document": doc_pk})
            for item in res
        ]
```

---

## Document Sub-service Wiring

Sub-services attached to a `Document` instance live in their own module to avoid circular imports.
Representative model/service files:

- `DocumentHistory`, `DocumentHistoryAction` — `from pypaperless.models import DocumentHistory, DocumentHistoryAction`
- `DocumentHistoryService` — `pypaperless/services/documents/history.py`
- `DocumentNote`, `DocumentNoteDraft` — `from pypaperless.models import DocumentNote, DocumentNoteDraft`
- `DocumentNoteService` — `pypaperless/services/documents/notes.py`
- `DocumentShareLinkService` — `pypaperless/services/documents/share_links.py`

### On the `Document` model (lazy init from the bound runtime)

```python
# In models/documents/document.py — top-level import (no circular dep because the service
# module does not import from models/documents/document.py):
from pypaperless.services.documents.history import DocumentHistoryService

# In the Document class body:
_history: DocumentHistoryService | None = PrivateAttr(default=None)


@property
def history(self) -> DocumentHistoryService:
    """Return the history service for this document."""
    if self._history is None:
        self._history = DocumentHistoryService(self._runtime, cast("int", self.id))
    return self._history
```

### On `DocumentService` (construct in `__init__`, expose via property)

```python
# In services/documents/document.py — import from the sub-service module:
from .history import DocumentHistoryService

# In DocumentService.__init__ (after super().__init__(runtime)):
self._history = DocumentHistoryService(runtime)


# Property on DocumentService:
@property
def history(self) -> DocumentHistoryService:
    return self._history
```

---

## Client Registration (top-level services)

Services are registered **lazily** on `PaperlessClient` as cached properties returning
`Service(self._runtime)` — never eagerly assigned in `__init__`.

```python
# pypaperless/client.py
from functools import cached_property
# dispatchable_cached_property is imported from .dispatch


@cached_property
def widgets(self) -> services.WidgetService:
    """Return the :class:`~pypaperless.services.WidgetService`."""
    return services.WidgetService(self._runtime)
```

Use `@dispatchable_cached_property` (instead of `@cached_property`) when the resource supports
`paperless.update(model)` / `paperless.delete(model)` — i.e. it uses `UpdatableService` /
`DeletableService`. That decorator registers the service with the `ModelDispatcher` so model-level
updates/deletes route back to it. Read-only or action-only services (e.g. `trash`) use plain
`@cached_property`.

---

## Test Fixture Shapes

### Paginated (`IterableService` resources)

```python
DATA_WIDGETS = {
    "count": 2,
    "next": None,
    "previous": None,
    "all": [1, 2],
    "results": [
        {"id": 1, "name": "Red Widget", ...},
        {"id": 2, "name": "Blue Widget", ...},
    ],
}
```

### Flat list (document sub-services)

```python
DATA_DOCUMENT_HISTORY = [
    {
        "id": 10,
        "timestamp": "2024-01-01T00:00:00Z",
        "action": "update",
        "changes": {},
        "actor": {"id": 1, "username": "admin"},
    },
    {
        "id": 1,
        "timestamp": "2023-01-01T00:00:00Z",
        "action": "create",
        "changes": {},
        "actor": {"id": 1, "username": "admin"},
    },
]
```

### Direct single object

```python
DATA_WIDGET_META = {
    "id": 42,
    "size_bytes": 1024,
    "checksum": "abc123",
}
```

---

## Audit EndpointSpec Examples

```python
ENDPOINTS = [
    # Paginated list endpoint
    EndpointSpec("Widget", "/api/widgets/?page_size=1", Widget, "paginated", "Widget"),
    # Single object
    EndpointSpec("Config", "/api/config/1/", Config, "direct", "ApplicationConfiguration"),
    # Flat list (use first element for field comparison)
    EndpointSpec(
        "DocumentNote", f"/api/documents/{TEST_DOC_ID}/notes/", DocumentNote, "list_index0", "Notes"
    ),
    # Reuses an existing model (e.g. Trash returns Document objects)
    EndpointSpec("Trash", "/api/trash/?page_size=1", Document, "paginated", "Document"),
]
```

### KNOWN_EXTRAS for injected fields

```python
KNOWN_EXTRAS["WidgetMeta"] = {
    "id": "injected by service from path parameter; not in API response",
}
KNOWN_SCHEMA_EXTRAS["WidgetMeta"] = {
    "id": "injected by service from path parameter; WidgetMeta schema has no 'id'",
}
```

---

## Mixin Reference

Service mixins (`pypaperless/services/mixins/`):

| Mixin                          | What it adds                                                             |
| ------------------------------ | ------------------------------------------------------------------------ |
| `mixins.CallableService[T]`    | `await service(pk)` — fetch a single item                                |
| `mixins.IterableService[T]`    | `async for item in service` + `.as_list()` + `.pages()` + `.filter()`    |
| `mixins.CreatableService[D]`   | `service.create(...)` (returns a draft) + `await service.save(draft)`    |
| `mixins.UpdatableService[T]`   | `await service.update(item)` (also reachable via `paperless.update`)     |
| `mixins.DeletableService[T]`   | `await service.delete(item)` (also reachable via `paperless.delete`)     |
| `mixins.SecurableService`      | adds `?full_perms=true` handling for permission-aware requests           |

Model mixins (`pypaperless/models/mixins/`):

| Mixin                          | What it adds                                                             |
| ------------------------------ | ------------------------------------------------------------------------ |
| `mixins.SecurableModel`        | `owner`, `user_can_change`, `permissions`                                |
| `mixins.SecurableDraftModel`   | `owner`, `set_permissions` (draft side)                                  |
| `mixins.CreatableModel`        | `serialize()` + `validate_draft()`; needs `_create_required_fields`      |
| `mixins.MatchingFieldsModel`   | `match`, `matching_algorithm` (`MatchingAlgorithm`), `is_insensitive`    |

Use only the mixins the endpoint actually supports.
