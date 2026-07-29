# Storage Paths

Storage paths define directory templates that control where Paperless-ngx stores archived documents on disk. They support the full CRUD lifecycle and permission management.

## Models

See [`pypaperless/models/storage_paths.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/storage_paths.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
sp = await paperless.storage_paths(2)
print(sp.name)  # "By year"
print(sp.path)  # "{created_year}/{correspondent}/{title}"
```

## Iterate

```python
async for sp in paperless.storage_paths:
    print(sp.id, sp.name, sp.path)

# Keyed by id
paths = await paperless.storage_paths.as_dict()
```

## Create

`save()` calls `validate_draft()` first — all of `name`, `path`, `match`,
`matching_algorithm` and `is_insensitive` are required and raise
`DraftFieldRequiredError` if missing.

```python
from pypaperless.models.types import MatchingAlgorithm

draft = paperless.storage_paths.create(
    name="By year and type",
    path="{created_year}/{document_type}/{title}",
    match="",
    matching_algorithm=MatchingAlgorithm.AUTO,
    is_insensitive=True,
)

pk = await paperless.storage_paths.save(draft)
print(pk)  # primary key of the new storage path
```

## Update

```python
sp = await paperless.storage_paths(2)
sp.path = "{created_year}/{correspondent}/{title}"
changed = await paperless.storage_paths.update(sp)
```

## Delete

```python
sp = await paperless.storage_paths(2)
await paperless.storage_paths.delete(sp)
```

Raises `DeletionError` on failure. Pass `silent_fail=True` to suppress it.

## Permissions

```python
async with paperless.storage_paths.with_permissions():
    sp = await paperless.storage_paths(2)
    print(sp.owner)  # owner user id
    print(sp.permissions)  # Permissions
```

See [Permissions](../concepts/permissions.md) for details.
