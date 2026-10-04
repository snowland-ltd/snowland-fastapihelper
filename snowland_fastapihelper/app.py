"""FastAPI application factory.

Wire up the unified-response exception handlers in one line, avoiding repeated
registration in every project.
"""
from typing import Any

from fastapi import FastAPI

from snowland_fastapihelper.exceptions import register_exception_handlers


def create_app(*args: Any, **kwargs: Any) -> FastAPI:
    """Create a FastAPI app with the unified exception handlers wired up.

    Usage is identical to native ``FastAPI(...)``, with the unified response
    exception handlers registered additionally:

        from snowland_fastapihelper import create_app
        app = create_app(title="My API")
    """
    app = FastAPI(*args, **kwargs)
    register_exception_handlers(app)
    return app
