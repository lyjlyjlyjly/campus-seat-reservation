from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.common.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(database_path=tmp_path / "campus.sqlite3", version="test-version")


@pytest.fixture
def empty_migrations(tmp_path: Path) -> Path:
    path = tmp_path / "migrations"
    path.mkdir()
    return path


@pytest.fixture
def client(settings: Settings):
    with TestClient(create_app(settings)) as test_client:
        yield test_client
