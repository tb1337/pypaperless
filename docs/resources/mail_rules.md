# Mail Rules

Mail rules define how Paperless-ngx processes incoming emails from a mail account. Each rule specifies filters (sender, subject, body) and actions to apply when a matching email is found.

## Model

See [`pypaperless/models/mails/rules.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/mails/rules.py) for all fields and types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
rule = await paperless.mail_rules(3)
print(rule.name)  # "Invoice imports"
print(rule.account)  # 1  (mail account id)
print(rule.enabled)  # True
print(rule.filter_from)  # "billing@vendor.com"
```

## Iterate

```python
async for rule in paperless.mail_rules:
    print(rule.id, rule.name, "enabled:", rule.enabled)

# Only active rules
active = [r async for r in paperless.mail_rules if r.enabled]
```

## Permissions

```python
async with paperless.mail_rules.with_permissions():
    rule = await paperless.mail_rules(3)
    print(rule.owner)  # owner user id
    print(rule.permissions)  # Permissions
```

See [Permissions](../concepts/permissions.md) for details.
