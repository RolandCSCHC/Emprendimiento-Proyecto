"""Fixtures compartidos para los tests."""

from __future__ import annotations

import pytest

from app import create_app


@pytest.fixture
def app():
    """App Flask configurada para tests (AWS deshabilitado)."""
    flask_app = create_app("testing")
    with flask_app.app_context():
        yield flask_app


@pytest.fixture
def client(app):
    """Cliente HTTP de test."""
    return app.test_client()
