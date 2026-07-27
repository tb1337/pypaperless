# Tasks

Tasks represent Celery background jobs - primarily document consumption jobs. You can look up a task by its UUID (returned when uploading a document) or by its integer primary key, and iterate over all tasks.

## Model

See [`pypaperless/models/tasks.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/tasks.py) for all fields and [`pypaperless/models/types.py`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/types.py) for enum and filter types, and the [Paperless-ngx API docs](https://docs.paperless-ngx.com/api/) for the upstream schema.

## Fetch by UUID

The primary use-case is monitoring a document upload by its task UUID:

```python
# task_uuid was returned by paperless.documents.save(draft)
task = await paperless.tasks(task_uuid)

print(task.status)  # TaskStatus.PENDING / STARTED / SUCCESS / FAILURE
print(task.related_document_ids)  # [42]  - list of document pks once finished
```

## Fetch by primary key

```python
task = await paperless.tasks(1337)
print(task.task_type)  # TaskType.CONSUME_FILE
```

## Poll until complete

```python
import asyncio
from pypaperless.models.tasks import TaskStatus

task_uuid = await paperless.documents.save(draft)

while True:
    task = await paperless.tasks(task_uuid)
    if task.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE):
        break
    await asyncio.sleep(1)

if task.status == TaskStatus.SUCCESS and task.related_document_ids:
    doc = await paperless.documents(task.related_document_ids[0])
    print("Uploaded:", doc.title)
else:
    print("Upload failed:", task.result_data)
```

## Iterate

```python
async for task in paperless.tasks:
    print(task.task_id, task.status)

# Collect all pending tasks
pending = [t async for t in paperless.tasks if t.status == "pending"]
```

## Filter

`filter()` is an async context manager - apply server-side filters within `async with` and iterate over the yielded `ctx`. See [`TaskFilters`](https://github.com/tb1337/paperless-api/blob/main/pypaperless/models/filters.py) for all keys.

```python
from pypaperless.models.tasks import TaskStatus, TaskType

# Only tasks with a specific status
async with paperless.tasks.filter(status=[TaskStatus.SUCCESS]) as ctx:
    async for task in ctx:
        print(task.task_id, task.result_data)

# Only unacknowledged consumption tasks
async with paperless.tasks.filter(
    acknowledged=False,
    task_type=[TaskType.CONSUME_FILE],
) as ctx:
    async for task in ctx:
        print(task.task_id)
```

## Active tasks

`active()` iterates over currently pending or running tasks (capped at 50 by the server):

```python
async for task in paperless.tasks.active():
    print(task.task_id, task.status)
```

## Summary statistics

`summary()` returns aggregated counts and durations per task type, optionally scoped to a rolling time window:

```python
summaries = await paperless.tasks.summary(days=7)
for s in summaries:
    print(s.task_type, s.success_count, s.failure_count, s.avg_duration_seconds)
```

## Status counts

`status_counts()` returns the aggregated task counts used by the task UI sections:

```python
counts = await paperless.tasks.status_counts()
print(counts.all, counts.needs_attention, counts.in_progress, counts.completed)
```

## Acknowledge tasks

Acknowledgement happens on the service - pass the list of primary keys to acknowledge:

```python
count = await paperless.tasks.acknowledge([1, 2, 3])
print("Acknowledged:", count)
```

## Run task

`run()` schedules a fresh background task by type and returns the new Celery UUID as a string:

```python
from pypaperless.models.tasks import TaskType

task_uuid = await paperless.tasks.run(TaskType.SANITY_CHECK)
task = await paperless.tasks(task_uuid)
print(task.status)
```
