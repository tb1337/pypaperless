---
name: pp-update-filters
description: "Update the query filter TypedDicts in pypaperless/models/filters.py by reading the paperless-ngx source FilterSets, then sync the service filter() overrides and the docs. Use whenever paperless-ngx adds, renames, or removes filter fields."
argument-hint: "Optional: name of a specific resource to update (e.g. Document, Tag). Omit to update all."
---

# Update Query Filters in pypaperless

## When to Use

- paperless-ngx added or changed filter fields
- A new resource needs a typed `filter()` override
- `ruff` or `mypy` reports issues in `pypaperless/models/filters.py`

## Files Involved

| File | Purpose |
| --- | --- |
| `pypaperless/models/filters.py` | TypedDicts — one per filterable resource |
| `pypaperless/models/types.py` | Re-exports all filter TypedDicts |
| `pypaperless/services/<name>.py` | `filter()` override with `Unpack[XxxFilters]` |
| `docs/resources/<name>.md` | Per-resource filter examples |

---

## Step 1 — Read the filter fields

**Primary:** `tests/data/schema.json` — fetch first to ensure it's current:

```bash
uv run python script/pngx_fetch_schema.py
```

For each list endpoint collect every `"in": "query"` parameter. Exclude: `page`, `page_size`, `format`, `ordering`, `full_perms`.

**Fallback:** upstream source — only for fields the schema omits (known case: `more_like_id` on `DocumentFilters`):

```bash
curl -sL https://raw.githubusercontent.com/paperless-ngx/paperless-ngx/dev/src/documents/filters.py
```

### Schema type → Python type

| Schema type | Python type |
| --- | --- |
| `integer` | `int` |
| `boolean` | `bool` |
| `string` / `string+date` / `string+date-time` | `str` |
| `number` | `int` (date/time components) |
| `array[integer]` | `str` — comma-separated PKs; **do not change to `list[int]`** |
| `array[string+enum]` | `EnumType \| str \| list[EnumType \| str]` |

Schema bug: `shared_by__id` is `boolean` in the schema — keep `int` in the TypedDict.

---

## Step 2 — Update `pypaperless/models/filters.py`

### FilterSet → TypedDict

| paperless-ngx FilterSet | pypaperless TypedDict |
| --- | --- |
| `CorrespondentFilterSet` | `CorrespondentFilters` |
| `TagFilterSet` | `TagFilters` |
| `DocumentTypeFilterSet` | `DocumentTypeFilters` |
| `StoragePathFilterSet` | `StoragePathFilters` |
| `CustomFieldFilterSet` | `CustomFieldFilters` |
| `DocumentFilterSet` | `DocumentFilters` |
| `PaperlessTaskFilterSet` | `TaskFilters` |
| `ShareLinkFilterSet` | `ShareLinkFilters` |

Not every filterable resource maps to a dedicated upstream FilterSet. `GroupFilters`, `UserFilters`,
`ProcessedMailFilters`, `ShareLinkBundleFilters` and `TaskSummaryFilters` are pypaperless-composed
(they extend the private bases or another TypedDict) — take their fields from `schema.json`
(Step 1), not from a row above.

`PaperlessTaskFilterSet.name` and `.result` are `CharFilter(method=…)` free-text searches, not
exact matches — keep the inline comments in `TaskFilters` that say so.

### Style rules

- `total=False` on every class.
- No `page` / `page_size` fields.
- No section-header comments (ERA001).
- Fields sorted **alphabetically**. Classes sorted **alphabetically**; private bases (`_CreatedFilters`, `_IdFilters`, `_ExpirationFilters`, `_NameFilters`, `_NameIdFilters`) always first.
- Use a pypaperless enum type instead of plain `str` whenever the schema documents a fixed value set for a field. Pattern: `XxxEnum | str` for single-value fields; `XxxEnum | str | list[XxxEnum | str]` for array fields. Import the enum directly from its model module (not from `types.py`).
- Inline comments only for non-obvious semantics: `# comma-separated PKs`, `# JSON expression`, `# True → has at least one tag`, etc.
- No blank lines between fields.

### Inheritance rules

**Absolute rule: no field may appear in more than one public TypedDict.** Whenever identical fields exist in two or more classes, extract them into a new private base `_XxxFilters`.

Always use the narrowest fitting base.

| Situation | Inherit from |
| --- | --- |
| Resource has `id` + `name__*` | `_NameIdFilters` |
| Resource has `name__*` only | `_NameFilters` |
| Resource has `id` only | `_IdFilters` |
| Resource has `created__*` date range | `_CreatedFilters` |
| Resource has `expiration__*` date range | `_ExpirationFilters` |
| Resource has both id and created | `_IdFilters, _CreatedFilters` |
| Resource has created + expiration | `_CreatedFilters, _ExpirationFilters` |

