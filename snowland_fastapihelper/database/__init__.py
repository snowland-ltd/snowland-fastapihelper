"""Database abstraction layer (ORM-agnostic) unified entry point.

Goal: hide the differences between underlying ORMs so business code only depends
on a unified interface::

    from snowland_fastapihelper.database import get_crud
    crud = get_crud(User, session)   # session comes from the ORM in use

Concrete ORMs implement ``base.CRUDProtocol`` in their own subpackages and
self-register with the registry:

* SQLAlchemy backend: ``snowland_fastapihelper.database.sqlalchemy``
  (importing this subpackage auto-registers it; available when sqlalchemy is installed).

To add support for another ORM (e.g. Tortoise / Piccolo), implement
``CRUDProtocol`` and call ``register_backend(name, SessionType, factory)`` in the
corresponding subpackage; the ``get_crud`` call in business code stays unchanged.

This file and the ``base`` / ``backends`` it imports do not depend on any ORM and
can be imported standalone.
"""
from snowland_fastapihelper.database.backends import (
    BackendRegistry,
    get_crud,
    register_backend,
)
from snowland_fastapihelper.database.base import CRUDProtocol

__all__ = [
    "CRUDProtocol",
    "get_crud",
    "register_backend",
    "BackendRegistry",
]
