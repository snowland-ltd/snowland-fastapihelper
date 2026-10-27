"""User models.

Mirrors the layout of ``django.contrib.auth.models``: an abstract base carrying
the reusable fields (``AbstractUser``), a concrete default (``User``) that can be
swapped, and an account-less identity (``VirtualUser``) for flows without a real
account.

These are plain dataclasses and hold no ORM dependency, so they can be reused
with any persistence layer (see ``database.sqlalchemy``).
"""
from dataclasses import dataclass
from typing import Optional

from snowland_fastapihelper.auth.base_user import AbstractBaseUser

USER_KEY_PREFIX = "user"
VIRTUAL_KEY_PREFIX = "virtual"


@dataclass
class AbstractUser(AbstractBaseUser):
    """Reusable base for real user accounts.

    Attributes:
        uuid: business primary key of the user; points to ``users.uuid``.
        username: optional login name, kept for display and diagnostics only.
        tenant_id: optional tenant uuid; points to ``tenants.uuid``, used for
            tenant-level isolation.
        merchant_id: optional merchant uuid; points to ``merchants.uuid``, used for
            merchant-level isolation.
    """

    uuid: str
    username: Optional[str] = None
    tenant_id: Optional[str] = None
    merchant_id: Optional[str] = None

    @property
    def identity_key(self) -> str:
        return f"{USER_KEY_PREFIX}:{self.uuid}"

    def __post_init__(self) -> None:
        if not self.uuid:
            raise ValueError("uuid is required for a real user")


@dataclass
class User(AbstractUser):
    """Default concrete user model.

    Projects with their own user model should subclass ``AbstractUser`` and
    register it with ``set_user_model()``; ``get_user_model()`` then returns it.
    """


@dataclass
class VirtualUser(AbstractBaseUser):
    """An account-less (virtual) identity, e.g. a phone number before registration.

    Attributes:
        identity_type: what identifies this virtual user, e.g. ``"phone"``,
            ``"email"``, ``"device"`` or ``"session"``.
        identity_value: the concrete identifier, e.g. ``"+8613800000000"``.
        tenant_id: optional tenant uuid; points to ``tenants.uuid``.
        merchant_id: optional merchant uuid; points to ``merchants.uuid``.
    """

    identity_type: str
    identity_value: str
    tenant_id: Optional[str] = None
    merchant_id: Optional[str] = None

    @property
    def identity_key(self) -> str:
        return f"{VIRTUAL_KEY_PREFIX}:{self.identity_type}:{self.identity_value}"

    def __post_init__(self) -> None:
        if not self.identity_type or not self.identity_value:
            raise ValueError("identity_type and identity_value are required")
