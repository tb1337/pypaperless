"""Provide `User` related models."""

import datetime as dt
from typing import ClassVar

from pypaperless.const import EndpointPath
from pypaperless.models.base import IdentifiedModel


class User(IdentifiedModel):
    """Represent a Paperless `User`."""

    _api_path: ClassVar[str] = EndpointPath.USERS_SINGLE

    username: str | None = None
    # password: intentionally excluded
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    date_joined: dt.datetime | None = None
    is_staff: bool | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    groups: list[int] | None = None
    user_permissions: list[str] | None = None
    inherited_permissions: list[str] | None = None
    is_mfa_enabled: bool | None = None
