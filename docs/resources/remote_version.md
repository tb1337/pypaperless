# Remote Version

The `remote_version` resource reports the latest available version of Paperless-ngx as published on GitHub, along with whether an update is available relative to the running instance.

## Model

See [`pypaperless/models/remote_version.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/remote_version.py) for all fields and types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch

This is a parameter-free call - there is no primary key:

```python
rv = await paperless.remote_version()

print(rv.version)  # "2.13.5"
print(rv.update_available)  # True / False

if rv.update_available:
    print(f"Update available: {rv.version}")
```
