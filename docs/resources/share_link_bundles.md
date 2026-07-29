# Share Link Bundles

Share link bundles group multiple documents into a single shareable archive. They support the full CRUD lifecycle plus a `rebuild` action.

## Models

See [`pypaperless/models/share_links/bundle.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/share_links/bundle.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
bundle = await paperless.share_link_bundles(3)
print(bundle.slug)  # "xyz789abc"
print(bundle.status)  # ShareLinkBundleStatus.READY
print(bundle.documents)  # [42, 43]
print(bundle.size_bytes)  # 204800
```

## Iterate

```python
async for bundle in paperless.share_link_bundles:
    print(bundle.id, bundle.status, bundle.documents)
```

## Create

`save()` calls `validate_draft()` first — only `document_ids` is required.
`file_version` and `expiration_days` are optional:

```python
from pypaperless.models.share_links import ShareLinkFileVersion

draft = paperless.share_link_bundles.create(
    document_ids=[42, 43],
    file_version=ShareLinkFileVersion.ARCHIVE,
    expiration_days=7,
)
bundle_id = int(await paperless.share_link_bundles.save(draft))
print(bundle_id)  # 3
```

!!! note
    The draft takes `document_ids` and `expiration_days`, while the created
    `ShareLinkBundle` exposes `documents` and an absolute `expiration` timestamp.

## Rebuild

Trigger a rebuild of an existing bundle (e.g. after documents change):

```python
updated = await paperless.share_link_bundles.rebuild(3)
print(updated.status)  # ShareLinkBundleStatus.PENDING
```

## Update

```python
import datetime

bundle = await paperless.share_link_bundles(3)
bundle.expiration = datetime.datetime(2026, 6, 1, tzinfo=datetime.timezone.utc)
changed = await paperless.share_link_bundles.update(bundle)
```

## Delete

```python
bundle = await paperless.share_link_bundles(3)
await paperless.share_link_bundles.delete(bundle)
```

Raises `DeletionError` on failure. Pass `silent_fail=True` to suppress it.

## Filter

```python
async with paperless.share_link_bundles.filter(status="ready") as ctx:
    async for bundle in ctx:
        print(bundle.id, bundle.size_bytes)
```
