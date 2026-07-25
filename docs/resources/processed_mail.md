# Processed Mail

The `processed_mail` resource is a read-only log of emails that have already been processed by a mail rule. Each entry records the outcome of the import attempt.

## Model

See [`pypaperless/models/mails/processed.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/mails/processed.py) for all fields and types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
entry = await paperless.processed_mail(5)
print(entry.subject)   # "RE: Invoice #1234"
print(entry.status)    # "success"
print(entry.processed) # datetime(2024, 3, 15, 10, 30, ...)
```

## Iterate

```python
async for entry in paperless.processed_mail:
    if entry.status == "failed":
        print(f"Failed: {entry.subject} - {entry.error}")

# Collect all failures
failures = [
    e async for e in paperless.processed_mail
    if e.status == "failed"
]
```

## Owner

`ProcessedMail` carries the `owner` field directly — no `with_permissions()`
context is needed (the model does not expose the full permissions table).

```python
entry = await paperless.processed_mail(5)
print(entry.owner)  # owner user id
```
