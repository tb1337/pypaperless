# Custom fields

Custom fields let you add structured, typed metadata to documents in Paperless-ngx. pypaperless provides a rich API for reading and writing them.

---

## Custom field types

Each custom field has a `data_type` which determines the type of its value:

| `CustomFieldType` | Python value type | Description                        |
| ----------------- | ----------------- | ---------------------------------- |
| `STRING`          | `str`             | Short text                         |
| `LONGTEXT`        | `str`             | Long text / multi-line             |
| `URL`             | `str`             | URL string                         |
| `DATE`            | `datetime.date`   | Date value                         |
| `BOOLEAN`         | `bool`            | True / False                       |
| `INTEGER`         | `int`             | Integer number                     |
| `FLOAT`           | `float`           | Floating point number              |
| `MONETARY`        | `str`             | Currency amount, e.g. `"EUR12.50"` |
| `SELECT`          | `int` or `str`    | Selection from predefined options  |
| `DOCUMENT_LINK`   | `list[int]`       | Links to other documents by ID     |

---

## The cache

To get typed `CustomFieldValue` instances (instead of plain `CustomFieldValue`), pypaperless needs to know the type of each field. This information comes from the **custom fields cache**.

### Providing a cache

The cache lives on the runtime (`paperless.runtime.cache.custom_fields`) and is
``None`` until you populate it. Fetch all custom fields once and assign them as
an ``id → CustomField`` mapping before working with documents:

```python
from pypaperless import PaperlessClient

async with PaperlessClient("localhost:8000", "your-api-token") as paperless:
    paperless.runtime.cache.custom_fields = await paperless.custom_fields.as_dict()

    doc = await paperless.documents(42)

    for item in doc.custom_fields:
        print(type(item).__name__, item.field, item.value)
```

With the cache populated, `doc.custom_fields` yields typed instances like `CustomFieldStringValue`, `CustomFieldIntegerValue`, etc.

### Without cache

Without the cache, every `CustomFieldValue` is of the base type and `data_type` will be `None`:

```python
doc = await paperless.documents(42)

for item in doc.custom_fields:
    # item is always CustomFieldValue, value is Any
    print(item.field, item.value)
```

---

## Reading custom field values

### Checking if a field is present

```python
# by field ID
if 8 in document.custom_fields:
    print("Field 8 is set")

# by CustomField object
cf = await paperless.custom_fields(8)
if cf in document.custom_fields:
    print("Present")
```

### Iterating over all values

```python
for item in document.custom_fields:
    print(item.field, item.value, item.name)
```

### Getting a specific value

Use `get()` to retrieve a value by field ID or `CustomField` object. Raises `ItemNotFoundError` if not present:

```python
value = document.custom_fields.get(8)
print(value.value)
```

Use `default()` to return `None` instead of raising when the field is absent:

```python
if value := document.custom_fields.default(8):
    print(value.value)
```

### Typed access

Both `get()` and `default()` accept an optional `expected_type` parameter to assert and return a more specific subclass:

```python
from pypaperless.models.custom_fields import CustomFieldIntegerValue

value = document.custom_fields.get(8, CustomFieldIntegerValue)
print(value.value + 1)  # IDE knows it's an int
```

A `TypeError` is raised if the actual type does not match `expected_type`.

---

## Typed value subclasses

When the cache is active, pypaperless instantiates the right subclass automatically:

| Class                          | `data_type`          | `value` type    |
| ------------------------------ | -------------------- | --------------- |
| `CustomFieldStringValue`       | `STRING`, `LONGTEXT` | `str`           |
| `CustomFieldURLValue`          | `URL`                | `str`           |
| `CustomFieldDateValue`         | `DATE`               | `datetime.date` |
| `CustomFieldBooleanValue`      | `BOOLEAN`            | `bool`          |
| `CustomFieldIntegerValue`      | `INTEGER`            | `int`           |
| `CustomFieldFloatValue`        | `FLOAT`              | `float`         |
| `CustomFieldMonetaryValue`     | `MONETARY`           | `str`           |
| `CustomFieldSelectValue`       | `SELECT`             | `int` or `str`  |
| `CustomFieldDocumentLinkValue` | `DOCUMENT_LINK`      | `list[int]`     |

### `CustomFieldMonetaryValue` extras

Monetary values provide convenience properties:

```python
item = document.custom_fields.get(8, CustomFieldMonetaryValue)

print(item.currency)  # "EUR"
print(item.amount)  # 12.5

item.currency = "USD"
item.amount = 9.99
# item.value is now "USD9.99"
```

### `CustomFieldSelectValue` extras

```python
item = document.custom_fields.get(5, CustomFieldSelectValue)

print(item.label)  # human-readable label of selected option
print(item.labels)  # all available options as list[CustomFieldSelectOptions]
```

---

## Writing custom field values

### Drafting a value from a `CustomField`

The recommended way is to call `draft_value()` on a `CustomField` instance. With the cache active, it returns the correct typed subclass:

```python
paperless.runtime.cache.custom_fields = await paperless.custom_fields.as_dict()

cf = await paperless.custom_fields(8)
new_value = cf.draft_value(42)
# new_value is CustomFieldIntegerValue(field=8, value=42)
```

### Adding a value to a document

Use `+=` or `add()` to append to a document's custom field list:

```python
document = await paperless.documents(42)

cf = await paperless.custom_fields(8)
new_value = cf.draft_value(100)

document.custom_fields += new_value
# or:
document.custom_fields.add(new_value)

await paperless.documents.update(document)
```

### Removing a value from a document

Use `-=` or `remove()`. You can pass a `CustomFieldValue`, a `CustomField` or a plain field ID:

```python
document.custom_fields -= new_value
# or:
document.custom_fields.remove(8)  # by field id
document.custom_fields.remove(cf)  # by CustomField object

await paperless.documents.update(document)
```

---

## Creating a custom field

Use `create()` and `save()` on `paperless.custom_fields`:

```python
from pypaperless.models.custom_fields import CustomFieldType

draft = paperless.custom_fields.create(
    name="Invoice amount",
    data_type=CustomFieldType.MONETARY,
)
new_id = await paperless.custom_fields.save(draft)
```

For `SELECT` fields, provide options in `extra_data`:

```python
from pypaperless.models.custom_fields import (
    CustomFieldExtraData,
    CustomFieldSelectOptions,
    CustomFieldType,
)

draft = paperless.custom_fields.create(
    name="Status",
    data_type=CustomFieldType.SELECT,
    extra_data=CustomFieldExtraData(
        select_options=[
            CustomFieldSelectOptions(id="1", label="Open"),
            CustomFieldSelectOptions(id="2", label="Closed"),
        ]
    ),
)
```
