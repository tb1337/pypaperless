# Permissions

Paperless-ngx supports **object-level permissions** - some resources can have explicit `view` and `change` permissions assigned to individual users or groups.

---

## Resources that support permissions

The following resources include permission fields (`SecurableModel`):

- `documents`
- `correspondents`
- `document_types`
- `mail_accounts`
- `mail_rules`
- `saved_views`
- `storage_paths`
- `tags`

!!! note
    `processed_mail` exposes a plain `owner` field but no permission table -
    `with_permissions()` has no effect there. See
    [Processed Mail](../resources/processed_mail.md#owner).

---

## Permission fields on a model

When permissions are loaded, a `Document` (or other securable model) exposes:

| Field             | Description                                  |
| ----------------- | -------------------------------------------- |
| `owner`           | User ID of the owner                         |
| `user_can_change` | Whether the current user can change the item |
| `permissions`     | Full permission table                        |

```python
doc = await paperless.documents(42)

print(doc.owner)
print(doc.user_can_change)

if doc.has_permissions:
    print(doc.permissions.view.users)
    print(doc.permissions.view.groups)
    print(doc.permissions.change.users)
    print(doc.permissions.change.groups)
```

!!! note
    `doc.permissions` is `None` unless you explicitly request the full permissions (see below).

---

## Requesting permissions alongside data

By default, Paperless-ngx does not include the full permission table in responses.

### Recommended: `with_permissions()` context manager

Use the `with_permissions()` context manager - the flag is set automatically on
entry and reset on exit, even if an exception occurs. It is task-local, so
concurrent asyncio tasks cannot interfere with each other:

```python
async with paperless.documents.with_permissions() as docs:
    doc = await docs(42)
    print(doc.permissions.view.users)

    async for doc in docs:
        print(doc.owner, doc.permissions)
```

### Alternative: `request_permissions` property

For cases where you need persistent control across multiple calls, the underlying property is available directly:

```python
paperless.documents.request_permissions = True

doc = await paperless.documents(42)
print(doc.permissions)

async for doc in paperless.documents:
    print(doc.owner, doc.permissions)

paperless.documents.request_permissions = False
```

The flag applies to all methods on the service (`__call__`, iteration, `update()`) until reset.

---

## Creating an item with permissions

When drafting a new item, use `set_permissions` to assign ownership and ACLs at creation time (`SecurableDraftModel`):

```python
from pypaperless.models.types import Permissions

perms = Permissions(
    view_users=[2, 3],
    change_users=[2],
    change_groups=[1],
)

draft = paperless.tags.create(
    name="confidential",
    owner=1,
    set_permissions=perms,
)

new_id = await paperless.tags.save(draft)
```

---

## Updating permissions on an existing item

Fetch the item, modify the `permissions` field, then call `update()`.

**Replace the whole permission set:**

```python
from pypaperless.models.types import Permissions

doc = await paperless.documents(42)

doc.permissions = Permissions(
    view_users=[2, 3],
    change_users=[2],
)
doc.owner = 1

await paperless.documents.update(doc)
```

**Or mutate in place** (useful when adding/removing a single user):

```python
async with paperless.documents.with_permissions() as docs:
    doc = await docs(42)

doc.permissions.view.users.append(9)
doc.permissions.change.users.remove(3)

await paperless.documents.update(doc)
```

---

## `Permissions`

```python
class Permissions:
    view: _PermissionScope  # .users: list[int], .groups: list[int]
    change: _PermissionScope  # .users: list[int], .groups: list[int]
```

Constructed with flat keyword arguments - only specify what you need, omitted keys default to `[]`:

| Keyword argument | Meaning                          |
| ---------------- | -------------------------------- |
| `view_users`     | User IDs with view permission    |
| `view_groups`    | Group IDs with view permission   |
| `change_users`   | User IDs with change permission  |
| `change_groups`  | Group IDs with change permission |

```python
from pypaperless.models.types import Permissions

# Only specify what you need
Permissions(view_users=[2, 3], change_users=[2], change_groups=[1])

# Read individual scopes
perms = doc.permissions
perms.view.users
perms.view.groups
perms.change.users
perms.change.groups
```

---

## Listing users and groups

To populate permission assignments, you can enumerate users and groups:

```python
async for user in paperless.users:
    print(user.id, user.username)

async for group in paperless.groups:
    print(group.id, group.name)
```
