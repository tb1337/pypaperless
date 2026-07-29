# Profile

The `profile` resource exposes the Paperless-ngx user profile for the currently authenticated token. It is a parameter-free singleton call and supports partial updates via `update()`.

## Model

See [`pypaperless/models/profile.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/profile.py) for all fields and types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch

No primary key - call without arguments:

```python
profile = await paperless.profile()

print(profile.email)  # "admin@example.com"
print(profile.first_name)  # "Admin"
print(profile.auth_token)  # "3e9505078d32d8ad4ecea00fa0eec8e426622b52"
print(profile.has_usable_password)  # True
print(profile.is_mfa_enabled)  # False

for account in profile.social_accounts or []:
    print(account.provider, account.name)
```

## Update

Use `update()` to partially update the profile. Only the supplied keyword arguments are sent to the API:

```python
updated = await paperless.profile.update(
    first_name="Jane",
    last_name="Doe",
    email="jane@example.com",
)

print(updated.first_name)  # "Jane"
```

`update()` returns a refreshed `Profile` instance reflecting the server response.
