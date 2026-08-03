# Documents

`paperless.documents` provides the full feature set of the Paperless-ngx document API - in addition to the standard CRUD operations available on all resources.

---

## Fetching a document

```python
document = await paperless.documents(42)

print(document.id)
print(document.title)
print(document.correspondent)
print(document.document_type)
print(document.tags)
print(document.created)
print(document.content)
print(document.page_count)
print(document.mime_type)
print(document.archive_serial_number)
```

---

## Downloading file contents

Every document can be fetched in three modes: **download** (archived), **preview** and **thumbnail**. All return a `DownloadedDocument` instance.

```python
download = await paperless.documents.download(42)
preview = await paperless.documents.preview(42)
thumbnail = await paperless.documents.thumbnail(42)
```

`DownloadedDocument` gives you the raw bytes plus everything from the response headers you'd need to save or serve the file:

```python
# save to disk using the filename suggested by the API
with open(download.disposition_filename, "wb") as f:
    f.write(download.content)

print(download.content_type)  # e.g. "application/pdf"
print(download.disposition_type)  # "attachment" or "inline"
```

### Requesting the original file

By default, the archived (processed) version is returned. Pass `original=True` to get the original uploaded file:

```python
download = await paperless.documents.download(42, original=True)
```

---

## Searching documents

### Full-text search

```python
async for document in paperless.documents.search("type:invoice"):
    print(document.title, document.search_hit.score)
```

You can also pass the query as a keyword argument:

```python
async for document in paperless.documents.search(query="annual report"):
    ...
```

### Search hits

When a document was returned from a search, it carries a `DocumentSearchHit`. Use `has_search_hit` to branch on it, or the walrus operator to check and bind in one step:

```python
if document.has_search_hit:
    print(f"{document.title} matched the query")

if hit := document.search_hit:
    print(hit.score)
    print(hit.highlights)
    print(hit.note_highlights)
    print(hit.rank)
```

`search_hit` is `None` for documents fetched directly (e.g. `paperless.documents(42)`).

### Custom field query

For building expressions in a type-safe way, see [Custom field query](custom_field_query.md).

---

## More-like search

Find documents similar to a given document:

```python
async for document in paperless.documents.more_like(42):
    print(document.title)
```

---

## Metadata

```python
meta = await paperless.documents.metadata(42)
```

The returned `DocumentMeta` object includes embedded metadata from the file (e.g. EXIF or PDF metadata):

```python
for entry in meta.original_metadata:
    print(entry.namespace, entry.key, entry.value)
```

---

## Suggestions

Paperless-ngx can suggest classifiers (correspondent, document type, tags) for a document:

```python
suggestions = await paperless.documents.suggestions(42)

print(suggestions.correspondents)
print(suggestions.document_types)
print(suggestions.tags)
print(suggestions.storage_paths)
print(suggestions.dates)
```

These are the classifier's rule-based suggestions and resolve to existing object IDs.

### AI suggestions

`ai_suggestions()` is a separate endpoint backed by the LLM configured on the server
(`config.ai_enabled` must be on). Alongside ID lists it returns *names* for objects
that do not exist yet, so you can create them before assigning:

```python
ai = await paperless.documents.ai_suggestions(42)

print(ai.title)  # suggested document title
print(ai.tags)  # [1, 5]  - existing tag IDs
print(ai.suggested_tags)  # ["Insurance"] - names not yet in Paperless
print(ai.correspondents)
print(ai.suggested_correspondents)
print(ai.document_types, ai.suggested_document_types)
print(ai.storage_paths, ai.suggested_storage_paths)
print(ai.dates)

# or via a fetched document (pk bound automatically)
doc = await paperless.documents(42)
ai = await doc.ai_suggestions()
```

---

## Chat

`documents.chat` sends a natural-language question to the LLM configured on the
Paperless-ngx server. Pass a document pk as the second argument to scope the
question to a single document, or omit it for an unscoped query:

```python
response = await paperless.documents.chat("What is this invoice about?", 42)
print(response.q)  # "What is this invoice about?" - echoed by the server
print(response.document_id)  # 42

# unscoped
response = await paperless.documents.chat("Which contracts expire this year?")
```

!!! warning "The answer is streamed, not returned"
    Upstream this is a streaming endpoint, and its documented JSON response contains
    only the echoed `q` and `document_id` — which is exactly what `DocumentChat`
    exposes. `chat()` therefore confirms the query was accepted; it does **not**
    give you the generated answer text.

