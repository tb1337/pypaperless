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
)
```

All bulk edit operations raise `BulkEditError` (a `ResponseError` subclass) when the API returns a non-OK result.
