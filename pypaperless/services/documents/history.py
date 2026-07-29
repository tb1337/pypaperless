"""Provide `DocumentHistory` related services."""

from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.models.documents.history import DocumentHistory

from .base import DocumentScopedServiceBase


class DocumentHistoryService(DocumentScopedServiceBase):
    """Represent a factory for Paperless `DocumentHistory` models."""

    _api_path = EndpointPath.DOCUMENTS_HISTORY
    _resource = PaperlessResource.DOCUMENTS

    _resource_cls = DocumentHistory

    async def __call__(self, pk: int | None = None) -> list[DocumentHistory]:
        """Return all history entries for a document.

        Args:
            pk: Document primary key.  May be omitted when the service is
                accessed via a :class:`~pypaperless.models.documents.document.Document`
                instance (``doc.history()``).

        Example::

            entries = await paperless.documents.history(42)
            for entry in entries:
                print(entry.action, entry.timestamp)

        """
        doc_pk = self._get_document_pk(pk)
        res = await self._runtime.transport.get(self._api_path.format(pk=doc_pk))
        return [
            self._resource_cls.from_data(self._runtime, {**item, "document": doc_pk})
            for item in res
        ]
