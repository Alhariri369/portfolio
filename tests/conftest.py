"""Shared pytest fixtures.

The environment is configured before any app import so the module-level engine
in app.db points at a throwaway SQLite file instead of the developer's own DB.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="portfolio-test-env-"))
os.environ["DATABASE_URL"] = "sqlite:///" + str(_TMP / "app.db").replace("\\", "/")
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-secret"
os.environ["RESEND_API_KEY"] = ""
os.environ["CF_ANALYTICS_TOKEN"] = ""

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.db import Base  # noqa: E402


@pytest.fixture
def engine():
    tmp = Path(tempfile.mkdtemp(prefix="portfolio-test-db-"))
    url = "sqlite:///" + str(tmp / "test.db").replace("\\", "/")
    eng = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine):
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


@pytest.fixture
def client(engine, session_factory):
    from fastapi.testclient import TestClient

    from app.main import app, get_db

    def override():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
