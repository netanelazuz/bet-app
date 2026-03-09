"""Pytest fixtures for BET app. Set env before any app import so Config uses SQLite."""
import os

os.environ["SECRET_KEY"] = "test-secret"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from app import create_app, db


@pytest.fixture(scope="function")
def app():
    application = create_app()
    application.config["TESTING"] = True
    application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    return application


@pytest.fixture(scope="function")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def init_db(app):
    with app.app_context():
        db.create_all()
        yield
        db.drop_all()
