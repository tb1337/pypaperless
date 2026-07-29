# Trash

The `trash` resource exposes documents that have been soft-deleted in Paperless-ngx. Trashed documents can be restored or permanently deleted. The service iterates over `Document` objects just like the main `documents` service.

## Model

Trashed documents use the same `Document` model - see [`pypaperless/models/documents/document.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/documents/document.py) and [`pypaperless/models/types.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/types.py) for enum and filter types. In the trash context, `deleted_at` is additionally populated with the timestamp when the document was moved to the trash.

## Iterate

```python
async for doc in paperless.trash:
    print(doc.id, doc.title, doc.deleted_at)

# Collect all trashed documents as a list
trashed = await paperless.trash.as_list()
print(f"{len(trashed)} document(s) in trash")
```

## Filter

`/api/trash/` declares no query filters. `filter()` therefore only accepts the pagination
parameters, and passing document filters has no effect — the endpoint silently returns the
full trash:

```python
# Only page / page_size are honoured here
async with paperless.trash.filter(page_size=25) as ctx:
    async for doc in ctx:
        print(doc.id, doc.title)
```

Narrow the result set client-side instead:

```python
trashed = await paperless.trash.as_list()
invoices = [doc for doc in trashed if "invoice" in (doc.title or "").lower()]
```

## Restore

Restore one or more documents back to the document archive:

```python
await paperless.trash.restore([42, 43])
```

## Empty

Permanently delete documents from the trash. Pass a list of IDs to delete specific documents, or call without arguments to empty the entire trash:

```python
# Delete specific documents permanently
await paperless.trash.empty([42, 43])

# Empty the entire trash
await paperless.trash.empty()
```

!!! warning
    `empty()` permanently destroys documents. This action cannot be undone.
