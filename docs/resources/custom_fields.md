# Custom Fields

Custom fields let you attach arbitrary typed metadata to documents. This page covers managing the field definitions themselves. For reading and writing field *values* on documents, see [Custom Fields concepts](../concepts/custom_fields.md).

## Models

See [`pypaperless/models/custom_fields.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/custom_fields.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/pypaperless/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch one

```python
field = await paperless.custom_fields(3)
print(field.name)       # "Invoice amount"
print(field.data_type)  # CustomFieldType.MONETARY
```

## Iterate

```python
async for field in paperless.custom_fields:
    print(field.id, field.name, field.data_type)

# Keyed by id
fields = await paperless.custom_fields.as_dict()
```

## Create

```python
from pypaperless.models.custom_fields import CustomFieldType

draft = paperless.custom_fields.create()
draft.name = "Invoice amount"
draft.data_type = CustomFieldType.MONETARY

pk = await paperless.custom_fields.save(draft)
```

For a `select` field, provide the allowed options via `extra_data`:

```python
from pypaperless.models.custom_fields import (
    CustomFieldDraft,
    CustomFieldExtraData,
    CustomFieldSelectOptions,
    CustomFieldType,
)

draft = paperless.custom_fields.create()
draft.name = "Priority"
draft.data_type = CustomFieldType.SELECT
draft.extra_data = CustomFieldExtraData(
    select_options=[
        CustomFieldSelectOptions(label="Low"),
        CustomFieldSelectOptions(label="Medium"),
        CustomFieldSelectOptions(label="High"),
    ]
)

pk = await paperless.custom_fields.save(draft)
```

## Update

```python
field = await paperless.custom_fields(3)
field.name = "Invoice total"
changed = await paperless.custom_fields.update(field)
```

## Delete

```python
field = await paperless.custom_fields(3)
await paperless.custom_fields.delete(field)
```

Raises `DeletionError` on failure. Pass `silent_fail=True` to suppress it.
