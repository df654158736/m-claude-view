"""HTTP interface adapter."""

from src.interfaces.http.main import build_handler, create_app, main

__all__ = ["create_app", "build_handler", "main"]
