"""Provide `Task` service."""

from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Self, Unpack, cast

from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.exceptions import TaskNotFoundError
from pypaperless.models.filters import TaskFilters, TaskSummaryFilters
from pypaperless.models.tasks import Task, TaskStatusCounts, TaskSummary, TaskType

from . import mixins
from .base import ResourceService


class TaskService(
    ResourceService,
    mixins.IterableService[Task],
):
    """Represent a factory for Paperless `Task` models."""

    _api_path = EndpointPath.TASKS
    _resource = PaperlessResource.TASKS

    _resource_cls = Task

    @asynccontextmanager
    async def filter(self, **kwargs: Unpack[TaskFilters]) -> AsyncGenerator[Self]:
        """Iterate over task items with optional server-side filters.

        See :class:`~pypaperless.models.filters.TaskFilters` for available keys.
        When called with no arguments, iterates over all tasks (same as iterating directly).

        Example::

            async with paperless.tasks.filter(status=["pending", "started"]) as filtered:
                async for task in filtered:
                    print(task.task_id)

        """
        async with self._store_filters(**kwargs) as ctx:
            yield ctx

    async def __call__(self, task_id: int | str) -> Task:
        """Fetch a single task by primary key or Celery UUID.

        Args:
            task_id: An ``int`` primary key, or a ``str`` Celery task UUID.

        Example::

            task = await paperless.tasks("a1b2c3d4-...")
            task = await paperless.tasks(1337)

        """
        if isinstance(task_id, str):
            params = {
                "task_id": task_id,
            }
            res = await self._runtime.transport.get(self._api_path, params=params)
            results: list[dict[str, object]] = res.get("results", [])
            try:
                return self._resource_cls.from_data(self._runtime, results.pop())
            except IndexError as exc:
                raise TaskNotFoundError(task_id) from exc
        else:
            api_path = self._resource_cls.format_api_path(pk=task_id)
            data = await self._runtime.transport.get(api_path)
            return self._resource_cls.from_data(self._runtime, data)

    async def active(self, **kwargs: Unpack[TaskFilters]) -> AsyncIterator[Task]:
        """Iterate over currently pending and running tasks (capped at 50 server-side).

        See :class:`~pypaperless.models.filters.TaskFilters` for available keys.

        Example::

            async for task in paperless.tasks.active():
                print(task.task_id, task.status)

        """
        res = await self._runtime.transport.get(EndpointPath.TASKS_ACTIVE, params=dict(kwargs))
        for data in res:
            yield self._resource_cls.from_data(self._runtime, data)

    async def acknowledge(self, tasks: list[int]) -> int:
        """Acknowledge a list of tasks by primary key.

        Returns the number of tasks that were acknowledged.

        Args:
            tasks: List of task primary keys to acknowledge.

        Example::

            count = await paperless.tasks.acknowledge([1, 2, 3])

        """
        data = cast(
            "dict[str, object]",
            await self._runtime.transport.post(
                EndpointPath.TASKS_ACKNOWLEDGE,
                json={"tasks": tasks},
            ),
        )
        return cast("int", data["result"])

    async def summary(self, **kwargs: Unpack[TaskSummaryFilters]) -> list[TaskSummary]:
        """Return aggregated task statistics per task type.

        See :class:`~pypaperless.models.filters.TaskSummaryFilters` for available keys.
        Pass ``days=N`` to limit the aggregation window (default 30, max 365).

        Example::

            summaries = await paperless.tasks.summary(days=7)
            for s in summaries:
                print(s.task_type, s.success_count, s.failure_count)

        """
        res = await self._runtime.transport.get(
            EndpointPath.TASKS_SUMMARY, params=dict(kwargs) or None
        )
        return [TaskSummary.model_validate(data) for data in res]

    async def status_counts(self) -> TaskStatusCounts:
        """Return aggregated task counts for the task UI sections.

        Example::

            counts = await paperless.tasks.status_counts()
            print(counts.all, counts.needs_attention)

        """
        res = await self._runtime.transport.get(EndpointPath.TASKS_STATUS_COUNTS)
        return TaskStatusCounts.model_validate(res)

    async def run(self, task_type: str | TaskType) -> str:
        """Trigger a background task by type and return the resulting Celery UUID.

        Args:
            task_type: One of the :class:`~pypaperless.models.tasks.TaskType` values,
                or a plain string matching the server-side task type name.

        Example::

            task_uuid = await paperless.tasks.run(TaskType.SANITY_CHECK)
            task = await paperless.tasks(task_uuid)

        """
        data = cast(
            "dict[str, object]",
            await self._runtime.transport.post(
                EndpointPath.TASKS_RUN,
                json={"task_type": task_type},
            ),
        )
        return cast("str", data["task_id"])
