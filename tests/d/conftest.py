"""D 与 M2 测试共用的真实数据库：一次迁移+种子，之后每个测试复制一份副本。"""

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import SEED_PATH, initialize_database
from app.common.config import Settings
from app.main import create_app


@pytest.fixture(scope="session")
def seeded_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # 种子会做 PBKDF2 派生，整个会话只构建一次数据库文件。
    path = tmp_path_factory.mktemp("seeded") / "template.sqlite3"
    initialize_database(path, seed_path=SEED_PATH)
    return path


@pytest.fixture
def seeded_settings(tmp_path: Path, seeded_template: Path) -> Settings:
    target = tmp_path / "campus.sqlite3"
    shutil.copyfile(seeded_template, target)
    return Settings(database_path=target, version="test-version")


@pytest.fixture
def seeded_client(seeded_settings: Settings):
    with TestClient(create_app(seeded_settings)) as test_client:
        yield test_client


@pytest.fixture
def login(seeded_client: TestClient):
    def _login(username: str, password: str) -> TestClient:
        response = seeded_client.post(
            "/m2/auth/login", json={"username": username, "password": password}
        )
        assert response.status_code == 200, response.text
        return seeded_client

    return _login
