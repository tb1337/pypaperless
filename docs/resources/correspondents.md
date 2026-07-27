# Correspondents

Correspondents represent the senders or recipients that Paperless-ngx associates with documents. They support the full CRUD lifecycle and permission management.

## Models

See [`pypaperless/models/correspondents.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/correspondents.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
correspondent = await paperless.correspondents(7)
print(correspondent.name)  # "ACME Corp"
print(correspondent.document_count)  # 42
```

## Iterate

```python
async for c in paperless.correspondents:
    print(c.id, c.name)

# Collect everything into a list
all_correspondents = await paperless.correspondents.as_list()

# Fetch only a subset matching a filter
filtered = [c async for c in paperless.correspondents if c.document_count and c.document_count > 0]
```

## Create

`save()` calls `validate_draft()` first — all of `name`, `match`, `matching_algorithm`
and `is_insensitive` are required and raise `DraftFieldRequiredError` if missing.

```python
from pypaperless.models.types import MatchingAlgorithm

draft = paperless.correspondents.create(
    name="ACME Corp",
    match="",
    matching_algorithm=MatchingAlgorithm.AUTO,
    is_insensitive=True,
)

pk = await paperless.correspondents.save(draft)
print(pk)  # primary key of the new correspondent
```

## Update

```python
c = await paperless.correspondents(7)
c.name = "ACME Corp (renamed)"

changed = await paperless.correspondents.update(c)
# True  → server accepted the change
# False → nothing was sent (no fields actually changed)
```

Pass `only_changed=False` to force a full `PUT` instead of a `PATCH`:

```python
await paperless.correspondents.update(c, only_changed=False)
```

## Delete

```python
c = await paperless.correspondents(7)
await paperless.correspondents.delete(c)
```

Raises `DeletionError` on failure. Pass `silent_fail=True` to suppress it.

## Permissions

```python
async with paperless.correspondents.with_permissions():
    c = await paperless.correspondents(7)
    print(c.owner)  # owner user id
    print(c.permissions)  # Permissions
```

See [Permissions](../concepts/permissions.md) for details on reading and modifying permission sets.
