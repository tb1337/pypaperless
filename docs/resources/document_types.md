# Document Types

Document types classify documents into categories (e.g. *Invoice*, *Contract*, *Receipt*). They support the full CRUD lifecycle and permission management.

## Models

See [`pypaperless/models/document_types.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/document_types.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
document_type = await paperless.document_types(4)
print(document_type.name)  # "Invoice"
print(document_type.document_count)  # 17
```

## Iterate

```python
async for dt in paperless.document_types:
    print(dt.id, dt.name)

# Keyed by id
types = await paperless.document_types.as_dict()
```

## Create

`save()` calls `validate_draft()` first — all of `name`, `match`, `matching_algorithm`
and `is_insensitive` are required and raise `DraftFieldRequiredError` if missing.

```python
from pypaperless.models.types import MatchingAlgorithm

draft = paperless.document_types.create(
    name="Invoice",
    match="",
    matching_algorithm=MatchingAlgorithm.AUTO,
    is_insensitive=True,
)

pk = await paperless.document_types.save(draft)
print(pk)  # primary key of the new document type
```

## Update

```python
dt = await paperless.document_types(4)
dt.name = "Invoice (updated)"
changed = await paperless.document_types.update(dt)
```

## Delete

```python
dt = await paperless.document_types(4)
await paperless.document_types.delete(dt)
```

Raises `DeletionError` on failure. Pass `silent_fail=True` to suppress it.

## Permissions

```python
async with paperless.document_types.with_permissions():
    dt = await paperless.document_types(4)
    print(dt.owner)  # owner user id
    print(dt.permissions)  # Permissions
```

See [Permissions](../concepts/permissions.md) for details on reading and modifying permission sets.
