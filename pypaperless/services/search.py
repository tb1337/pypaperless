"""Provide `Search` service."""

from typing import cast

from pypaperless.builders import SearchQuery
from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.models.search import SearchResult

from .base import ResourceService


class SearchService(ResourceService):
    """Represent a factory for Paperless global search results."""

    _api_path = EndpointPath.SEARCH
    _resource = PaperlessResource.SEARCH

    _resource_cls = SearchResult

    async def __call__(
        self,
        query: str | SearchQuery,
        *,
        db_only: bool | None = None,
    ) -> SearchResult:
        """Perform a global search and return a ``SearchResult``.

        Args:
            query:   The search query — a plain Whoosh string or a
                     :class:`~pypaperless.builders.search.SearchQuery` builder object.
            db_only: When ``True``, only the database is searched (no
                     full-text index).  Defaults to ``None`` (server decides).

        Example::

            # Plain string
            result = await paperless.search("invoice")

            # Builder
            from pypaperless.models.types import SearchQuery
            q = SearchQuery("invoice") & SearchQuery.field("tag", "unpaid")
            result = await paperless.search(q)

        """
        params: dict[str, str | bool] = {"query": str(query)}
        if db_only is not None:
            params["db_only"] = db_only
        res = await self._runtime.transport.get(self._api_path, params=params)
        return self._resource_cls.from_data(self._runtime, res)

    async def autocomplete(self, term: str, limit: int | None = None) -> list[str]:
        """Return full-text index terms completing a partial search term.

        This is the typeahead helper behind the Paperless-ngx search bar — it
        answers with bare strings from the search index, not resource objects.

        Args:
            term:  Prefix to complete.  An empty term is rejected by the server
                   with HTTP 400, surfacing as
                   :exc:`~pypaperless.exceptions.UnexpectedStatusError`.
            limit: Maximum number of terms to return.  Defaults to ``None``,
                   which omits the parameter and leaves the server default (10)
                   in place.  Values below ``1`` are rejected by the server.

        Example::

            terms = await paperless.search.autocomplete("inv")
            # ["invoice", "invoices", "invoiced"]

            terms = await paperless.search.autocomplete("inv", limit=3)

        """
        params: dict[str, str | int] = {"term": term}
        if limit is not None:
            params["limit"] = limit
        res = await self._runtime.transport.get(EndpointPath.SEARCH_AUTOCOMPLETE, params=params)
        return cast("list[str]", res)
