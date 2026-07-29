# Resources

Every Paperless-ngx entity is exposed through a **service** on the `PaperlessClient` instance. Each service supports a consistent set of operations - fetch, iterate, create, update or delete.

---

## Capability matrix

| Resource            | `call` | `iterate` | `create`/`save` | `update` | `delete` | `permissions` |
| ------------------- | :----: | :-------: | :-------------: | :------: | :------: | :-----------: |
| `bulk_edit_objects` |        |           |                 |          |          |               |
| `config`            |   ✓    |           |                 |          |          |               |
| `correspondents`    |   ✓    |     ✓     |        ✓        |    ✓     |    ✓     |       ✓       |
| `custom_fields`     |   ✓    |     ✓     |        ✓        |    ✓     |    ✓     |               |
| `documents`         |   ✓    |     ✓     |        ✓        |    ✓     |    ✓     |       ✓       |
| `document_types`    |   ✓    |     ✓     |        ✓        |    ✓     |    ✓     |       ✓       |
| `groups`            |   ✓    |     ✓     |                 |          |          |               |
| `mail_accounts`     |   ✓    |     ✓     |                 |          |          |       ✓       |
| `mail_rules`        |   ✓    |     ✓     |                 |          |          |       ✓       |
| `processed_mail`    |   ✓    |     ✓     |                 |          |          |     owner     |
| `profile`           |   ✓    |           |                 |    ✓     |          |               |
| `saved_views`       |   ✓    |     ✓     |                 |          |          |       ✓       |
| `share_link_bundles`|   ✓    |     ✓     |        ✓        |    ✓     |    ✓     |               |
| `share_links`       |   ✓    |     ✓     |        ✓        |    ✓     |    ✓     |               |
| `statistics`        |   ✓    |           |                 |          |          |               |
| `remote_version`    |   ✓    |           |                 |          |          |               |
| `status`            |   ✓    |           |                 |          |          |               |
| `storage_paths`     |   ✓    |     ✓     |        ✓        |    ✓     |    ✓     |       ✓       |
| `tags`              |   ✓    |     ✓     |        ✓        |    ✓     |    ✓     |       ✓       |
| `tasks`             |   ✓    |     ✓     |                 |          |          |               |
| `trash`             |        |     ✓     |                 |          |          |               |
| `users`             |   ✓    |     ✓     |                 |          |          |               |
| `workflows`         |   ✓    |     ✓     |                 |          |          |               |

