# Documents

Documents are the core resource in Paperless-ngx. This page shows the essential CRUD examples. For the full feature set - downloading, searching, notes, next ASN, email, and upload - see the dedicated [Documents](../concepts/documents.md) page.

## Models

See [`pypaperless/models/documents/document.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/documents/document.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
doc = await paperless.documents(42)
print(doc.title)
print(doc.created_date)  # datetime.date
```

## Iterate

```python
async for doc in paperless.documents:
    print(doc.id, doc.title)

# All documents in memory
all_docs = await paperless.documents.as_list()
```

## Create (upload)

To upload a new document, use `create()` + `save()`. The raw file content (`bytes`) is a required draft field - pass it as `document=` to `create()` (or assign it to `draft.document`) before saving:

```python
with open("invoice.pdf", "rb") as fh:
    raw = fh.read()

draft = paperless.documents.create(document=raw)
draft.title = "Invoice 2024"
draft.correspondent = 7
draft.tags = [1, 3]

task_id = await paperless.documents.save(draft)
```

`save()` returns a `str` task UUID. Monitor progress via `paperless.tasks`.

## Update

```python
doc = await paperless.documents(42)
doc.title = "Updated title"
doc.tags = [1, 2, 5]
changed = await paperless.documents.update(doc)
```

## Delete

```python
doc = await paperless.documents(42)
await paperless.documents.delete(doc)
```

Raises `DeletionError` on failure. Pass `silent_fail=True` to suppress it.

## Document sub-service shortcuts

The `Document` model exposes six **bound sub-services** as properties -
`notes`, `history`, `share_links`, `ai_suggestions`, `root` and `versions`.
These are the same services reachable from `paperless.documents`, but with the
document's primary key pre-filled:

```python
doc = await paperless.documents(42)

# notes: cache-first by default, force_request=True to re-fetch from API
notes = await doc.notes()  # from cache (no HTTP request)
notes = await doc.notes(force_request=True)  # fresh from API
note_draft = doc.notes.create(note="Checked.")
note_id = await doc.notes.save(note_draft)
await doc.notes.delete(notes[0])  # model instance
await doc.notes.delete(notes[0].id)  # integer shorthand (document pk implicit)

# history (read-only)
entries = await doc.history()  # list[DocumentHistory]

# share links (read-only from here, use paperless.share_links to create/delete)
links = await doc.share_links()  # list[ShareLink]

# AI suggestions (read-only)
ai = await doc.ai_suggestions()  # DocumentAISuggestions

# root document record (read-only)
root = await doc.root()  # DocumentRoot

# versions: upload / relabel / delete a document's file versions (not callable)
with open("updated.pdf", "rb") as fh:
    await doc.versions.upload(fh, version_label="v2")
info = await doc.versions.update(1, version_label="final")  # DocumentVersionInfo
await doc.versions.delete(1)
```

See [Documents — AI suggestions](../concepts/documents.md#ai-suggestions) and
[Document versions](../concepts/documents.md#document-versions) for the full
signatures.

All other operations (download, preview, thumbnail, metadata, suggestions, more-like,
email, chat) are **service-only** — there are no model-level shortcuts for these:

```python
downloaded = await paperless.documents.download(doc.id)
preview = await paperless.documents.preview(doc.id)
thumbnail = await paperless.documents.thumbnail(doc.id)
meta = await paperless.documents.metadata(doc.id)
suggestions = await paperless.documents.suggestions(doc.id)
async for similar in paperless.documents.more_like(doc.id):
    print(similar.title)
await paperless.documents.email(doc.id, addresses="alice@example.com", subject="Fwd", message="")
answer = await paperless.documents.chat("What is this about?", doc.id)
```

## Permissions

```python
async with paperless.documents.with_permissions():
    doc = await paperless.documents(42)
    print(doc.owner)  # owner user id
    print(doc.permissions)  # Permissions
```

---

!!! note
    For downloading, searching, note management, and more, see [Documents](../concepts/documents.md).
    To filter documents by custom field values, see [Custom Field Query](../concepts/custom_field_query.md).
