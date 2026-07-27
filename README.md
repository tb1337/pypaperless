# pypaperless

[![GitHub Release][release-badge]][release-url]
[![Python Version][python-badge]][python-url]
[![GitHub License][license-badge]][license-url]

[![Tests][tests-badge]][tests-url]
[![Codecov][codecov-badge]][codecov-url]
[![Linting][linting-badge]][linting-url]
[![Typing][typing-badge]][typing-url]

**pypaperless** is a modern, fully async Python client library for the [Paperless-ngx](https://docs.paperless-ngx.com/) REST API.

- [Features](#features)
- [Quick example](#quick-example)
- [Installation](#installation)
- [Documentation](#documentation)
- [Compatibility matrix](#compatibility-matrix)
- [Authors \& contributors](#authors--contributors)

---

## Features

| Feature                        | Details                                                                                                                                                         |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Fully async**                | Built on `asyncio` + `httpx.AsyncClient`; drop-in for any async framework                                                                                       |
| **Type-safe models**           | All resources are validated [Pydantic](https://docs.pydantic.dev/) models                                                                                       |
| **Complete resource coverage** | Documents, Correspondents, Tags, Document Types, Storage Paths, Custom Fields, Saved Views, Share Links, Workflows, Mail Accounts/Rules, Tasks, Trash, and more |
| **CRUD + permissions**         | Create, read, update, delete and manage object-level permissions per resource                                                                                   |
| **Async iteration & paging**   | Iterate over all items or page-by-page; server-side filtering via `filter()`                                                                                    |
| **Document operations**        | Upload, download, search (full-text & advanced), notes, suggestions, metadata                                                                                   |
| **Custom field system**        | Rich typed access to custom field values — read, write, remove with caching                                                                                     |
| **Token generation**           | Static helper to exchange username + password for an API token                                                                                                  |
| **Custom HTTP client**         | Bring your own `httpx.AsyncClient` for full control over timeouts, proxies, TLS, …                                                                              |

## Quick example

```python
import asyncio
from pypaperless import PaperlessClient


async def main():
    async with PaperlessClient("localhost:8000", "your-api-token") as paperless:
        # iterate all documents - pagination is handled automatically
        async for document in paperless.documents:
            print(document.id, document.title)

        # fetch a single item
        doc = await paperless.documents(42)

        # filter with server-side parameters
        async with paperless.tags.filter(name__icontains="invoice") as filtered:
            async for tag in filtered:
                print(tag.id, tag.name)


asyncio.run(main())
```

## Installation

Requires **Python 3.13+**.

```bash
pip install pypaperless
```

## Documentation

Full documentation is available **[here][docs-url]**.

## Compatibility matrix

| **pypaperless** | *Paperless-ngx* | Python | Notes                                   |
| --------------- | --------------- | ------ | --------------------------------------- |
| **>= v6.0**     | **>= 3.0**      | 3.13   | Current release                         |
| >= v5.2         | >= 2.19         | 3.12   |                                         |
| >= v5.0         | >= 2.17         | 3.12   |                                         |
| >= v4.x         | >= 2.15         | 3.12   |                                         |
| < v4.0          | < 2.15          | 3.11   | Incompatible with Paperless-ngx >= 2.15 |

> **Recommendation:** Keep both *Paperless-ngx* and **pypaperless** up to date to benefit from the latest API features and bug fixes.

## Authors & contributors

**pypaperless** is written and maintained by: [Tobias Schulz][contributors-tbsch] and Claude. Feedback and contributions are always welcome.

Check out all [contributors][contributors-url].

[codecov-badge]: https://codecov.io/gh/tb1337/pypaperless/graph/badge.svg?token=IMXRBK3HRE
[codecov-url]: https://app.codecov.io/gh/tb1337/pypaperless/tree/main
[contributors-tbsch]: https://tbsch.de
[contributors-url]: https://github.com/tb1337/pypaperless/graphs/contributors
[docs-url]: https://pypaperless.docs.tbsch.de
[license-badge]: https://img.shields.io/github/license/tb1337/pypaperless
[license-url]: /LICENSE.md
[python-badge]: https://img.shields.io/pypi/pyversions/pypaperless
[python-url]: https://pypi.org/project/pypaperless/
[tests-badge]: https://github.com/tb1337/pypaperless/actions/workflows/tests.yml/badge.svg
[tests-url]: https://github.com/tb1337/pypaperless/actions
[release-badge]: https://img.shields.io/github/v/release/tb1337/pypaperless
[release-url]: https://github.com/tb1337/pypaperless/releases
[linting-badge]: https://github.com/tb1337/pypaperless/actions/workflows/linting.yml/badge.svg
[linting-url]: https://github.com/tb1337/pypaperless/actions
[typing-badge]: https://github.com/tb1337/pypaperless/actions/workflows/typing.yml/badge.svg
[typing-url]: https://github.com/tb1337/pypaperless/actions
