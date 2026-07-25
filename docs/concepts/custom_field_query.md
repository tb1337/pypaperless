# Custom field query

The `custom_field_query` filter lets you search documents by custom field values using a structured boolean expression. Paperless-ngx parses the expression serverside - pypaperless provides a small builder so you never have to construct the JSON by hand.

---

## Basic usage

Build an expression and pass `str(q)` to the `custom_field_query` kwarg of `documents.filter()`:

```python
from pypaperless.builders import CustomFieldQuery as Q

q = Q("Status", "exact", "open")

async with paperless.documents.filter(custom_field_query=str(q)) as docs:
    async for doc in docs:
        print(doc.title)
```

---

## Combining expressions

Use `&`, `|` and `~` to build boolean queries. Chained `&` and `|` are automatically flattened:

```python
q = (
    Q("Status", "exact", "open")
    & Q("Amount", "gte", 100)
    & ~Q("Archived", "exact", True)
)
# Serialises to:
# ["AND", [["Status","exact","open"], ["Amount","gte",100], ["NOT",["Archived","exact",true]]]]
```

OR across multiple categories:

```python
q = (
    Q("Category", "exact", "A")
    | Q("Category", "exact", "B")
    | Q("Category", "exact", "C")
)
```

---

## Referencing a field

`field` can be either the **integer ID** or the **name string**:

```python
Q(42, "exists", True)        # by ID
Q("Invoice Amount", "gte", 100)  # by name
```

---

## Supported operators

The valid operators depend on the field's data type:

| Applies to                           | Operators                             |
| ------------------------------------ | ------------------------------------- |
| **All types**                        | `exact` `in` `isnull` `exists`        |
| `STRING` `LONGTEXT` `URL` `MONETARY` | `icontains` `istartswith` `iendswith` |
| `INTEGER` `FLOAT` `MONETARY` `DATE`  | `gt` `gte` `lt` `lte` `range`         |
| `DOCUMENT_LINK`                      | `contains`                            |

The full operator set is enumerated in
[`builders/custom_fields.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/builders/custom_fields.py)
as the `_QueryOperation` literal — those are the only values the type
checker accepts as the second argument to `CustomFieldQuery(...)`.

### `exists` vs `isnull`

`exists` is the idiomatic way to check field presence:

```python
Q("Due Date", "exists", True)   # document has the field
Q("Due Date", "exists", False)  # document does not have the field
```

### `in` and `range`

Pass a list as the value:

```python
Q("Status", "in", ["open", "pending"])
Q("Amount", "range", [10, 100])  # start, end (inclusive)
```

---

## Using `build()`

`str(q)` is shorthand for `json.dumps(q.build())`. Call `build()` directly if you need the raw Python structure:

```python
q = Q("Amount", "gte", 50) & Q("Status", "exact", "open")
print(q.build())
# ["AND", [["Amount", "gte", 50], ["Status", "exact", "open"]]]

print(str(q))
# '["AND", [["Amount", "gte", 50], ["Status", "exact", "open"]]]'
```

---

## Server-side limits

Paperless-ngx enforces:

- Maximum nesting depth: **10**
- Maximum number of atoms: **20**

Exceeding these limits returns a HTTP 400 validation error.

The full filter specification is in the [Paperless-ngx API reference](https://docs.paperless-ngx.com/api/#filtering-by-custom-fields).
