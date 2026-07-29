# Tags

Tags are labels that can be applied to documents for classification and filtering. They support the full CRUD lifecycle and permission management.

## Models

See [`pypaperless/models/tags.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/tags.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
tag = await paperless.tags(5)
print(tag.name)  # "Invoice"
print(tag.color)  # "#a6cee3"
print(tag.document_count)  # 38
```

## Iterate

```python
async for tag in paperless.tags:
    print(tag.id, tag.name, tag.color)

# Find the inbox tag
inbox = next(
    (t async for t in paperless.tags if t.is_inbox_tag),
    None,
)
```

## Tag hierarchy

Tags can be nested. `parent` holds the parent tag's id (`None` for a top-level tag) and
`children` holds the nested tags as full `Tag` instances:

```python
tag = await paperless.tags(5)
print(tag.parent)  # 2, or None for a root tag

for child in tag.children or []:
    print(child.id, child.name)
```

Use the `is_root` filter to iterate only top-level tags:

```python
async with paperless.tags.filter(is_root=True) as ctx:
    async for tag in ctx:
        print(tag.name, len(tag.children or []))
```

Assign a parent when creating a tag by passing `parent=` to `create()`.

## Create

`save()` calls `validate_draft()` first — all of `name`, `color`, `is_inbox_tag`,
`match`, `matching_algorithm` and `is_insensitive` are required and raise
`DraftFieldRequiredError` if missing. `parent` and `text_color` are optional.

```python
from pypaperless.models.types import MatchingAlgorithm

draft = paperless.tags.create(
    name="Invoice",
    color="#a6cee3",
    is_inbox_tag=False,
    match="",
    matching_algorithm=MatchingAlgorithm.AUTO,
    is_insensitive=True,
)

pk = await paperless.tags.save(draft)
print(pk)  # primary key of the new tag
```

## Update

```python
tag = await paperless.tags(5)
tag.color = "#ff0000"
changed = await paperless.tags.update(tag)
```

## Delete

```python
tag = await paperless.tags(5)
await paperless.tags.delete(tag)
```

Raises `DeletionError` on failure. Pass `silent_fail=True` to suppress it.

## Permissions

```python
async with paperless.tags.with_permissions():
    tag = await paperless.tags(5)
    print(tag.owner)  # owner user id
    print(tag.permissions)  # Permissions
```

See [Permissions](../concepts/permissions.md) for details.
