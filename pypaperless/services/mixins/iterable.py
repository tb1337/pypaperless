"""IterableService for PyPaperless services."""

from collections.abc import AsyncGenerator, AsyncIterator, Mapping
from contextlib import asynccontextmanager
from contextvars import ContextVar
from types import MappingProxyType
from typing import Any, Self, TypedDict, Unpack

from pypaperless.models.base import IdentifiedT
from pypaperless.pagination import PageGenerator
from pypaperless.services.base import ResourceServiceProtocol

# Task-local query filters, keyed by service identity.  Values are immutable
# mappings that are replaced (never mutated) on entry and restored via token
# reset on exit, so concurrent asyncio tasks filtering the same (client-cached)
# service instance cannot clobber each other.
_SCOPED_FILTERS: ContextVar[Mapping[int, dict[str, Any]]] = ContextVar(
    "_SCOPED_FILTERS", default=MappingProxyType({})
)


class _BaseFilters(TypedDict, total=False):
    """Empty base TypedDict used by IterableService.filter().

    Being empty, every concrete filter TypedDict is a structural supertype
    of this class (PEP 692), so subclass overrides that narrow **kwargs to
    a specific filter TypedDict satisfy the Liskov substitution principle
    without requiring ``# type: ignore[override]``.
    """


class IterableService(ResourceServiceProtocol[IdentifiedT]):
    """Provide methods for iterating over resource items."""

    async def __aiter__(self) -> AsyncIterator[IdentifiedT]:
        """Iterate over all resource items, page by page.

        Example::

            async for item in paperless.documents:
                print(item.title)

        """
        pages = self.pages()
        try:
            async for page in pages:
                for item in page:
                    yield item
        finally:
            await pages.aclose()

    @asynccontextmanager
    async def _store_filters(self: Self, **kwargs: Any) -> AsyncGenerator[Self]:
        """Store query filters in :data:`_SCOPED_FILTERS` for the duration of the context.

        This is the private implementation backing :meth:`filter`.  Subclasses
        call ``self._store_filters(**kwargs)`` rather than ``super().filter()``
        so that the typed public override does not need to widen its signature
        back to ``**kwargs: Any``.
        """
        scoped = MappingProxyType({**_SCOPED_FILTERS.get(), id(self): kwargs})
        token = _SCOPED_FILTERS.set(scoped)
        try:
            yield self
        finally:
            _SCOPED_FILTERS.reset(token)

    @asynccontextmanager
    async def filter(
        self: Self,
        **kwargs: Unpack[_BaseFilters],
    ) -> AsyncGenerator[Self]:
        """Context manager for iterating over resource items with query parameters.

        The context variable is the service itself, scoped to the given filters.
        Use :meth:`__aiter__` or :meth:`pages` inside the block.  The filters are
        task-local — concurrent asyncio tasks filtering the same service do not
        interfere with each other.

        Example::

            async with paperless.documents.filter(
                page_size=25,
                title__icontains="2023",
            ) as filtered:
                async for item in filtered:
                    print(item.title)

                async for page in filtered.pages():
                    print(page.count)

        """
        async with self._store_filters(**kwargs) as ctx:
            yield ctx

    async def as_dict(self) -> dict[int, IdentifiedT]:
        """Return a ``{pk: model}`` mapping of all resource items.

        When used within a :meth:`filter` context, only filtered items are included.

        Example::

            docs = await paperless.documents.as_dict()
            doc = docs[42]

        """
        return {item.id: item async for item in self}

    async def as_list(self) -> list[IdentifiedT]:
        """Return a flat list of all resource items.

        When used within a :meth:`filter` context, only filtered items are included.

        Example::

            tags = await paperless.tags.as_list()

        """
        return [item async for item in self]

    def pages(
        self,
        page: int = 1,
        page_size: int = 150,
    ) -> PageGenerator[IdentifiedT]:
        """Iterate over resource pages.

        Each yielded :class:`~pypaperless.pagination.Page` contains up to
        *page_size* items.  Use within a :meth:`filter` context to apply
        server-side filters.

        Args:
            page:      Page number to start from (1-based).
            page_size: Maximum number of items per page.

        Example::

            async for page in paperless.documents.pages(page_size=50):
                print(f"Page {page.current_page} / {page.last_page}")
                for doc in page:
                    print(doc.title)

        """
        params: dict[str, Any] = dict(_SCOPED_FILTERS.get().get(id(self), {}))

        for param, value in params.items():
            # Paperless expects comma-separated values; a plain list would be sent as
            # repeated query params, of which Django only reads the last one.
            if param.endswith(("__in", "__all")) and isinstance(value, list):
                params[param] = ",".join(map(str, value))

        params.setdefault("page", page)
        params.setdefault("page_size", page_size)

        # set requesting full permissions
        if getattr(self, "request_permissions", False):
            params.update({"full_perms": "true"})

        return PageGenerator(self._runtime, self._api_path, self._resource_cls, params=params)
