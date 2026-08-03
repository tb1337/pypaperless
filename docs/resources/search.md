# Search

The `search` resource exposes the Paperless-ngx global search endpoint (`/api/search/`). It searches across documents, tags, correspondents, document types, and other resource types simultaneously and returns a scored, ranked result. It also exposes the typeahead endpoint (`/api/search/autocomplete/`) via [`autocomplete()`](#autocomplete).

## Model

See [`pypaperless/models/search.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/search.py) and [`pypaperless/models/types.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/types.py) for all types. The upstream schema component is `SearchResult`.

### `SearchResult`

| Field            | Type                  | Description                                       |
| ---------------- | --------------------- | ------------------------------------------------- |
| `total`          | `int`                 | Total number of matching objects across all types |
| `documents`      | `list[Document]`      | Matching documents (full `Document` objects)      |
| `saved_views`    | `list[SavedView]`     | Matching saved views                              |
| `tags`           | `list[Tag]`           | Matching tags                                     |
| `correspondents` | `list[Correspondent]` | Matching correspondents                           |
| `document_types` | `list[DocumentType]`  | Matching document types                           |
| `storage_paths`  | `list[StoragePath]`   | Matching storage paths                            |
| `users`          | `list[User]`          | Matching users                                    |
| `groups`         | `list[Group]`         | Matching groups                                   |
| `mail_rules`     | `list[MailRule]`      | Matching mail rules                               |
| `mail_accounts`  | `list[MailAccount]`   | Matching mail accounts                            |
| `workflows`      | `list[Workflow]`      | Matching workflows                                |
| `custom_fields`  | `list[CustomField]`   | Matching custom fields                            |

All fields are `None`-able. Nested objects are full model instances — pass them to the matching service (`paperless.documents.update(doc)`, `paperless.tags.delete(tag)`, …) or to the client-level dispatcher (`paperless.update(doc)`, `paperless.delete(tag)`) to act on them.

## Search

### Plain string query

```python
result = await paperless.search("invoice")

print(result.total)  # total matches across all types
for doc in result.documents or []:
    print(doc.title, doc.id)
```

### Using the SearchQuery builder

For complex queries, use the `SearchQuery` builder (see [Search Query Builder](../concepts/search_query.md)):

```python
from pypaperless.models.types import SearchQuery

q = SearchQuery("invoice") & SearchQuery.field("tag", "unpaid")
result = await paperless.search(q)
```

### Database-only search

Pass `db_only=True` to skip the full-text index and search only the database fields:

```python
result = await paperless.search("contract", db_only=True)
```

### Autocomplete

`autocomplete()` hits `/api/search/autocomplete/` and returns a plain list of index terms - the typeahead helper behind the Paperless-ngx search bar, not resource objects:

```python
terms = await paperless.search.autocomplete("inv")
# ['invoice', 'invoices', 'invoiced']

terms = await paperless.search.autocomplete("inv", 3)
```

`limit` is omitted from the request when left at `None`, which leaves the server default (10) in place. An empty term or a `limit` below 1 is rejected by the server with HTTP 400, raising `UnexpectedStatusError`.

### Working with results

All nested objects in `SearchResult` are `PaperlessModel` instances, so you can act on them immediately:

```python
result = await paperless.search("old project")

# Delete all matched documents
for doc in result.documents or []:
    await paperless.documents.delete(doc)

# The correspondents list works the same way
for corr in result.correspondents or []:
    print(corr.name)
```
