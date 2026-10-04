"""Backend registry: maps session types to the corresponding ORM's CRUD factory.

Business code only depends on the single entry point ``get_crud(model, session)``
and does not care which ORM is underneath. To add a new ORM, call
``register_backend`` in the corresponding subpackage (the SQLAlchemy backend
self-registers in ``snowland_fastapihelper.database.sqlalchemy``).

This file does not depend on any ORM and can be imported standalone.
"""
import inspect
from typing import Any, Callable, Dict, Tuple, Type

from snowland_fastapihelper.database.base import CRUDProtocol

# Factory signature: (model, session) -> CRUDProtocol instance
BackendFactory = Callable[[Any, Any], CRUDProtocol]


class BackendRegistry:
    """Holds the ``session type -> backend CRUD factory`` mapping and dispatches."""

    def __init__(self) -> None:
        # session type -> (backend name, factory)
        self._by_session: Dict[type, Tuple[str, BackendFactory]] = {}
        # backend name -> (session type, factory)
        self._by_name: Dict[str, Tuple[type, BackendFactory]] = {}

    def register(
        self, name: str, session_type: Type[Any], factory: BackendFactory
    ) -> None:
        """Register a backend. ``session_type`` is used for automatic dispatch."""
        self._by_session[session_type] = (name, factory)
        self._by_name[name] = (session_type, factory)

    def get_factory(self, session: Any, *, backend: str = None) -> BackendFactory:
        if backend is not None:
            if backend not in self._by_name:
                raise KeyError(
                    f"unregistered database backend: {backend!r}; "
                    f"registered: {sorted(self._by_name)}"
                )
            return self._by_name[backend][1]

        session_type = type(session)
        if session_type in self._by_session:
            return self._by_session[session_type][1]
        # Supports custom session subclasses (e.g. subclasses of AsyncSession)
        for cls in inspect.getmro(session_type):
            if cls in self._by_session:
                return self._by_session[cls][1]
        raise TypeError(
            f"no registered database backend for session type {session_type!r}; "
            f"import the corresponding ORM subpackage "
            f"(e.g. snowland_fastapihelper.database.sqlalchemy), "
            f"or pass backend= explicitly."
        )

    def get_crud(
        self, model: Any, session: Any, *, backend: str = None
    ) -> CRUDProtocol:
        factory = self.get_factory(session, backend=backend)
        return factory(model, session)


# The single global registry instance
registry = BackendRegistry()


def register_backend(
    name: str, session_type: Type[Any], factory: BackendFactory
) -> None:
    """Register a CRUD factory for an ORM backend (used for self-registration)."""
    registry.register(name, session_type, factory)


def get_crud(model: Any, session: Any, *, backend: str = None) -> CRUDProtocol:
    """Unified entry point: return the CRUD helper for the ORM backend matching the
    session type.

    Dispatch is automatic by ``type(session)`` by default; an explicit
    ``backend=`` name can also be given.
    """
    return registry.get_crud(model, session, backend=backend)
