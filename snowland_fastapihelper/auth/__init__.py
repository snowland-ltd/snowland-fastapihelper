"""Identity / user primitives, modelled after ``django.contrib.auth``.

This package owns everything identity related (user classes, the account-less
virtual user, and the swappable user model) so that features such as captcha can
depend on it without defining user classes themselves.

Typical use::

    from snowland_fastapihelper.auth import User, VirtualUser, get_user_model

    user = get_user_model()(uuid="u-1", merchant_id="m-1")
"""
from typing import Type

from snowland_fastapihelper.auth.base_user import AbstractBaseUser
from snowland_fastapihelper.auth.models import AbstractUser, User, VirtualUser

# Active user model; swappable via set_user_model().
_user_model: Type[AbstractUser] = User


def get_user_model() -> Type[AbstractUser]:
    """Return the user model currently in use.

    Defaults to ``User``; returns whatever was registered via ``set_user_model()``.
    """
    return _user_model


def set_user_model(model: Type[AbstractUser]) -> None:
    """Swap the active user model.

    Args:
        model: a concrete ``AbstractUser`` subclass.

    Raises:
        TypeError: if ``model`` is not an ``AbstractUser`` subclass.
    """
    global _user_model
    if not (isinstance(model, type) and issubclass(model, AbstractUser)):
        raise TypeError("user model must be a subclass of AbstractUser")
    _user_model = model


__all__ = [
    "AbstractBaseUser",
    "AbstractUser",
    "User",
    "VirtualUser",
    "get_user_model",
    "set_user_model",
]
