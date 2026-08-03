# Migrating from v5 to v6

## Python version requirement raised to 3.13

v6 drops support for **Python 3.12**. The minimum required version is now **Python 3.13**.

If you are still on Python 3.12, upgrade your runtime before updating pypaperless to v6.

---

v6 is also almost a full rewrite of pypaperless. Four things drove it:

- **Models were too tightly coupled to the HTTP layer.** In v5, every model instance carried a reference to the client and called it directly. That made testing awkward and sharing models between contexts impossible. v6 models are plain data - all I/O goes through services.
- **No runtime type safety.** v5 used dataclasses with manual dict conversion, so bad API responses would silently produce wrong values. v6 uses Pydantic v2, which validates every response at parse time.
- **`aiohttp` got removed.** `httpx` is modern, has a cleaner sync/async API and a built-in mock transport that makes testing easier.
- **Model-level CRUD shortcuts removed — replaced by a dispatcher.** `doc.update()`, `doc.delete()`, and `draft.save()` are gone. Instead, call the operations directly on the `PaperlessClient`; the dispatcher routes to the correct service automatically: `await paperless.update(model)`, `await paperless.delete(model)`, `await paperless.save(draft)`. See [CRUD](#crud).

---

## Quick checklist

| #   | What to change                                                                                                        | Section                                                                       |
| --- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 1   | Replace `aiohttp` / `yarl` with `httpx`                                                                               | [Dependencies](#dependencies)                                                 |
| 2   | Rename class `Paperless` → `PaperlessClient`; `PaperlessConfig` → `PaperlessSettings`                                 | [Initializing the client](#initializing-the-client)                           |
| 3   | Constructor changed: env-var mode → `PaperlessClient.from_env()`; config mode → `PaperlessClient.from_config(cfg)`    | [Initializing the client](#initializing-the-client)                           |
| 4   | `request_api_version` removed from constructor and `PaperlessSettings`                                                | [Initializing the client](#initializing-the-client)                           |
| 5   | Replace `reduce()` with `filter()` - different call pattern                                                           | [Iteration and filtering](#iteration-and-filtering)                           |
| 6   | `draft()` renamed to `create()`; model shortcuts `update()`, `delete()`, `save()` removed - use service or dispatcher | [CRUD](#crud)                                                                 |
| 7   | Replace `request_permissions = True` with `with_permissions()`                                                        | [Permissions](#permissions)                                                   |
| 8   | Rename `doc.get_download()`, `doc.get_metadata()`, etc. - shortcuts are back                                          | [Document convenience methods renamed](#document-convenience-methods-renamed) |
| 9   | Note deletion: `note.delete()` → service call                                                                         | [Document notes](#document-notes)                                             |
| 10  | `generate_api_token()` is now a module-level function, no longer a static class method                                | [Token generation](#token-generation)                                         |
| 11  | `Task` fields and enum values overhauled; `run()` signature changed; new `active()` and `summary()` methods           | [Changed resources](#changed-resources)                                       |
| 12  | New: `profile`, `trash`, `search`, `share_link_bundles`, `bulk_edit_objects`, six `documents.*` sub-services          | [New resources](#new-resources)                                               |
| 13  | Rename four `Paperless`-prefixed exception classes; new `DeletionError`, `DispatchError`                              | [Error handling](#error-handling)                                             |
| 14  | HTTP error statuses now raise typed exceptions: 404 → `NotFoundError`, other non-2xx → `UnexpectedStatusError`        | [Error handling](#http-error-statuses-raise-typed-exceptions)                 |

---

## Dependencies

Replace `aiohttp` and `yarl` with `httpx`:

=== "v5"
    ```toml
    dependencies = ["aiohttp", "yarl", "pypaperless"]
    ```

=== "v6"
    ```toml
    dependencies = ["httpx", "pypaperless"]
    ```

---

## Initializing the client

### Class renamed

The client class and settings class were renamed:

| v5                | v6                  |
| ----------------- | ------------------- |
| `Paperless`       | `PaperlessClient`   |
| `PaperlessConfig` | `PaperlessSettings` |

Update all imports and type annotations accordingly.

### Constructor signature changed

In v5, the constructor accepted `url`, `token`, and `request_api_version`. In v6 the constructor only accepts `url`, `token`, and `client`. Environment-variable and config-object modes are now explicit factory class methods.

=== "v5"
    ```python
    import aiohttp

    paperless = Paperless("http://localhost:8000", "mytoken")
    paperless = Paperless("http://localhost:8000", "mytoken", session=my_session)
    paperless = Paperless("http://localhost:8000", "mytoken", request_args={"ssl": False})
    ```

=== "v6"
    ```python
    import httpx
    from pypaperless import PaperlessClient

    paperless = PaperlessClient("http://localhost:8000", "mytoken")
    paperless = PaperlessClient("http://localhost:8000", "mytoken", client=my_httpx_client)
    ```

!!! tip "SSL / TLS customization"
    Pass a pre-configured `httpx.AsyncClient` to control TLS behaviour:
    ```python
    client = httpx.AsyncClient(verify=False)  # or verify="/path/to/cert.pem"
    paperless = PaperlessClient("http://localhost:8000", "mytoken", client=client)
    ```

The `url` parameter no longer accepts `yarl.URL` objects - pass a plain string.

### `PaperlessSettings` and factory class methods

v6 exposes `PaperlessSettings` (backed by `pydantic-settings`) and two factory class methods.

**Config object** - useful when you want to construct or validate settings in one place:

=== "v5"
    ```python
    from pypaperless import Paperless, PaperlessConfig

    cfg = PaperlessConfig(url="http://localhost:8000", token="mytoken")
    paperless = Paperless(config=cfg)
    ```

=== "v6"
    ```python
    from pypaperless import PaperlessClient, PaperlessSettings

    cfg = PaperlessSettings(url="http://localhost:8000", token="mytoken")
    paperless = PaperlessClient.from_config(cfg)
    ```

**Environment variables** - use the `from_env()` factory; `PaperlessSettings` reads the values automatically:

=== "v5"
    ```python
    paperless = Paperless()  # zero-arg constructor read env vars
    ```

=== "v6"
    ```python
    paperless = PaperlessClient.from_env()
    ```

| Environment variable | Maps to                           |
| -------------------- | --------------------------------- |
| `PYPAPERLESS_URL`    | URL of the Paperless-ngx instance |
| `PYPAPERLESS_TOKEN`  | API token                         |

!!! note
    `PYPAPERLESS_REQUEST_API_VERSION` was removed. API version is now negotiated
    automatically from the server's `x-api-version` response header.

---

## Token generation

`generate_api_token()` is now a **module-level function** importable from `pypaperless`, no longer a static method on `PaperlessClient`. The optional custom-client argument was also renamed from `session` to `client`.

=== "v5"
    ```python
    token = await Paperless.generate_api_token(url, username, password, session=my_session)
    ```

=== "v6"
    ```python
    from pypaperless import generate_api_token

    token = await generate_api_token(url, username, password, client=my_client)
    ```

---

## Iteration and filtering

`reduce()` was replaced by `filter()`. The key difference: the context manager now **yields the service object**, so you iterate over `ctx` instead of reusing the outer service name.

=== "v5"
    ```python
    async with paperless.documents.reduce(title__icontains="invoice"):
        async for doc in paperless.documents:
            print(doc.title)
    ```

=== "v6"
    ```python
    async with paperless.documents.filter(title__icontains="invoice") as ctx:
        async for doc in ctx:
            print(doc.title)
    ```

`pages()` is available and returns enhanced `Page` objects with `.items`, `.current_page`, `.last_page`, and more.

=== "v5"
    ```python
    async for page in paperless.documents.pages(page_size=25):
        for doc in page:
            print(doc.title)
    ```

=== "v6"
    ```python
    async for page in paperless.documents.pages(page_size=25):
        print(f"Page {page.current_page} of {page.last_page}")
        for doc in page:
            print(doc.title)
    ```

You can also use the convenience helpers:

```python
docs = await paperless.documents.as_list()
dmap = await paperless.documents.as_dict()  # {pk: Document}
```

!!! note "Removed in API v10"
    `all()` — which returned a flat list of primary keys — was removed together with
    the `all` field in paginated API responses (Paperless-ngx API v10+).
    To get a list of primary keys, use `as_list()` and extract `.id`:

    ```python
    ids = [doc.id for doc in await paperless.documents.as_list()]
    ```

---

## CRUD

In v5, CRUD operations lived on model instances. v6 moves the canonical API to
the **service** level. Model-level shortcuts (`doc.update()`, `doc.delete()`, `draft.save()`) have been removed.

!!! tip "New in v6: client-level dispatcher"
    Instead of calling the operation on a specific service, you can call it directly on
    the `PaperlessClient` instance. The **dispatcher** automatically routes to the correct
    service based on the model type — no need to know which service owns the model:

    ```python
    doc = await paperless.documents(42)
    doc.title = "New Title"
    await paperless.update(doc)  # routes to DocumentService.update()

    await paperless.delete(doc)  # routes to DocumentService.delete()

    draft = paperless.tags.create(name="urgent")
    pk = await paperless.save(draft)  # routes to TagService.save()
    ```

    This works for all dispatchable resources: documents, document notes, correspondents,
    document types, storage paths, tags, share links, share link bundles, and custom fields.

v6 provides two equivalent ways to perform CRUD:

- **Service-level** — call the operation on the service that owns the model type.
- **Client-level dispatcher** — call `await paperless.update(model)` /
  `await paperless.delete(model)` / `await paperless.save(draft)` directly on
  the client; the dispatcher resolves the responsible service automatically.

!!! tip "`id` is no longer optional"
    Resource models fetched from the API now type their `id` as a required
    `int` instead of `int | None`. Guards like `if doc.id is not None` are
    dead code in v6, and expressions such as `my_dict[doc.id]` type-check
    without casts.

### update()

=== "v5"
    ```python
    doc = await paperless.documents(42)
    doc.title = "New Title"
    await doc.update()
    ```

=== "v6 (service)"
    ```python
    doc = await paperless.documents(42)
    doc.title = "New Title"
    await paperless.documents.update(doc)
    ```

=== "v6 (dispatcher)"
    ```python
    doc = await paperless.documents(42)
    doc.title = "New Title"
    await paperless.update(doc)  # resolves to DocumentService automatically
    ```

!!! warning "Assignments are validated"
    In v6, assigning a value to a model field validates (and coerces) it
    immediately - invalid values raise a `pydantic.ValidationError` at the
    assignment site instead of failing later inside `update()` with a server
    error:

    ```python
    doc.created = "2024-08-13"  # coerced to datetime.date(2024, 8, 13)
    doc.created = "not a date"  # ValidationError - right here
    ```

### delete()

`delete()` no longer returns a boolean. It raises `DeletionError` on failure
(or swallows it when `silent_fail=True`).

=== "v5"
    ```python
    doc = await paperless.documents(42)
    await doc.delete()
    ```

=== "v6 (service)"
    ```python
    doc = await paperless.documents(42)
    await paperless.documents.delete(doc)
    # raises DeletionError on failure
    ```

=== "v6 (dispatcher)"
    ```python
    doc = await paperless.documents(42)
    await paperless.delete(doc)
    ```

This applies to every resource - correspondents, tags, custom fields, etc.

### save() / create()

`draft()` was renamed to `create()`. The model-level `draft.save()` shortcut was
removed; use the service or the dispatcher instead.

=== "v5"
    ```python
    draft = paperless.documents.draft(document=raw_bytes, title="Invoice")
    task_id = await draft.save()
    ```

=== "v6 (service)"
    ```python
    draft = paperless.documents.create(document=raw_bytes, title="Invoice")
    task_id = await paperless.documents.save(draft)
    ```

=== "v6 (dispatcher)"
    ```python
    draft = paperless.documents.create(document=raw_bytes, title="Invoice")
    task_id = await paperless.save(draft)
    ```

For all other resources (correspondents, tags, …):

=== "v5"
    ```python
    draft = paperless.tags.draft(name="urgent")
    pk = await draft.save()
    ```

=== "v6 (service)"
    ```python
    draft = paperless.tags.create(name="urgent")
    pk = await paperless.tags.save(draft)
    ```

=== "v6 (dispatcher)"
    ```python
    draft = paperless.tags.create(name="urgent")
    pk = await paperless.save(draft)
    ```

!!! warning "Draft models reject unknown fields"
    In v6, `create()` raises a `pydantic.ValidationError` for unknown keyword
    arguments instead of silently dropping them:

    ```python
    paperless.tags.create(tag_name="urgent")  # field is called "name"
    # ValidationError: Extra inputs are not permitted
    ```

    v5 ignored such typos, which usually surfaced much later as a confusing
    "missing field" error - or not at all.

---

## Permissions

The mutable `request_permissions` setter was replaced by a `with_permissions()` context manager. The flag is now automatically reset on exit.

=== "v5"
    ```python
    paperless.documents.request_permissions = True
    doc = await paperless.documents(42)
    print(doc.owner, doc.permissions)
    paperless.documents.request_permissions = False
    ```

=== "v6"
    ```python
    async with paperless.documents.with_permissions() as ctx:
        doc = await ctx(42)
        print(doc.owner, doc.permissions)
        async for doc in ctx:
            print(doc.owner, doc.permissions)
    ```

!!! note
    Unlike v5, `with_permissions()` resets it automatically on exit, even if an exception occurs.

---

## Document convenience methods renamed

The `get_*` shortcut methods that existed in v5 on `Document` instances are **fully removed** in v6.
All file and metadata access now goes through the service:

| v5 (on model instance)                  | v6                                                          |
| --------------------------------------- | ----------------------------------------------------------- |
| `await doc.get_download()`              | `await paperless.documents.download(doc.id)`                |
| `await doc.get_download(original=True)` | `await paperless.documents.download(doc.id, original=True)` |
| `await doc.get_preview()`               | `await paperless.documents.preview(doc.id)`                 |
| `await doc.get_thumbnail()`             | `await paperless.documents.thumbnail(doc.id)`               |
| `await doc.get_metadata()`              | `await paperless.documents.metadata(doc.id)`                |
| `await doc.get_suggestions()`           | `await paperless.documents.suggestions(doc.id)`             |
| *(not available)*                       | `async for d in paperless.documents.more_like(doc.id):`     |
| *(not available)*                       | `await paperless.documents.email(doc.id, ...)`              |

**Sub-service shortcuts** remain available via bound sub-service properties on the
`Document` instance - six of them in v6:

| Access                       | Equivalent                                         |
| ---------------------------- | -------------------------------------------------- |
| `await doc.notes()`          | `await paperless.documents.notes(doc.id)`          |
| `await doc.history()`        | `await paperless.documents.history(doc.id)`        |
| `await doc.share_links()`    | `await paperless.documents.share_links(doc.id)`    |
| `await doc.ai_suggestions()` | `await paperless.documents.ai_suggestions(doc.id)` |
| `await doc.root()`           | `await paperless.documents.root(doc.id)`           |
| `doc.versions.upload(f)`     | `paperless.documents.versions.upload(f, pk=doc.id)` |

---

## Document notes

Note deletion moved from the model to the service, consistent with the general CRUD pattern. The model-level `note.delete()` shortcut was removed.

=== "v5"
    ```python
    notes = await paperless.documents.notes(42)
    for note in notes:
        await note.delete()
    ```

=== "v6"
    ```python
    notes = await paperless.documents.notes(42)
    for note in notes:
        await paperless.documents.notes.delete(note)
    ```

The `doc.notes` property on `Document` instances still exposes a bound `DocumentNoteService`:

Creating a new note:

=== "v5"
    ```python
    draft = paperless.documents.notes.draft(note="Checked.", document=42)
    note_id, doc_id = await draft.save()
    ```

=== "v6"
    ```python
    doc = await paperless.documents(42)
    draft = doc.notes.create(note="Checked.")
    note_id = await doc.notes.save(draft)
    ```

!!! note
    When using `doc.notes`, the document pk is bound automatically - no need to pass `document=` to `create()`.

=== "v6 (service)"
    ```python
    draft = paperless.documents.notes.create(42, note="Checked.")
    note_id = await paperless.documents.notes.save(draft)
    ```

!!! note
    `save()` now returns only the new note `id` as `int`. In v5 it returned a `(note_id, doc_id)` tuple.

---

## Changed resources

### `paperless.tasks`

The `Task` model was significantly overhauled for Paperless-ngx API v10. The `type` field was renamed to `task_type`, and `task_name`, `task_file_name`, and `result` were removed. The single `related_document` integer was replaced by `related_document_ids` (a list of integers). New fields include `task_type_display`, `trigger_source`, `trigger_source_display`, `status_display`, `date_started`, `duration_seconds`, `wait_time_seconds`, `input_data`, and `result_data`.

The `TaskType` enum values changed entirely — the old high-level categories (`AUTO`, `SCHEDULED`, `MANUAL`) are gone and replaced with specific task-type names such as `CONSUME_FILE`, `SANITY_CHECK`, `MAIL_FETCH`, and others. The `TaskStatus` values changed from uppercase strings to lowercase; the `RECEIVED` and `RETRY` statuses were removed. A new `TaskTriggerSource` enum was introduced to express how a task was initiated (e.g. `API_UPLOAD`, `FOLDER_CONSUME`, `EMAIL_CONSUME`).

#### `filter()` is now a context manager

Consistent with the general `filter()` change [described above](#iteration-and-filtering), `tasks.filter()` now returns a context manager:

=== "v5"
    ```python
    async for task in paperless.tasks.filter(status="SUCCESS", acknowledged=False):
        print(task.task_id)
    ```

=== "v6"
    ```python
    async with paperless.tasks.filter(status=["success"], acknowledged=False) as ctx:
        async for task in ctx:
            print(task.task_id)
    ```

#### `run()` changed signature and return type

In v5, `run()` accepted a Celery UUID and returned a `Task`. In v6 it accepts a `TaskType` (or plain string) and schedules a fresh background task, returning the new Celery UUID as a string:

=== "v5"
    ```python
    rerun = await paperless.tasks.run("a1b2c3d4-...")
    print(rerun.status)  # returned a Task
    ```

=== "v6"
    ```python
    from pypaperless.models.tasks import TaskType

    task_uuid = await paperless.tasks.run(TaskType.SANITY_CHECK)  # returns str UUID
    task = await paperless.tasks(task_uuid)
    ```

#### New methods

Two new service methods were added:

- `active()` — iterates over currently pending and running tasks (capped at 50 server-side).
- `summary()` — returns a list of `TaskSummary` objects with aggregated statistics (counts, durations, last run) per task type, optionally scoped to a rolling time window via the `days` parameter.

```python
async for task in paperless.tasks.active():
    print(task.task_id, task.status)

summaries = await paperless.tasks.summary(days=7)
for s in summaries:
    print(s.task_type, s.success_count, s.failure_count)
```

---

## New resources

Five new top-level services were added - `profile`, `trash`, `search`,
`share_link_bundles` and `bulk_edit_objects` - plus six new document
sub-services: `history`, `bulk_edit`, `chat`, `ai_suggestions`, `versions`
and `root`.

### `paperless.profile`

Access the currently authenticated user's own profile:

```python
profile = await paperless.profile()
print(profile.first_name, profile.email)
```

See [Profile](resources/profile.md) for details.

### `paperless.trash`

Browse and manage soft-deleted documents:

```python
async for doc in paperless.trash:
    print(doc.id, doc.title, doc.deleted_at)

await paperless.trash.restore([42, 43])
await paperless.trash.empty()
```

The `Document.is_deleted` property returns `True` for documents retrieved from the trash.

See [Trash](resources/trash.md) for details.

### `paperless.search`

Query the global search endpoint, which matches across documents, tags,
correspondents, document types and more in a single call:

```python
from pypaperless.models.types import SearchQuery as Q

result = await paperless.search(Q("invoice") & Q.field("tag", "unpaid"))
print(result.total)
for doc in result.documents or []:
    print(doc.title)
```

See [Search](resources/search.md) and [Search Query](concepts/search_query.md) for details.

### `paperless.share_link_bundles`

Group several documents into one shareable archive. Supports full CRUD plus a
`rebuild()` action:

```python
from pypaperless.models.types import ShareLinkFileVersion

draft = paperless.share_link_bundles.create(
    document_ids=[42, 43],
    file_version=ShareLinkFileVersion.ARCHIVE,
)
bundle_id = int(await paperless.share_link_bundles.save(draft))
bundle = await paperless.share_link_bundles.rebuild(bundle_id)
print(bundle.status)
```

See [Share Link Bundles](resources/share_link_bundles.md) for details.

!!! note
    `paperless.share_links` itself is **not** new - it already existed in v5 with
    full CRUD. Only the v6 CRUD call pattern changed, as described under
    [CRUD](#crud).

### `paperless.documents.history`

A new document audit-log sub-service:

```python
entries = await paperless.documents.history(42)
for entry in entries:
    print(entry.actor, entry.timestamp, entry.action)
```

### `paperless.documents.bulk_edit`

A new sub-service for performing bulk operations across many documents in a single
API call. All operations accept a list of document primary keys.

```python
# Assign metadata to multiple documents at once
await paperless.documents.bulk_edit.set_correspondent([1, 2, 3], 5)
await paperless.documents.bulk_edit.set_document_type([1, 2], 3)
await paperless.documents.bulk_edit.set_storage_path([1, 2], 4)

# Tag operations
await paperless.documents.bulk_edit.add_tag([1, 2, 3], 7)
await paperless.documents.bulk_edit.remove_tag([1, 2, 3], 7)
await paperless.documents.bulk_edit.modify_tags([1, 2], add_tags=[5], remove_tags=[2])

# Custom fields
await paperless.documents.bulk_edit.modify_custom_fields(
    [1, 2],
    add_custom_fields={3: "open"},
    remove_custom_fields=[4],
)

# Permissions
from pypaperless.models.types import Permissions

await paperless.documents.bulk_edit.set_permissions(
    [1, 2, 3],
    owner=1,
    permissions=Permissions(view_users=[2, 3], change_users=[1]),
)

# Document operations
await paperless.documents.bulk_edit.delete([10, 11])  # move to trash
await paperless.documents.bulk_edit.reprocess([1, 2, 3])  # re-run OCR
await paperless.documents.bulk_edit.rotate([1, 2], 90)
await paperless.documents.bulk_edit.merge(
    [10, 11, 12],
    metadata_document_id=10,
    delete_originals=True,
)

# PDF page operations and password removal
await paperless.documents.bulk_edit.edit_pdf(42, [{"page": 1, "rotate": 90}])
await paperless.documents.bulk_edit.split(42, [[1, 2], [3]])
await paperless.documents.bulk_edit.delete_pages(42, [2, 4])
await paperless.documents.bulk_edit.remove_password([5, 6], password="secret")
```

Raises `BulkEditError` (a `ResponseError` subclass) when the API returns a non-OK
result.

### `paperless.documents.chat`

An LLM-backed chat query, optionally scoped to one document. Requires AI to be
enabled on the Paperless-ngx side (`config.ai_enabled`):

```python
response = await paperless.documents.chat("What is this invoice about?", 42)
print(response.q)
```

Note that the answer itself is streamed server-side — the parsed response only echoes
the query. See [Chat](concepts/documents.md#chat).

### `paperless.documents.ai_suggestions`

AI-generated classifier suggestions, distinct from the rule-based
`documents.suggestions`:

```python
result = await paperless.documents.ai_suggestions(42)
print(result.title, result.suggested_tags, result.suggested_correspondents)
```

### `paperless.documents.versions` and `paperless.documents.root`

Documents can now carry multiple file versions:

```python
with open("updated.pdf", "rb") as fh:
    await paperless.documents.versions.upload(fh, version_label="v2", pk=42)

await paperless.documents.versions.update(1, version_label="final", pk=42)
await paperless.documents.versions.delete(1, pk=42)

root = await paperless.documents.root(42)
print(root.root_id)
```

See the [Documents concept page](concepts/documents.md#document-versions) for details.

### `paperless.bulk_edit_objects`

A new top-level service for setting permissions or deleting multiple non-document
objects - tags, correspondents, document types, or storage paths - in a single call.

```python
from pypaperless.models.types import Permissions

# Set permissions on several tags
await paperless.bulk_edit_objects.set_permissions(
    "tags",
    [1, 2, 3],
    owner=1,
    permissions=Permissions(view_users=[2], change_users=[1]),
)

# Permanently delete correspondents
await paperless.bulk_edit_objects.delete("correspondents", [4, 5])
```

Transport-level failures raise the standard errors (e.g. `JsonResponseWithError`
for an HTTP 400, `UnexpectedStatusError` for other non-2xx responses); unlike
`paperless.documents.bulk_edit`, this service does not raise `BulkEditError`.
See [Bulk Edit Objects](resources/bulk_edit_objects.md) for details.

---

## Custom field values

`DocumentCustomFieldList` is now a pydantic `RootModel` and the typed value
classes (`CustomFieldBooleanValue`, `CustomFieldDateValue`, …) are resolved
through a discriminated union on `data_type`. The container API (`add`,
`remove`, `get`, `default`, `in`, iteration, `+=`/`-=`) is unchanged. Three
internals moved:

- `CUSTOM_FIELD_TYPE_VALUE_MAP` was removed - use `isinstance()` checks against
  the typed value classes, or the `AnyCustomFieldValue` union from
  `pypaperless.models.types`.
- The `.data` property (raw payload) was removed - the validated items live in
  `.root`, or just iterate the container.
- `model_dump()` of a `CustomFieldValue` now emits only `field` and `value` -
  `name`, `data_type`, and `extra_data` are client-side metadata and are
  excluded from serialization.

---

## Error handling

`PaperlessConnectionError` is now raised for every transport-level failure (connection refused, DNS failure, broken connection mid-response) rather than `aiohttp.ClientConnectorError`. Timeouts raise the more specific `PaperlessTimeoutError`, a subclass of `PaperlessConnectionError`. If you catch library-specific exceptions, update accordingly:

=== "v5"
    ```python
    except aiohttp.ClientConnectorError:
        ...
    ```

=== "v6"
    ```python
    except PaperlessTimeoutError:
        ...  # host alive but slow - consider retrying
    except PaperlessConnectionError:
        ...  # host not reachable
    ```

!!! tip
    `PaperlessConnectionError` works in both v5 and v6 - catching it is the most forward-compatible option. In v6 no `httpx` exception ever leaks through, so catching `httpx.ConnectError` or `httpx.ReadTimeout` is unnecessary.

### HTTP error statuses raise typed exceptions

In v5, requests failing with an HTTP error status leaked the HTTP library's own
exception (`aiohttp.ClientResponseError`). v6 translates every non-2xx response
into a pypaperless exception, so you never need to catch `httpx` exceptions:

| Status                   | v6 exception                                   |
| ------------------------ | ---------------------------------------------- |
| 400 (with JSON body)     | `JsonResponseWithError`                        |
| 401                      | `InvalidTokenError` / `InactiveOrDeletedError` |
| 403                      | `ForbiddenError`                               |
| 404                      | `NotFoundError`                                |
| any other non-2xx status | `UnexpectedStatusError`                        |

`NotFoundError` and `UnexpectedStatusError` expose the original `httpx.Response`
via their `response` attribute.

=== "v5"
    ```python
    import aiohttp

    try:
        doc = await paperless.documents(999999)
    except aiohttp.ClientResponseError as exc:
        if exc.status == 404:
            print("Document does not exist.")
    ```

=== "v6"
    ```python
    from pypaperless.exceptions import NotFoundError

    try:
        doc = await paperless.documents(999999)
    except NotFoundError:
        print("Document does not exist.")
    ```

### Exception renames

Four exception classes lost their `Paperless` prefix to follow standard Python naming conventions. `PaperlessConnectionError` is the only exception kept as-is, because it would otherwise shadow Python's built-in `ConnectionError`.

| v5                                | v6                       |
| --------------------------------- | ------------------------ |
| `PaperlessAuthError`              | `AuthError`              |
| `PaperlessInvalidTokenError`      | `InvalidTokenError`      |
| `PaperlessInactiveOrDeletedError` | `InactiveOrDeletedError` |
| `PaperlessForbiddenError`         | `ForbiddenError`         |

=== "v5"
    ```python
    from pypaperless.exceptions import PaperlessAuthError, PaperlessForbiddenError

    except PaperlessAuthError:
        ...
    except PaperlessForbiddenError:
        ...
    ```

=== "v6"
    ```python
    from pypaperless.exceptions import AuthError, ForbiddenError

    except AuthError:
        ...
    except ForbiddenError:
        ...
    ```

### New exception base classes

v6 introduces intermediate base classes that you can use to catch whole groups of related errors:

| Class                 | Catches                                                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------------------------- |
| `InitializationError` | All session/transport errors (unchanged from v5)                                                           |
| `ResponseError`       | `BadJsonResponseError`, `JsonResponseWithError`, `NotFoundError`, `UnexpectedStatusError`, `BulkEditError` |
| `DraftError`          | `DraftFieldRequiredError`, `DraftNotSupportedError`                                                        |
| `ResourceError`       | `DeletionError`, `ItemNotFoundError`, `PrimaryKeyRequiredError`, `TaskNotFoundError`                       |
| `DocumentError`       | `AsnRequestError`, `SendEmailError`                                                                        |

### New exceptions

| Exception               | When raised                                                              |
| ----------------------- | ------------------------------------------------------------------------ |
| `DeletionError`         | `delete()` call receives a non-2xx HTTP response                         |
| `DispatchError`         | `update()` / `delete()` / `save()` called on an unregistered model type  |
| `NotFoundError`         | The requested resource does not exist (HTTP 404)                         |
| `UnexpectedStatusError` | The API responds with an unhandled non-2xx status code (e.g. 5xx errors) |