!!! note "Bulk-action services"
    `bulk_edit_objects` exposes bulk `set_permissions` and `delete` for tags,
    correspondents, document types and storage paths. `documents.bulk_edit` exposes
    bulk operations (set metadata, tags, custom fields, permissions, delete, reprocess,
    rotate, merge, edit PDF pages, remove PDF passwords) for documents. Neither service
    follows the standard CRUD pattern above.
    See [Bulk Edit Objects](resources/bulk_edit_objects.md) and the
    [Documents concept page](concepts/documents.md#bulk-editing) for details.

!!! note "`permissions` column"
    A ✓ means the resource model carries the full `owner` / `user_can_change` /
    `permissions` set and the service offers `with_permissions()`. `processed_mail`
    is the one exception: it carries `owner` only, with no permission table.

---

## Fetching a single item

Call the service with a primary key to retrieve one item:

```python
document = await paperless.documents(42)
correspondent = await paperless.correspondents(7)
tag = await paperless.tags(3)
```

### Lazy loading

Pass `lazy=True` to create a model instance without making any HTTP request. Useful when you only need the primary key reference:

```python
doc = await paperless.documents(42, lazy=True)
# doc.id == 42, but no data was fetched
```

---

## Iterating over all items

Use `async for` to iterate over every item in a resource. pypaperless handles pagination automatically:

```python
async for correspondent in paperless.correspondents:
    print(correspondent.id, correspondent.name)

async for tag in paperless.tags:
    print(tag.name, tag.color)
```

### Pagination

You can iterate page-by-page instead of item-by-item. `Page` objects provide metadata about the current page:

```python
async for page in paperless.documents.pages():
    print(f"Page {page.current_page} of {page.last_page} ({page.count} total)")
    for doc in page:
        print(doc.title)
```

Control the starting page and page size:

```python
async for page in paperless.documents.pages(page=3, page_size=25):
    ...
```

---

## Filtering with `filter()`

`filter()` is an async context manager that applies server-side filters to iteration.
Filter keys are fully type-checked - your IDE will autocomplete available parameters
and flag unknown keys.

Each service exposes its own typed filter set (e.g. `DocumentFilters`, `TagFilters`).
Import them from `pypaperless.models.filters` to construct the dict separately:

```python
from pypaperless.models.filters import DocumentFilters

filters: DocumentFilters = {
    "correspondent__id": 3,
    "title__icontains": "invoice",
}

async with paperless.documents.filter(**filters) as ctx:
    async for document in ctx:
        ...
```

You can also pass filters directly as keyword arguments:

```python
async with paperless.documents.filter(title__icontains="invoice") as ctx:
    async for document in ctx:
        print(document.title)
```

The filter context is automatically cleared when the `async with` block exits.
Filters are task-local - concurrent asyncio tasks filtering the same service
do not interfere with each other.

!!! note "Resources without a typed filter set"
    `saved_views`, `mail_accounts`, `mail_rules`, `trash` and `workflows`
    (including `workflows.triggers` and `workflows.actions`) have no filter
    TypedDict of their own, so `filter()` accepts no keys there. Iterate them
    directly and narrow the result client-side.

    For `trash` that is a server-side limitation rather than a gap: `/api/trash/`
    declares no query parameters and silently returns the full trash when
    filters are passed.

---

## Creating items

Use `create()` to construct a new draft model and `save()` to persist it:

```python
from pypaperless.models.types import MatchingAlgorithm

# Create a new tag
draft = paperless.tags.create(
    name="important",
    color="#ff0000",
    is_inbox_tag=False,
    match="",
    matching_algorithm=MatchingAlgorithm.AUTO,
    is_insensitive=True,
)
new_id = await paperless.tags.save(draft)
print(f"Created tag with id {new_id}")
```

```python
# Create a new correspondent
draft = paperless.correspondents.create(
    name="ACME Corp",
    match="",
    matching_algorithm=MatchingAlgorithm.AUTO,
    is_insensitive=True,
)
new_id = await paperless.correspondents.save(draft)
```

You can also save via the client-level dispatcher — no need to know which service owns the draft:

```python
new_id = await paperless.save(draft)
```

!!! note
    `save()` returns the integer `id` of the created resource for most resource types, or a `task_id` string when uploading a document.

For required fields, see the model reference in the source code. If required fields are missing, `DraftFieldRequiredError` is raised.

---

## Updating items

Modify fields on a fetched model and call `update()`:

```python
tag = await paperless.tags(3)
tag.name = "urgent"
tag.color = "#ff0000"

updated = await paperless.tags.update(tag)
print(f"Updated: {updated}")  # True if any field changed
```

`update()` returns `True` if any field was changed and sent to the API, `False` if no fields differed from the stored state. The model is refreshed in-place after a successful update.

By default, only changed fields are sent via `PATCH`. Pass `only_changed=False` to replace all fields via `PUT`:

```python
await paperless.tags.update(tag, only_changed=False)
```

You can also update via the client-level dispatcher:

```python
await paperless.update(tag)
```

---

## Deleting items

```python
tag = await paperless.tags(3)
await paperless.tags.delete(tag)
```

`delete()` raises `DeletionError` when the deletion fails. To silently ignore a
failed deletion, pass `silent_fail=True`:

```python
await paperless.tags.delete(tag, silent_fail=True)
```

You can also delete via the client-level dispatcher:

```python
await paperless.delete(tag)
```

---

## Model fields: matching & algorithms

Resources like `Correspondent`, `Tag`, `DocumentType` and `StoragePath` include matching fields inherited from `MatchingFieldsModel`:

| Field                | Description                |
| -------------------- | -------------------------- |
| `match`              | The matching pattern       |
| `matching_algorithm` | How the pattern is applied |
| `is_insensitive`     | Case-insensitive matching  |

**`MatchingAlgorithm` values:**

| Value         | Meaning                       |
| ------------- | ----------------------------- |
| `NONE` (0)    | No automatic matching         |
| `ANY` (1)     | Match any word                |
| `ALL` (2)     | Match all words               |
| `LITERAL` (3) | Exact literal match           |
| `REGEX` (4)   | Regular expression            |
| `FUZZY` (5)   | Fuzzy matching                |
| `AUTO` (6)    | Automatic (Paperless decides) |
