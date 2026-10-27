"""Minimal identity contract.

Mirrors ``django.contrib.auth.base_user.AbstractBaseUser``: it defines only what
every identity in the system must provide, without any storage or framework
coupling. Features such as captcha bind to this contract instead of owning user
definitions themselves.
"""
from abc import ABC, abstractmethod


class AbstractBaseUser(ABC):
    """Minimal contract for anything a credential / code / token is issued for."""

    @property
    @abstractmethod
    def identity_key(self) -> str:
        """Stable, unique key identifying this identity.

        Used by consumers (captcha cache keys, token subjects, ...) as the
        namespace under which identity-bound data is stored.
        """
        ...
