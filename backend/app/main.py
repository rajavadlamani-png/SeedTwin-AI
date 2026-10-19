"""Expose the root FastAPI application as app.main:app for container launch."""

from main import app

__all__ = ["app"]
