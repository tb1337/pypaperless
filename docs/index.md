# pypaperless

**pypaperless** is a modern, fully async Python client library for the [Paperless-ngx](https://docs.paperless-ngx.com/) REST API.

It is built on top of [httpx](https://www.python-httpx.org/) and [Pydantic](https://docs.pydantic.dev/), providing type-safe, async-first access to all Paperless-ngx resources.

---

## Installation

```bash
pip install pypaperless
```

Requires **Python 3.13+**.

---

## Quick example

```python
import asyncio
from pypaperless import PaperlessClient

async def main():
    async with PaperlessClient("localhost:8000", "your-api-token") as paperless:
        async for document in paperless.documents:
            print(document.id, document.title)

asyncio.run(main())
```

---

## Features

| Feature                   | Description                                                                                                                                              |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Fully async**           | Built on `asyncio` + `httpx.AsyncClient`                                                                                                                 |
| **Type-safe models**      | All resources are Pydantic models                                                                                                                        |
| **All resources**         | Documents, Correspondents, Tags, Document Types, Storage Paths, Custom Fields, Saved Views, Share Links, Workflows, Mail Accounts/Rules, Tasks, and more |
| **CRUD operations**       | Create, read, update and delete on all supported resources                                                                                               |
| **Iteration & filtering** | Async iteration, pagination and server-side filtering via `filter()`                                                                                     |
| **Custom field system**   | Rich, typed access to custom field values on documents                                                                                                   |
| **Object permissions**    | Full support for Paperless-ngx object-level permissions                                                                                                  |
| **Token generation**      | Helper to generate API tokens from username + password                                                                                                   |
| **Custom HTTP client**    | Bring your own `httpx.AsyncClient`                                                                                                                       |

---

## Documentation

- [Getting started](quickstart.md) - installation, first session, token generation
- [Session management](session.md) - lifecycle, configuration modes, custom client
- [Resources](resources.md) - all available resources and their capabilities
- [Documents](concepts/documents.md) - uploads, search, download, notes, metadata
- [Custom fields](concepts/custom_fields.md) - typed field values, cache, read & write
- [Permissions](concepts/permissions.md) - object-level permission management
- [Custom field query](concepts/custom_field_query.md) - structured `custom_field_query` filter builder
- [Search query](concepts/search_query.md) - fluent builder for the global search endpoint
- [Exceptions](exceptions.md) - full exception reference

---

## Links

- [GitHub repository](https://github.com/tb1337/pypaperless)
- [Paperless-ngx documentation](https://docs.paperless-ngx.com/)
- [Paperless-ngx API reference](https://docs.paperless-ngx.com/api/)
