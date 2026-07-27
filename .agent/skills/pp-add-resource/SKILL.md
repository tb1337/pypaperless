---
name: pp-add-resource
description: "Add a new Paperless-ngx API resource to pypaperless. Use when implementing a new endpoint, service, model, or sub-service (e.g. /api/trash/, /api/documents/{id}/history/). Covers model definition, service class, const.py wiring, client registration, test fixtures, unit tests, script/pngx_audit_coverage.py, and script/pngx_smoketest.py."
argument-hint: "Name or path of the endpoint to implement (e.g. /api/trash/)"
---

# Add a New Resource to pypaperless

## When to Use

- Implementing a new top-level endpoint (e.g. `/api/trash/`)
- Implementing a document sub-service (e.g. `/api/documents/{id}/history/`)
- Any time a `/api/...` path is listed as "unimplemented" in `script/pngx_audit_coverage.py`

## Decision Tree

Before starting, answer these questions:

| Question                                                          | →                                                                                                     |
| ----------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Is it a sub-resource of `/api/documents/{id}/...`?                | → **Document sub-service** (see [Sub-service pattern](./references/patterns.md#document-sub-service-flat-list-attached-pk)) |
| Does GET return `{ count, next, previous, all, results }`?        | → **Paginated** (`IterableService`)                                                                   |
| Does GET return a flat list `[...]`?                              | → **Flat list** (direct `transport.get` + list comprehension)                                         |
| Does GET return a single object (not a list)?                     | → **Direct** (`CallableService` only, no `IterableService`)                                           |
| Does the endpoint have POST/action methods (e.g. restore, empty)? | → Add explicit `async def` methods calling `self._runtime.transport.post(...)`                        |

## Step-by-Step Procedure

### 1. Research the Endpoint

```bash
set -a && source .env && set +a
curl -s "$PYPAPERLESS_URL/api/<endpoint>/" \
  -H "Authorization: Token $PYPAPERLESS_TOKEN" | python3 -m json.tool | head -60
# Check OpenAPI schema component
uv run python -c "
import os, httpx, json
r = httpx.get(f\"{os.environ['PYPAPERLESS_URL']}/api/schema/?format=json\",
    headers={'Authorization': f\"Token {os.environ['PYPAPERLESS_TOKEN']}\"})
s = r.json()
# Replace 'ComponentName' with the schema component name
print(json.dumps(s['components']['schemas'].get('ComponentName', {}), indent=2))
"
```

### 2. `pypaperless/const.py`

Add an `EndpointPath` member (and a `_SINGLE` variant if the resource has detail routes) plus a
`PaperlessResource` enum value — both in alphabetical order:

```python
# EndpointPath (StrEnum) — list route + detail route
TRASH = "/api/trash/"
TRASH_SINGLE = "/api/trash/{pk}/"

# PaperlessResource enum
TRASH = "trash"
```

For document sub-services, add only an `EndpointPath` member with a `{pk}` placeholder (no new
`PaperlessResource` value needed):

```python
DOCUMENTS_HISTORY = "/api/documents/{pk}/history/"
```

### 3. Model (`pypaperless/models/<name>.py` or into `documents.py`)

See [model templates](./references/patterns.md#model-templates) for full code examples.

- The resource (read) model inherits `IdentifiedModel` (provides a required, non-optional `id: int` —
  do **not** redeclare `id`); the draft model inherits `PaperlessModel`. Add the mixins each side needs
  (`SecurableModel` / `MatchingFieldsModel` on the read model; `SecurableDraftModel` / `CreatableModel`
  on the draft)
- Set `_api_path: ClassVar[str] = EndpointPath.<MEMBER>` (and `_resource` for dispatched resources)
- All other fields `Optional` (use `| None = None`); `id` is the exception — inherited as a required `int`
- Use `datetime.datetime | None` for timestamps
- Use `StrEnum` subclasses for typed enum fields
- Export from `pypaperless/models/__init__.py`
- Re-export any public enum and filter types from `pypaperless/models/types.py`

**If reusing an existing model** (e.g. `Document` for `/api/trash/`): no new model needed.

### 4. Service (`pypaperless/services/<name>.py`)

See [service templates](./references/patterns.md#service-templates).

**Top-level paginated service:**

```python
class TrashService(ResourceService, mixins.IterableService[Document]):
    _api_path = EndpointPath.TRASH
    _resource = PaperlessResource.TRASH
    _resource_cls = Document
```

**Document sub-service (flat list):** inherit `DocumentScopedServiceBase`, which provides
`__init__(runtime, attached_to=None)` and `_get_document_pk()` — do not re-implement them:

```python
class DocumentHistoryService(DocumentScopedServiceBase):
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

**Action methods (POST):** `transport.post` already parses JSON and raises on error:

```python
async def restore(self, documents: list[int]) -> None:
    await self._runtime.transport.post(
        self._api_path, json={"action": "restore", "documents": documents}
    )
```

### 5. Wire Up

**`pypaperless/services/__init__.py`** — export the new service class.

**`pypaperless/client.py`** — register lazily on `PaperlessClient` as a cached property (never an
eager assignment in `__init__`):

```python
@cached_property
def trash(self) -> services.TrashService:
    """Return the :class:`~pypaperless.services.TrashService`."""
    return services.TrashService(self._runtime)
```

Use `@dispatchable_cached_property` instead when the resource supports `paperless.update()` /
`paperless.delete()` (i.e. it uses `UpdatableService` / `DeletableService`).

**For document sub-services** — construct in `DocumentService.__init__`, expose a property, and add
a lazy property on the `Document` model (see [sub-service wiring](./references/patterns.md#document-sub-service-wiring)).

### 6. Test Fixture (`tests/data/<name>.py`)

Create realistic snapshot data matching the actual API response shape:

- **Paginated**: wrap in `{ "count": N, "next": null, "previous": null, "all": [...], "results": [...] }`
- **Flat list**: plain `[{...}, ...]`
- **Direct**: single `{...}` dict

Export from `tests/data/__init__.py` (import + add to `__all__`).

### 7. Unit Tests

Add a `class Test<Name>:` — top-level resources go in `tests/test_resources.py`, document
sub-services in `tests/test_documents.py`:

- `test_iter` / `test_call` — test the main GET path via `httpx_mock`
- `test_<action>` — test each POST method
- For sub-services: also test via the parent `document.property()` and the `PrimaryKeyRequiredError` case

Pattern for mocking:

```python
httpx_mock.add_response(
    method="GET",
    url=f"{PAPERLESS_TEST_URL}{EndpointPath.TRASH}",  # or re.compile(...) for query params
    status_code=200,
    json=DATA_TRASH,
)
```

### 8. `script/pngx_audit_coverage.py`

Add an `EndpointSpec` to the `ENDPOINTS` list:

```python
ENDPOINTS = [
    ...,
    EndpointSpec("Trash", "/api/trash/?page_size=1", Document, "paginated", "Document"),
]
```

`unwrap` values:

- `"paginated"` — DRF paginated response
- `"direct"` — single object
- `"list_index0"` — flat list (use first element)

If the service injects fields not in the API response (e.g. `document` PK):

- Add to `KNOWN_EXTRAS["ModelName"]`
- Add to `KNOWN_SCHEMA_EXTRAS["ModelName"]`

### 9. Documentation (`docs/resources/<name>.md`)

Create a Markdown page under `docs/resources/` for the new resource:

- **Heading** — resource name (e.g. `# Trash`)
- **Short description** — one sentence about what this resource represents
- **Model table** — all fields with a brief description
- **Sub-model tables** — one table per nested model class (if any)
- **Usage examples** — `GET` (call / iterate), any `POST` actions (restore, update, …)

Follow the style of existing pages such as
`docs/resources/statistics.md` (direct call) or
`docs/resources/correspondents.md` (full CRUD).

In the **Model** section of the new page, always link both the model file and
[`pypaperless/models/types.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/types.py)
whenever the resource has enum or filter types re-exported there.

Then update **`docs/resources.md`**:

- Add the new resource to the **capability matrix** table (alphabetical order).
  Columns: `call`, `iterate`, `create`/`save`, `update`, `delete`, `permissions`.

Then register the new page in **`zensical.toml`** (the MkDocs nav):

- Add a `{ "Name" = "resources/<name>.md" }` entry inside the `"Resources"` nav list, in alphabetical order.

```toml
{ "Profile" = "resources/profile.md" },
{ "Trash"   = "resources/trash.md" },
```

### 10. `script/pngx_smoketest.py`

Add a test function before the relevant section and wire it into `main()`:

```python
async def test_trash(p: PaperlessClient) -> None:
    _hdr("Trash – list deleted documents")
    await check("trash.as_list()", p.trash.as_list(), detail_fn=lambda r: f"count={len(r)}")
```

### 11. Validate

```bash
# Unit tests
uv run pytest -x -q

# Linting
uv run ruff check pypaperless

# Live audit (requires running Paperless instance)
uv run python script/pngx_audit_coverage.py

# Live smoketest
uv run python script/pngx_smoketest.py
```

Expected: all unit tests pass, audit shows `<Name> → OK`, smoketest shows 0 failed.

## Checklist

- [ ] `const.py` — `EndpointPath` member(s) + `PaperlessResource`
- [ ] Model class with `_api_path`, typed fields, `StrEnum` for enums; public enum/filter types re-exported via `models/types.py`
- [ ] `models/__init__.py` — export
- [ ] Service class with correct mixins
- [ ] `services/__init__.py` — export
- [ ] `client.py` — register lazily on `PaperlessClient` (`@cached_property` / `@dispatchable_cached_property`)
- [ ] Test fixture in `tests/data/`
- [ ] `tests/data/__init__.py` — export
- [ ] Unit tests in `test_resources.py` (or `test_documents.py` for document sub-services)
- [ ] `script/pngx_audit_coverage.py` — `EndpointSpec` + any `KNOWN_EXTRAS`
- [ ] `docs/resources/<name>.md` — model table + usage examples
- [ ] `docs/resources.md` — capability matrix row
- [ ] `zensical.toml` — nav entry in alphabetical order
- [ ] `script/pngx_smoketest.py` — test function + wired in `main()`
- [ ] All tests green, lint clean

## Reference

- [Code patterns & templates](./references/patterns.md)
- Live Paperless dev credentials: git-ignored `.env` (`PYPAPERLESS_URL`, `PYPAPERLESS_TOKEN`,
  `PYPAPERLESS_TEST_DOC`); copy `.env.example` to `.env`. Scripts and `run/debug.py` read them via
  `script/_dev_env.py`.
