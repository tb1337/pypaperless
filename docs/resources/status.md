# Status

The `status` resource reports the health of the Paperless-ngx server - database connectivity, storage availability, background task workers, and the ML classifier. It is a parameter-free singleton call.

## Model

See [`pypaperless/models/status.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/status.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch

No primary key - call without arguments:

```python
status = await paperless.status()

print(status.pngx_version)  # "2.13.5"
print(status.server_os)  # "Linux"

# Check storage
if storage := status.storage:
    gb_free = storage.available / 1024**3
    print(f"{gb_free:.1f} GB free")

# Check database health
if database := status.database:
    print(database.status)  # "OK"

# Check background workers
if tasks := status.tasks:
    print(tasks.celery_status)  # "OK"
    print(tasks.redis_status)  # "OK"

# Convenience property for any errors present
if status.has_errors:
    print("One or more components are unhealthy!")
```