!!! note
    Requires AI to be enabled server-side, and `q` is capped at 4000 characters. Check
    `(await paperless.config()).ai_enabled` before relying on `chat` or `ai_suggestions`.

---

## Document versions

A document can hold several file versions. `documents.versions` uploads, relabels and
removes them; `documents.root` reports which document is the root of a version chain.

```python
# upload a new version of document 42
with open("invoice-v2.pdf", "rb") as fh:
    await paperless.documents.versions.upload(fh, version_label="v2", pk=42)

# relabel an existing version - returns the updated DocumentVersionInfo
info = await paperless.documents.versions.update(1, version_label="final", pk=42)
print(info.version_label, info.checksum, info.is_root)

# delete a version
await paperless.documents.versions.delete(1, pk=42)

# which document is the root of this chain?
root = await paperless.documents.root(42)
print(root.root_id)
```

Via a fetched document the pk is bound automatically, so `pk=` can be omitted:

```python
doc = await paperless.documents(42)

with open("invoice-v2.pdf", "rb") as fh:
    await doc.versions.upload(fh, version_label="v2")

await doc.versions.delete(1)
root = await doc.root()
```

!!! note
    `doc.versions` is not callable - it has no `__call__`, only `upload()`, `update()`
    and `delete()`. The version list the API embeds in a document response is parsed
    into `doc.versions_` (a `list[DocumentVersionInfo]`), and `doc.root_document` holds
    the root document's pk.

---

## Notes

Every document can have a list of notes attached to it. When a document is fetched
from the API the notes are already embedded in the response - calling `doc.notes()`
returns them immediately from an in-memory cache without a second HTTP request.

```python
doc = await paperless.documents(42)

notes = await doc.notes()  # served from cache, no HTTP request
for note in notes:
    print(note.id, note.note, note.created)
```

To force a fresh fetch from the API and refresh the cache, pass `force_request=True`:

```python
notes = await doc.notes(force_request=True)
```

The standalone service always requests the API:

```python
notes = await paperless.documents.notes(42)
```

### Adding a note

```python
# Pass the document pk as the first positional argument
draft = paperless.documents.notes.create(42, note="This needs review")
note_id = await paperless.documents.notes.save(draft)
```

Or via a fetched document (the document pk is bound automatically):

```python
doc = await paperless.documents(42)
draft = doc.notes.create(note="This needs review")
note_id = await doc.notes.save(draft)
```

After `save()` the cache is updated automatically - the next `doc.notes()` call
returns the latest state without an extra request.

### Deleting a note

```python
notes = await doc.notes()
await doc.notes.delete(notes[0])  # model instance
await doc.notes.delete(notes[0].id)  # integer shorthand (document pk implicit)

# standalone — supply the document pk explicitly
await paperless.documents.notes.delete(notes[0].id, pk=42)
```

After a successful delete the cache is updated in-place.

---

## Share links for a document

Every document can have share links attached to it. These are read-only from the document sub-service - to create or delete share links use `paperless.share_links`.

```python
# Fetch share links for a document
links = await paperless.documents.share_links(42)

# or via a fetched document
doc = await paperless.documents(42)
links = await doc.share_links()

for link in links:
    print(link.slug, link.expiration)
```

---

## Next available ASN

Request the next free archive serial number from Paperless-ngx:

```python
next_asn = await paperless.documents.get_next_asn()
print(f"Next ASN: {next_asn}")
```

---

## Updating & deleting a document

Modify fields on a fetched document and persist them with `update()`, or remove the document with `delete()`. Both can be called on the service directly or via the client-level dispatcher:

```python
doc = await paperless.documents(42)
doc.title = "Invoice 2024-01"
doc.correspondent = 3

# service
await paperless.documents.update(doc)
await paperless.documents.delete(doc)

# dispatcher — no need to reference the service explicitly
await paperless.update(doc)
await paperless.delete(doc)
```

