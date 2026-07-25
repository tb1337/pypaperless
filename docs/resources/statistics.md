# Statistics

The `statistics` resource returns aggregate counts and metadata about the Paperless-ngx document archive. It is a parameter-free singleton call.

## Model

See [`pypaperless/models/statistics.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/statistics.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch

No primary key - call without arguments:

```python
stats = await paperless.statistics()

print(stats.documents_total)      # 1024
print(stats.documents_inbox)      # 3
print(stats.current_asn)          # 512
print(stats.correspondent_count)  # 47

for ft in stats.document_file_type_counts or []:
    print(ft.mime_type, ft.mime_type_count)
    # "application/pdf" 980
    # "image/jpeg" 44
```
