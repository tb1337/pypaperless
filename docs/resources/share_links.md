# Share Links

Share links create publicly accessible URLs for individual documents without requiring authentication. They support the full CRUD lifecycle.

## Models

See [`pypaperless/models/share_links/share_link.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/share_links/share_link.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
link = await paperless.share_links(8)
print(link.slug)  # "abc123xyz"
print(link.document)  # 42
print(link.expiration)  # datetime(2024, 12, 31, ...) or None
```

## Iterate

```python
async for link in paperless.share_links:
    print(link.id, link.document, link.slug)

# Find links for a specific document
doc_links = [lnk async for lnk in paperless.share_links if lnk.document == 42]
```

## Create

`save()` calls `validate_draft()` first — `document` and `file_version` are required.

```python
import datetime
from pypaperless.models.share_links import ShareLinkFileVersion

draft = paperless.share_links.create(
    document=42,
    file_version=ShareLinkFileVersion.ARCHIVE,
    expiration=datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
)

new_id = await paperless.share_links.save(draft)
print(new_id)  # primary key of the new share link

# fetch the freshly created link to read its generated slug
link = await paperless.share_links(new_id)
print(link.slug)  # e.g. "abc123xyz"
```

## Update

```python
import datetime

link = await paperless.share_links(8)
link.expiration = datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)
changed = await paperless.share_links.update(link)
```

## Delete

```python
link = await paperless.share_links(8)
await paperless.share_links.delete(link)
```

Raises `DeletionError` on failure. Pass `silent_fail=True` to suppress it.