See [Resources — Updating items](../resources.md#updating-items) and [Resources — Deleting items](../resources.md#deleting-items) for full options (`only_changed`, `silent_fail`).

---

## Uploading a document

Use `create()` to construct a document upload and `save()` to submit it. The document content must be provided as `bytes`. All fields except `document` are optional.

```python
with open("invoice.pdf", "rb") as f:
    content = f.read()

draft = paperless.documents.create(
    document=content,  # required - raw file bytes
    filename="invoice.pdf",  # original filename
    title="Invoice 2024-01",
    created=datetime.datetime(2024, 1, 15),
    correspondent=3,  # correspondent ID
    document_type=2,  # document type ID
    storage_path=1,  # storage path ID
    tags=[1, 5],  # tag IDs
    archive_serial_number=1042,
    custom_fields=[3, 8],  # custom field IDs (Paperless assigns null values)
)

task_id = await paperless.documents.save(draft)
print(f"Upload queued as task: {task_id}")
```

!!! note
    Unlike other resources, `save()` for documents returns a **task ID string**, not an integer ID. The document is processed asynchronously by Paperless-ngx. Use `paperless.tasks` to monitor the task.

### Skipping duplicates before upload

Paperless-ngx rejects duplicate files server-side, but the consume task only fails *after* the file has been transferred and queued. For large files, or when you upload from a bulk script, it is cheaper to check up-front. `find_duplicate()` hashes the bytes (MD5, as used by Paperless) and asks the server whether a document with that checksum already exists:

```python
with open("invoice.pdf", "rb") as f:
    content = f.read()

existing = await paperless.documents.find_duplicate(content, filename="invoice.pdf")
if existing is not None:
    print(f"Already uploaded as #{existing.id}: {existing.title}")
else:
    draft = paperless.documents.create(document=content, filename="invoice.pdf")
    await paperless.documents.save(draft)
```

`filename` is optional and, when given, additionally matches `original_filename` case-insensitively. The hash is computed in a worker thread so the event loop stays responsive on large files.

### Uploading with custom field values

To set explicit values on custom fields at upload time, build a
`DocumentCustomFieldList` via its `from_data()` factory (which binds the
runtime) and add `CustomFieldValue` entries:

```python
from pypaperless.models.documents import DocumentCustomFieldList
from pypaperless.models.custom_fields import CustomFieldValue

cf_list = DocumentCustomFieldList.from_data(paperless.runtime, [])
cf_list += CustomFieldValue(field=3, value="ACME Corp")
cf_list += CustomFieldValue(field=8, value=42)

draft = paperless.documents.create(document=content, custom_fields=cf_list)
```

See [Custom fields](custom_fields.md) for the full custom field API.

---

## Monitoring upload tasks

After uploading a document, use `paperless.tasks` to check the status:

```python
import asyncio
from pypaperless.models.tasks import TaskStatus

task_id = await paperless.documents.save(draft)

for _ in range(30):
    await asyncio.sleep(2)
    task = await paperless.tasks(task_id)
    if task.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE):
        break

print(task.status, task.result_data)
```

---

## Checking if a document is deleted

The `is_deleted` property returns `True` when the document is currently in the trash:

```python
doc = await paperless.documents(42)
print(doc.is_deleted)  # False for active documents

# Documents returned from paperless.trash also have this set
async for doc in paperless.trash:
    print(doc.id, doc.is_deleted, doc.deleted_at)
```

---

## Sending documents by e-mail

You can send one or more documents as attachments to one or more e-mail addresses:

```python
await paperless.documents.email(
    [23, 42],
    addresses="alice@example.com, bob@example.com",
    subject="Your requested documents",
    message="Please find the documents attached.",
)
```

A single document can also be passed as an integer:

```python
await paperless.documents.email(
    42,
    addresses="alice@example.com",
    subject="Invoice",
    message="See attachment.",
    use_archive_version=False,  # send original instead of archived version
)
```

| Parameter             | Default | Description                                 |
| --------------------- | ------- | ------------------------------------------- |
| `documents`           | -       | Document ID(s) to send                      |
| `addresses`           | -       | Comma-separated recipient e-mail addresses  |
| `subject`             | -       | E-mail subject                              |
| `message`             | -       | E-mail body text                            |
| `use_archive_version` | `True`  | Send archived version; `False` for original |

Raises `SendEmailError` if the Paperless server rejects the request.

---

## Audit history

Every change to a document is recorded as an audit-log entry. Use `document.history()` or the service directly to retrieve the full history of a document.

```python
# Via a fetched document (document pk is bound automatically)
doc = await paperless.documents(42)
entries = await doc.history()

for entry in entries:
    print(entry.timestamp, entry.action, entry.actor.username if entry.actor else "-")
    print(entry.changes)  # dict of changed fields

# Via the service, passing the document pk explicitly
entries = await paperless.documents.history(42)
```

---

## Bulk editing

`paperless.documents.bulk_edit` lets you apply operations to many documents at once in a single API call.

### Metadata

```python
await paperless.documents.bulk_edit.set_correspondent([1, 2, 3], 5)
await paperless.documents.bulk_edit.set_document_type([1, 2], 3)
await paperless.documents.bulk_edit.set_storage_path([1, 2], 4)

# clear correspondent
await paperless.documents.bulk_edit.set_correspondent([1, 2, 3], None)
```

### Tags

```python
await paperless.documents.bulk_edit.add_tag([1, 2, 3], 7)
await paperless.documents.bulk_edit.remove_tag([1, 2, 3], 7)

# Add and remove in one call
await paperless.documents.bulk_edit.modify_tags(
    [1, 2, 3],
    add_tags=[5, 6],
    remove_tags=[2],
)
```

### Custom fields

```python
await paperless.documents.bulk_edit.modify_custom_fields(
    [1, 2],
    add_custom_fields={3: "open"},  # {pk: value} or list of PKs
    remove_custom_fields=[4],
)
```

### Permissions

```python
from pypaperless.models.types import Permissions

await paperless.documents.bulk_edit.set_permissions(
    [1, 2, 3],
    owner=1,
    permissions=Permissions(view_users=[2, 3], change_users=[1]),
    merge=False,  # True merges with existing instead of replacing
)
```

### Document operations

```python
# Move to trash
await paperless.documents.bulk_edit.delete([10, 11, 12])

# Re-run OCR
await paperless.documents.bulk_edit.reprocess([1, 2, 3])

# Rotate pages
await paperless.documents.bulk_edit.rotate([1, 2], 90)

# Merge into a new single document
await paperless.documents.bulk_edit.merge(
    [10, 11, 12],
    metadata_document_id=10,  # whose metadata to use for the result
    delete_originals=True,  # move source documents to trash after merging
    archive_fallback=False,  # fall back to the archived file if no original exists
)
```

### PDF operations

`edit_pdf()` applies page-level operations to **one** document - the API accepts only a
single document per request. Each operation needs a `page` key; `rotate` and `doc` are
optional:

```python
await paperless.documents.bulk_edit.edit_pdf(
    42,
    operations=[{"page": 1, "rotate": 90}, {"page": 3}],
    delete_original=False,  # move the source document to trash afterwards
    update_document=False,  # True updates in place instead of creating a new document
    include_metadata=True,  # carry metadata over to the result
)
```

`split()` and `delete_pages()` are convenience wrappers around `edit_pdf()` - both take a
single document, like `edit_pdf()` itself:

```python
# two new documents: pages 1-2 and page 3
await paperless.documents.bulk_edit.split(
    42,
    [[1, 2], [3]],
    delete_originals=False,  # move the source document to trash afterwards
)

# drop pages 2 and 4, creating a new version of document 42
await paperless.documents.bulk_edit.delete_pages(42, [2, 4])
```

Two things worth knowing:

- The documents produced by `split()` inherit the source metadata **unchanged** - there is
  no `(split 1)`, `(split 2)`, … title suffix. Rename the results afterwards if you need it.
- The API keeps the pages it is handed rather than removing them, so `delete_pages()` needs
  the total page count and looks it up with one extra request. Pass `page_count=` when you
  already have the document, when its record carries no page count (not a PDF, or not
  processed yet), or when `source_mode` selects a file with a different number of pages.
- That count comes from an earlier request, so the pages to keep are a snapshot. If the
  document gains a version in between, the wrong pages survive - a shorter file is rejected
  by the server as out of bounds, but a longer one silently loses its extra pages. Passing
  `page_count=` does not close that window; it only skips the lookup, moving the staleness to
  your own read. The native, now-deprecated `delete_pages` bulk method avoided this by
  removing pages by index server-side.

Both raise `BulkEditPagesError` for input that cannot produce a valid PDF - no page groups, an
empty group, no pages to remove, page numbers outside the document, or removing every page.
It subclasses both `DocumentError` and `ValueError`, and the checks run before any request is
sent. See [Exceptions](../exceptions.md#bulkeditpageserror).

`remove_password()` decrypts password-protected PDFs:

```python
await paperless.documents.bulk_edit.remove_password(
    [5, 6],
    password="secret",
    update_document=True,
)
```

### Choosing the source file

`rotate()`, `merge()`, `edit_pdf()`, `split()`, `delete_pages()` and `remove_password()` all
accept `source_mode`, which selects the file the operation reads from - `"latest_version"`
(default) or `"explicit_selection"`:

```python
await paperless.documents.bulk_edit.rotate([1, 2], 90, source_mode="explicit_selection")
```

All bulk edit operations raise `BulkEditError` (a `ResponseError` subclass) when the API returns a non-OK result.
