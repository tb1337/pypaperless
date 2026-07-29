"""Provide `Trash` related services."""

from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.models.documents import Document

from . import mixins
from .base import ResourceService


class TrashService(
    ResourceService,
    mixins.IterableService[Document],
):
    """Represent a factory for Paperless trashed `Document` models.

    ``/api/trash/`` declares no query filters and silently ignores the document
    ones, so :meth:`filter` supports pagination only.
    """

    _api_path = EndpointPath.TRASH
    _resource = PaperlessResource.TRASH

    _resource_cls = Document

    async def restore(self, documents: list[int]) -> None:
        """Restore the given documents from the trash.

        Args:
            documents: List of document primary keys to restore.

        Example::

            await paperless.trash.restore([10, 11])

        """
        await self._runtime.transport.post(
            self._api_path, json={"action": "restore", "documents": documents}
        )

    async def empty(self, documents: list[int] | None = None) -> None:
        """Permanently delete documents from the trash.

        Args:
            documents: List of document primary keys to permanently delete.
                       When ``None``, the entire trash is emptied.

        Example::

            await paperless.trash.empty([10, 11])  # specific documents
            await paperless.trash.empty()           # empty entire trash

        """
        payload: dict = {"action": "empty"}
        if documents is not None:
            payload["documents"] = documents
        await self._runtime.transport.post(self._api_path, json=payload)
