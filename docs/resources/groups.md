# Groups

Groups are Paperless-ngx user groups used for permission management. They are read-only from the API perspective - groups can only be fetched and iterated, not created or modified via pypaperless.

## Model

See [`pypaperless/models/permissions/groups.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/permissions/groups.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
group = await paperless.groups(2)
print(group.name)  # "Administrators"
print(group.permissions)  # ["view_document", "change_document", ...]
```

## Iterate

```python
async for group in paperless.groups:
    print(group.id, group.name)

# Keyed by id
groups = await paperless.groups.as_dict()
```