Current private bases and what they provide:

| Base | Fields provided |
| --- | --- |
| `_IdFilters` | `id`, `id__in` |
| `_NameFilters` | `name__icontains/iendswith/iexact/istartswith` |
| `_NameIdFilters(_IdFilters, _NameFilters)` | both of the above |
| `_CreatedFilters` | `created__date__gt/gte/lt/lte`, `created__day/month/year`, `created__gt/gte/lt/lte` |
| `_ExpirationFilters` | same fields with `expiration__` prefix |

`groups` is the only name-filterable resource without `id`/`id__in` — it inherits `_NameFilters`
directly, every other named resource uses `_NameIdFilters`. Re-verify against `schema.json`
before moving a class between the two.

A class body with only a docstring is correct when the base covers everything.
When adding a new date-range field group that would appear in ≥ 2 classes, create a new private base first.

---

## Step 3 — Update `pypaperless/models/types.py`

Import the new TypedDict and add it to `__all__` in alphabetical order.

---

## Step 4 — Update service `filter()` overrides

Pattern (identical for every service):

```python
@asynccontextmanager
async def filter(self, **kwargs: Unpack[XxxFilters]) -> AsyncGenerator[Self]:
    """Iterate with server-side filters.

    See :class:`~pypaperless.models.filters.XxxFilters` for available keys.
    """
    async with self._store_filters(**kwargs) as ctx:
        yield ctx
```

Always call `self._store_filters(**kwargs)` — never `super().filter(**kwargs)`.

### Service → Filters

| Service | TypedDict |
| --- | --- |
| `CorrespondentService` | `CorrespondentFilters` |
| `CustomFieldService` | `CustomFieldFilters` |
| `DocumentService` | `DocumentFilters` |
| `DocumentTypeService` | `DocumentTypeFilters` |
| `GroupService` | `GroupFilters` |
| `ProcessedMailService` | `ProcessedMailFilters` |
| `ShareLinkBundleService` | `ShareLinkBundleFilters` |
| `ShareLinkService` | `ShareLinkFilters` |
| `StoragePathService` | `StoragePathFilters` |
| `TagService` | `TagFilters` |
| `TaskService` | `TaskFilters` |
| `UserService` | `UserFilters` |

No override for: `SavedViewService`, `WorkflowService`, `MailAccountService`, `MailRuleService`, `TrashService`.

`TrashService` deliberately has none: `/api/trash/` declares zero query parameters and silently
ignores document filters (verified live — identical `count` with and without a filter), so it keeps
the pagination-only base `filter()`.

`TaskService` additionally exposes two typed methods that must be kept in sync alongside `filter()`:
`active(**Unpack[TaskFilters])` and `summary(**Unpack[TaskSummaryFilters])`. `TaskSummaryFilters`
extends `TaskFilters` (adds `days: int`); when `TaskFilters` fields change, both methods follow
automatically, but a summary-only field belongs on `TaskSummaryFilters`.

---

## Step 5 — Update docs

Only update `docs/resources/<name>.md` files that already have a `filter()` example — do not create new doc files.

---

## Step 6 — Add or Update Tests

**`tests/test_filters.py`** — add a row to the `test_service_filter_accepts_typed_kwargs` parametrize table **and** the matching entry in its `ids` list: an `(api_key, service_attr, filter_kwargs, mock_data)` tuple where `filter_kwargs` uses a key specific to the new TypedDict and `mock_data` is the resource's `DATA_*` fixture (import it at the top).

**`tests/test_service_mixins.py`** — add an HTTP-level test for the new service's `filter()` using a key specific to that TypedDict.

**`script/pngx_smoketest.py`** — add a live call inside `test_filter_context` using a safe, read-only filter key.

---

## Step 7 — Validate

```bash
uv run pytest -x -q
uv run python script/pngx_smoketest.py
uv run python script/pngx_audit_coverage.py
```

---

## Common Mistakes

- Repeating `id`/`id__in` or `name__*` in a class that inherits `_NameFilters`.
- Repeating `created__*` in a class that inherits `_CreatedFilters`.
- Adding `page` / `page_size` to a TypedDict.
- Adding section-header comments inside TypedDicts (ERA001).
- Sorting fields non-alphabetically.
- Using `TypeVar` with `Unpack` (not supported by PEP 692).
- Calling `super().filter(**kwargs)` instead of `self._store_filters(**kwargs)`.
- Forgetting to add the resource's row to the `test_service_filter_accepts_typed_kwargs` parametrize table (and its `ids` list) in `tests/test_filters.py`.
