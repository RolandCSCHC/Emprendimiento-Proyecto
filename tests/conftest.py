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


@pytest.fixture
def db_session(app):
    """
    Crea el esquema y entrega la sesión de DB; limpia al terminar.

    Requiere una DB con tipos PostgreSQL (UUID/JSONB). Para correr estos tests
    usar ``TEST_DATABASE_URL`` apuntando a Postgres (ver docker-compose).
    """
    from app.extensions import db

    db.create_all()
    yield db.session
    db.session.remove()
    db.drop_all()
