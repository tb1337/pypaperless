# Processed Mail

The `processed_mail` resource is a read-only log of emails that have already been processed by a mail rule. Each entry records the outcome of the import attempt.

## Model

See [`pypaperless/models/mails/processed.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/mails/processed.py) for all fields and types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
entry = await paperless.processed_mail(5)
print(entry.subject)  # "RE: Invoice #1234"
print(entry.status)  # "SUCCESS"
print(entry.processed)  # datetime(2024, 3, 15, 10, 30, ...)
```

`status` is a free-form string upstream. Paperless-ngx writes it in upper case — `"SUCCESS"`,
`"FAILED"` and `"PROCESSED_WO_CONSUMPTION"`.

## Iterate

```python
async for entry in paperless.processed_mail:
    if entry.status == "FAILED":
        print(f"Failed: {entry.subject} - {entry.error}")

# Collect all failures
failures = [e async for e in paperless.processed_mail if e.status == "FAILED"]
```

## Filter

```python
# Entries produced by a single mail rule
async with paperless.processed_mail.filter(rule=3) as ctx:
    async for entry in ctx:
        print(entry.subject, entry.status)

# Combine with the processing status
async with paperless.processed_mail.filter(rule=3, status="FAILED") as ctx:
    failures = await ctx.as_list()
```

`/api/processed_mail/` supports exactly two filters, both exact-match — see
[`ProcessedMailFilters`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/filters.py).
Note that `rule` must reference an existing mail rule; the API answers unknown ids with
HTTP 400 rather than an empty result set.

## Owner

`ProcessedMail` carries the `owner` field directly — no `with_permissions()`
context is needed (the model does not expose the full permissions table).

```python
entry = await paperless.processed_mail(5)
print(entry.owner)  # owner user id
```
