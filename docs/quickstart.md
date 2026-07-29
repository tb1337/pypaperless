# Getting started

This page walks you through the first steps with **pypaperless**: installation, creating a session and obtaining an API token.

---

## Installation

Install from PyPI:

```bash
pip install pypaperless
```

Requires **Python 3.13** or higher.

---

## Your first session

Import the `PaperlessClient` class and create an instance with your Paperless-ngx host and API token.

pypaperless is fully **async**. All API calls must be made inside an `async` function.

### Context manager (recommended)

The cleanest way to use pypaperless is as an async context manager. It calls `initialize()` and `close()` automatically.

```python
import asyncio
from pypaperless import PaperlessClient


async def main():
    async with PaperlessClient("localhost:8000", "your-api-token") as paperless:
        # paperless is now ready to use
        async for document in paperless.documents:
            print(document.id, document.title)


asyncio.run(main())
```

### Manual lifecycle

You can also manage the lifecycle manually by calling `initialize()` and `close()` yourself:

```python
async def main():
    paperless = PaperlessClient("localhost:8000", "your-api-token")
    await paperless.initialize()

    # do something...

    await paperless.close()
```

### Configuration via environment variables

Instead of hard-coding credentials you can set environment variables and call `PaperlessClient.from_env()`:

```bash
export PYPAPERLESS_URL=https://paperless.example.com
export PYPAPERLESS_TOKEN=your-api-token
```

```python
from pypaperless import PaperlessClient

async with PaperlessClient.from_env() as paperless:
    ...
```

See [Session management](session.md#configuration-modes) for all three configuration modes.

---

## URL formats

The `url` parameter accepts a variety of formats. pypaperless normalises the URL automatically.

| Input                             | Resolved to                     |
| --------------------------------- | ------------------------------- |
| `"localhost:8000"`                | `https://localhost:8000`        |
| `"http://192.168.1.10:8000"`      | `http://192.168.1.10:8000`      |
| `"https://paperless.example.com"` | `https://paperless.example.com` |

!!! note
    When no scheme is provided, `https://` is assumed.

---

## Generating an API token

If you don't have a token yet, you can generate one from a username and password using the `generate_api_token` helper function:

```python
from pypaperless import generate_api_token, PaperlessClient

token = await generate_api_token(
    "localhost:8000",
    username="admin",
    password="secret",
)

paperless = PaperlessClient("localhost:8000", token)
```

!!! warning
    `generate_api_token` sends credentials as plain JSON. Do not use this in production environments or automated pipelines where security matters.

---

## Checking connection status

After `initialize()`, you can inspect the host:

```python
from pypaperless import PaperlessClient

async with PaperlessClient("localhost:8000", "your-api-token") as paperless:
    print(paperless.is_initialized)  # True
    print(paperless.host_version)  # e.g. "3.0.0"
    print(paperless.host_api_version)  # e.g. 10
```

---

## Next steps

- [Session management](session.md) - custom HTTP clients, advanced lifecycle
- [Resources](resources.md) - learn about all available resources and CRUD operations
