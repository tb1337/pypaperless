# Users

Users are the Paperless-ngx user accounts. They are read-only from the API perspective - only fetching and iterating is supported.

## Model

See [`pypaperless/models/permissions/users.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/permissions/users.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
user = await paperless.users(1)
print(user.username)  # "admin"
print(user.is_active)  # True
print(user.groups)  # [2, 5]
```

## Iterate

```python
async for user in paperless.users:
    print(user.id, user.username, user.email)

# Find all superusers
admins = [u async for u in paperless.users if u.is_superuser]
```
