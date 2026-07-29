# Mail Accounts

Mail accounts are the IMAP mailbox configurations that Paperless-ngx polls for incoming documents. They support fetching and iterating, with permission information available on request.

## Model

See [`pypaperless/models/mails/accounts.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/mails/accounts.py) for all fields and types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
account = await paperless.mail_accounts(1)
print(account.name)  # "My Gmail"
print(account.imap_server)  # "imap.gmail.com"
print(account.username)  # "user@gmail.com"
```

## Iterate

```python
async for account in paperless.mail_accounts:
    print(account.id, account.name)

# All accounts as a dict keyed by id
accounts = await paperless.mail_accounts.as_dict()
```

## Test connection

```python
result = await paperless.mail_accounts.test()
print(result)
```

## Process mailbox now

```python
await paperless.mail_accounts.process(1)
```

## Permissions

```python
async with paperless.mail_accounts.with_permissions():
    account = await paperless.mail_accounts(1)
    print(account.owner)  # owner user id
    print(account.permissions)  # Permissions
```

See [Permissions](../concepts/permissions.md) for details.
