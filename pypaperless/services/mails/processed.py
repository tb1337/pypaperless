"""Provide `ProcessedMail` related services."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Self, Unpack

from pypaperless.const import EndpointPath, PaperlessResource
from pypaperless.models.filters import ProcessedMailFilters
from pypaperless.models.mails.processed import ProcessedMail
from pypaperless.services import mixins
from pypaperless.services.base import ResourceService


class ProcessedMailService(
    ResourceService,
    mixins.SecurableService,
    mixins.CallableService[ProcessedMail],
    mixins.IterableService[ProcessedMail],
):
    """Represent a factory for Paperless `ProcessedMail` models."""

    _api_path = EndpointPath.PROCESSED_MAIL
    _resource = PaperlessResource.PROCESSED_MAIL

    _resource_cls = ProcessedMail

    @asynccontextmanager
    async def filter(self, **kwargs: Unpack[ProcessedMailFilters]) -> AsyncGenerator[Self]:
        """Iterate processed mails with server-side filters.

        See :class:`~pypaperless.models.filters.ProcessedMailFilters` for all available keys.

        Example::

            async with paperless.processed_mail.filter(status="FAILED") as filtered:
                async for entry in filtered:
                    print(entry.subject, entry.error)

        """
        async with self._store_filters(**kwargs) as ctx:
            yield ctx
