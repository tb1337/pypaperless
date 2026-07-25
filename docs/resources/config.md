# Config

The `config` resource exposes the Paperless-ngx application configuration. It is a single-item resource - the instance is always fetched with primary key `1`.

## Model

See [`pypaperless/models/config.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/config.py) for all fields and types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch

Config is a singleton — call without arguments:

```python
config = await paperless.config()

print(config.language)          # e.g. "deu"
print(config.barcodes_enabled)  # True / False
print(config.app_title)         # e.g. "Paperless-ngx"
```
