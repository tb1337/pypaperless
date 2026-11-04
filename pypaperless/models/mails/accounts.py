"""Provide `MailAccount` related models."""

import datetime as dt
from enum import IntEnum
from typing import ClassVar, Self

from pypaperless.const import EndpointPath
from pypaperless.models import mixins
from pypaperless.models.base import IdentifiedModel


class ImapSecurity(IntEnum):
    """Represent a subtype of `MailAccount`."""

    NONE = 1
    SSL = 2
    STARTTLS = 3
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, *_: object) -> Self:
        """Return the UNKNOWN member for any unrecognised value."""
        return cls["UNKNOWN"]


class MailAccountType(IntEnum):
    """Represent a subtype of `MailAccount`."""

    IMAP = 1
    GMAIL_OAUTH = 2
    OUTLOOK_OAUTH = 3
    UNKNOWN = -1

    @classmethod
    def _missing_(cls, *_: object) -> Self:
        """Return the UNKNOWN member for any unrecognised value."""
        return cls["UNKNOWN"]


class MailAccount(IdentifiedModel, mixins.SecurableModel):
    """Represent a Paperless `MailAccount`."""

    _api_path: ClassVar[str] = EndpointPath.MAIL_ACCOUNTS_SINGLE

    name: str | None = None
    imap_server: str | None = None
    imap_port: int | None = None
    imap_security: ImapSecurity | None = None
    username: str | None = None
    # password:intentionally excluded
    character_set: str | None = None
    is_token: bool | None = None
    account_type: MailAccountType | None = None
    expiration: dt.datetime | None = None
