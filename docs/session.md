# Session management

This page covers all configuration modes, custom HTTP clients and connection lifecycle details.

---

## Configuration modes

**pypaperless** can be configured in three ways:

### 1. Explicit parameters

Pass `url` and `token` directly to the constructor:

```python
from pypaperless import PaperlessClient

paperless = PaperlessClient("localhost:8000", "your-api-token")
```

### 2. `PaperlessSettings` object

Build a `PaperlessSettings` instance and pass it to `PaperlessClient.from_config()`. Useful when you want to construct or validate settings separately:

```python
from pypaperless import PaperlessClient, PaperlessSettings

cfg = PaperlessSettings(
    url="https://paperless.example.com",
    token="your-api-token",
)

async with PaperlessClient.from_config(cfg) as paperless:
    ...
```

### 3. Environment variables

Set the `PYPAPERLESS_*` environment variables and call `PaperlessClient.from_env()`. Ideal for containers, CI pipelines and twelve-factor apps:

| Environment variable | Field     | Required |
| -------------------- | --------- | :------: |
| `PYPAPERLESS_URL`    | Base URL  |    ✓     |
| `PYPAPERLESS_TOKEN`  | API token |          |

```bash
export PYPAPERLESS_URL=https://paperless.example.com
export PYPAPERLESS_TOKEN=your-api-token
```

```python
from pypaperless import PaperlessClient

async with PaperlessClient.from_env() as paperless:
    ...
```

!!! note
    `PYPAPERLESS_URL` is required. If it is not set, a `ValidationError` is raised immediately.

---

## The `PaperlessClient` constructor reference

```python
PaperlessClient(
    url: str,
    token: str | None = None,
    *,
    client: httpx.AsyncClient | None = None,
)
```

| Parameter | Description                                                     |
| --------- | --------------------------------------------------------------- |
| `url`     | Hostname, IP address or full URL of your Paperless-ngx instance |
| `token`   | API token obtained from Paperless-ngx settings                  |
| `client`  | Optional custom HTTP client (see below)                         |

For config-object or environment-variable based initialization use the factory
class methods:

| Factory method                     | Description                                                      |
| ---------------------------------- | ---------------------------------------------------------------- |
| `PaperlessClient.from_config(cfg)` | Initialize from a `PaperlessSettings` instance                   |
| `PaperlessClient.from_env()`       | Initialize from `PYPAPERLESS_URL` / `PYPAPERLESS_TOKEN` env vars |

---

## Lifecycle

### Context manager

The recommended approach - `initialize()` and `close()` are called automatically:

```python
from pypaperless import PaperlessClient

async with PaperlessClient("localhost:8000", "your-api-token") as paperless:
    # fully initialised here
    ...
# connection closed here
```

### Manual

```python
paperless = PaperlessClient("localhost:8000", "your-api-token")
await paperless.initialize()

try:
    # use paperless
    pass
finally:
    await paperless.close()
```

### What `initialize()` does

1. Sends a `GET` request to `/api/schema/` to verify connectivity and authentication.
2. Reads the `x-api-version` and `x-version` response headers.
3. Sets `is_initialized = True`.

Any connectivity or authentication problem raises an exception before `is_initialized` becomes `True`. See [Exceptions](exceptions.md) for details.

---

## Custom HTTP client

You can supply your own `httpx.AsyncClient`. This is useful when you need to:

- Configure timeouts, retries or proxy settings
- Reuse an existing client for connection pooling
- Inject custom headers or SSL certificates

```python
import httpx
from pypaperless import PaperlessClient

custom_client = httpx.AsyncClient(
    timeout=httpx.Timeout(30.0),
    verify="/path/to/ca-bundle.pem",
    headers={"X-Custom-Header": "value"},
)

async with PaperlessClient("localhost:8000", "your-api-token", client=custom_client) as paperless:
    ...
```

!!! note
    When you provide a `client`, pypaperless does **not** close it automatically when `close()` is called. You are responsible for managing its lifecycle.

---

## Logging

pypaperless uses the standard Python `logging` module under the logger name `pypaperless`.

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

The library logs `INFO`-level messages for `initialize()` and `close()` events.

---

## Available resources

After initialisation, the following services are available on the `PaperlessClient` instance:

| Attribute                     | Resource                         |
| ----------------------------- | -------------------------------- |
| `paperless.bulk_edit_objects` | Bulk edit (non-document objects) |
| `paperless.config`            | Application configuration        |
| `paperless.correspondents`    | Correspondents                   |
| `paperless.custom_fields`     | Custom fields                    |
| `paperless.documents`         | Documents                        |
| `paperless.document_types`    | Document types                   |
| `paperless.groups`            | User groups                      |
| `paperless.mail_accounts`     | Mail accounts                    |
| `paperless.mail_rules`        | Mail rules                       |
| `paperless.processed_mail`    | Processed mail                   |
| `paperless.profile`           | User profile                     |
| `paperless.saved_views`       | Saved views                      |
| `paperless.search`            | Full-text search                 |
| `paperless.share_link_bundles`| Share link bundles               |
| `paperless.share_links`       | Share links                      |
| `paperless.statistics`        | Statistics                       |
| `paperless.remote_version`    | Remote version info              |
| `paperless.status`            | System status                    |
| `paperless.storage_paths`     | Storage paths                    |
| `paperless.tags`              | Tags                             |
| `paperless.tasks`             | Background tasks                 |
| `paperless.trash`             | Trash (soft-deleted docs)        |
| `paperless.users`             | Users                            |
| `paperless.workflows`         | Workflows                        |

See [Resources](resources.md) for the full feature matrix.
