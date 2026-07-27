# Search Query Builder

The `SearchQuery` builder provides a fluent, composable DSL for constructing Tantivy query strings for the Paperless-ngx global search endpoint (`/api/search/`).

The builder output is a plain string - it is fully compatible with the raw string API. Both raw strings and builder objects are accepted by `paperless.search()`.

---

## Quick start

```python
from pypaperless.models.types import SearchQuery as Q

# Plain term
result = await paperless.search("invoice")

# Using the builder (equivalent to above)
result = await paperless.search(Q("invoice"))

# Field-scoped: tag:unpaid
result = await paperless.search(Q.field("tag", "unpaid"))

# Combined: (invoice AND tag:unpaid)
q = Q("invoice") & Q.field("tag", "unpaid")
result = await paperless.search(q)
```

---

## Atoms

### Plain term

```python
Q("produ*name")  # wildcard
Q("contract")  # exact word
```

### Field-scoped term (`field:value`)

Match against a specific metadata field:

```python
Q.field("document_type", "invoice")
Q.field("tag", "unpaid")
Q.field("correspondent", "university")
Q.field("storage_path", "archive")
```

Notes and custom fields support JSON sub-field syntax for targeted queries:

```python
Q.field("notes.note", "urgent")  # match within note text
Q.field("notes.user", "alice")  # match by note author
Q.field("custom_fields.value", "12345")  # match custom field value
Q.field("custom_fields.name", "invoice")  # match custom field name
```

The field names correspond to the Paperless-ngx Tantivy index schema.

### Date range (`field:[start to end]`)

```python
Q.date_range("created", "2005", "2009")
# → created:[2005 to 2009]

Q.date_range("added", "yesterday", "today")
# → added:[yesterday to today]

Q.date_range("modified", "2024-01-01", "2024-12-31")
# → modified:[2024-01-01 to 2024-12-31]
```

Paperless-ngx rewrites natural-language date keywords to ISO 8601 ranges before passing them to Tantivy. Relative expressions like `today`, `yesterday`, and partial dates like `2024` are all valid.

---

## Combining expressions

### AND (`&`)

All terms must match. Chaining `&` flattens into a single AND node (no extra parentheses):

```python
q = Q("invoice") & Q.field("tag", "unpaid")
# str(q) → "(invoice AND tag:unpaid)"

q = Q("shop") & Q.field("document_type", "invoice") & Q.date_range("created", "2020", "2024")
# str(q) → "(shop AND document_type:invoice AND created:[2020 to 2024])"
```

### OR (`|`)

At least one term must match. Chaining `|` also flattens:

```python
q = Q.field("tag", "inbox") | Q.field("tag", "important")
# str(q) → "(tag:inbox OR tag:important)"
```

### NOT (`~`)

Negates a term or expression:

```python
q = ~Q.field("document_type", "letter")
# str(q) → "NOT document_type:letter"
```

---

## Complex expressions

Operators compose freely:

```python
from pypaperless.models.types import SearchQuery as Q

# "Find invoices or receipts tagged unpaid, from 2020 onwards, that are not letters"
q = (
    (Q.field("document_type", "invoice") | Q.field("document_type", "receipt"))
    & Q.field("tag", "unpaid")
    & Q.date_range("created", "2020", "today")
    & ~Q.field("document_type", "letter")
)
# str(q) → "((document_type:invoice OR document_type:receipt) AND tag:unpaid AND created:[2020 to today] AND NOT document_type:letter)"

result = await paperless.search(q)
```

---

## `str()` passthrough

Calling `str()` on any builder object yields the Tantivy query string directly:

```python
q = Q("contract") & Q.date_range("created", "2015", "2019")
print(str(q))
# (contract AND created:[2015 to 2019])
```

This means you can freely mix builder objects and raw strings in your code - both work with `paperless.search()`:

```python
# These are equivalent:
result = await paperless.search("invoice")
result = await paperless.search(Q("invoice"))
```

---

## API reference

| Class / method                       | Output format   |
| ------------------------------------ | --------------- |
| `SearchQuery(term)`                  | `term`          |
| `SearchQuery.field(name, value)`     | `name:value`    |
| `SearchQuery.date_range(name, s, e)` | `name:[s to e]` |
