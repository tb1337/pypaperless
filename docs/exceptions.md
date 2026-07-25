# Exceptions

pypaperless raises structured exceptions so you can handle specific error conditions precisely.

All exceptions inherit from `PaperlessError`, which in turn inherits from Python's built-in `Exception`.

---

## Exception hierarchy

```
PaperlessError
├── InitializationError
│   ├── PaperlessConnectionError
│   │   └── PaperlessTimeoutError
│   ├── AuthError
│   │   ├── InvalidTokenError
│   │   └── InactiveOrDeletedError
│   └── ForbiddenError
├── ResponseError
│   ├── BadJsonResponseError
│   ├── JsonResponseWithError
│   ├── NotFoundError
│   ├── UnexpectedStatusError
│   └── BulkEditError
├── DraftError
│   ├── DraftFieldRequiredError
│   └── DraftNotSupportedError
├── DispatchError
├── ResourceError
│   ├── DeletionError
│   ├── ItemNotFoundError
│   ├── PrimaryKeyRequiredError
│   └── TaskNotFoundError
└── DocumentError
    ├── AsnRequestError
    └── SendEmailError
```

---

## Reference

### `PaperlessError`

Base class for all pypaperless exceptions. Catch this to handle any pypaperless error generically.

---

### `InitializationError`

Raised when `PaperlessClient.initialize()` fails for any reason - connectivity, authentication or authorisation.

```python
from pypaperless.exceptions import InitializationError
from pypaperless import PaperlessClient

try:
    async with PaperlessClient("localhost:8000", "bad-token") as p:
        pass
except InitializationError as exc:
    print("Could not initialise:", exc)
```

**Subclasses:**

#### `PaperlessConnectionError`

The host could not be reached (network error, wrong URL, DNS failure, broken connection mid-response, etc.). All transport-level failures raise this exception - `httpx` internals never leak through.

**Subclasses:**

- **`PaperlessTimeoutError`** - the request timed out. The host is reachable but did not respond in time; retrying, or passing a custom `httpx.AsyncClient` with a higher timeout, may help.

#### `AuthError`

The server responded with HTTP **401**.

**Subclasses:**

- **`InvalidTokenError`** - 401 because the token is invalid or expired.
- **`InactiveOrDeletedError`** - 401 because the user account is inactive or deleted.

#### `ForbiddenError`

The server responded with HTTP **403** - the user is authenticated but lacks permission to access the resource.

---

### `ResponseError`

Base class for exceptions caused by an unexpected or error API response. Catch this to handle all response-level failures in one place.

#### `BadJsonResponseError`

The API returned a response that could not be decoded as JSON.

#### `JsonResponseWithError`

The API accepted the request but returned an error payload in its JSON body. The exception message includes the key path and error message extracted from the payload.

```python
from pypaperless.exceptions import JsonResponseWithError

try:
    await paperless.documents.save(draft)
except JsonResponseWithError as exc:
    print(exc)  # e.g. "Paperless [document]: No file was submitted."
```

#### `NotFoundError`

The server responded with HTTP **404** - the requested resource does not exist. The original `httpx.Response` is available as the `response` attribute.

```python
from pypaperless.exceptions import NotFoundError

try:
    doc = await paperless.documents(999999)
except NotFoundError:
    print("Document does not exist.")
```

#### `UnexpectedStatusError`

The server responded with a non-2xx status code that has no dedicated exception (e.g. a 5xx server error). The original `httpx.Response` is available as the `response` attribute.

#### `BulkEditError`

Raised when a bulk edit operation via `paperless.documents.bulk_edit` returns a non-OK result from the API.

```python
from pypaperless.exceptions import BulkEditError

try:
    await paperless.documents.bulk_edit.delete([10, 11])
except BulkEditError as exc:
    print(exc)  # "Bulk edit operation returned a non-OK result: ..."
```

---

### `DraftError`

Base class for exceptions raised during draft lifecycle operations. Catch this to handle all draft-related failures in one place.

#### `DraftFieldRequiredError`

Raised by `draft.validate_draft()` (called automatically inside `save()`) when one or more required fields are missing.

```python
draft = paperless.documents.create()  # missing `document` field

try:
    await paperless.documents.save(draft)
except DraftFieldRequiredError as exc:
    print(exc)  # "Missing fields for saving a `DocumentDraft`: document."
```

#### `DraftNotSupportedError`

Raised when calling `create()` on a service that does not have a `_draft_cls` defined (i.e. creation is not supported for that resource).

---

### `DispatchError`

Raised when `paperless.update()`, `paperless.delete()`, or `paperless.save()` is called with a model type that has no registered service. Only models managed by a CRUD service can be dispatched.

---

### `ResourceError`

Base class for exceptions raised during resource access or lookup operations. Catch this to handle all resource-level failures in one place.

#### `DeletionError`

Raised by `delete()` when the API returns a non-2xx response. To suppress this exception, pass `silent_fail=True` to the service `delete()` method.

```python
from pypaperless.exceptions import DeletionError

try:
    await paperless.tags.delete(tag)
except DeletionError as exc:
    print("Deletion failed:", exc)

# or suppress silently:
await paperless.tags.delete(tag, silent_fail=True)
```

#### `ItemNotFoundError`

Raised by `DocumentCustomFieldList.get()` when the requested field is not present on the document.

```python
from pypaperless.exceptions import ItemNotFoundError

try:
    value = document.custom_fields.get(99)
except ItemNotFoundError:
    print("Field 99 is not set on this document")
```

Use `default()` instead of `get()` to avoid this exception and receive `None` on absence.

#### `PrimaryKeyRequiredError`

Raised when a document-scoped sub-service is used without a resolvable document primary
key — that is, neither bound via a `Document` instance nor passed as `pk`. This covers
`notes`, `history`, `share_links`, `ai_suggestions`, `root` and `versions`.

```python
from pypaperless.exceptions import PrimaryKeyRequiredError

try:
    await paperless.documents.history()   # no pk, no bound document
except PrimaryKeyRequiredError:
    print("Pass the document pk: paperless.documents.history(42)")
```

#### `TaskNotFoundError`

Raised when looking up a task by UUID that does not exist in Paperless-ngx.

```python
from pypaperless.exceptions import TaskNotFoundError

try:
    task = await paperless.tasks("non-existent-uuid")
except TaskNotFoundError as exc:
    print(exc)  # "Task with UUID non-existent-uuid not found."
```

---

### `DocumentError`

Base class for exceptions raised by document-specific service operations. Catch this to handle all document-level failures in one place.

#### `AsnRequestError`

Raised when the request for the next available archive serial number fails unexpectedly.

#### `SendEmailError`

Raised when the API rejects an e-mail send request.

---

## Recommended error handling pattern

```python
from pypaperless.exceptions import (
    PaperlessConnectionError,
    AuthError,
    ForbiddenError,
    PaperlessError,
)
from pypaperless import PaperlessClient

try:
    async with PaperlessClient("localhost:8000", "your-token") as paperless:
        doc = await paperless.documents(42)
except PaperlessConnectionError:
    print("Cannot reach the Paperless server.")
except AuthError:
    print("Authentication failed - check your token.")
except ForbiddenError:
    print("Access denied.")
except PaperlessError as exc:
    print(f"Unexpected error: {exc}")
```
