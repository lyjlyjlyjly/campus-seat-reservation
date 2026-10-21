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


@pytest.fixture(scope="session")
def seeded_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """全量迁移 + 种子的模板库；种子含 PBKDF2，整个会话只构建一次。"""
    from app.bootstrap import SEED_PATH, initialize_database

    path = tmp_path_factory.mktemp("seeded") / "template.sqlite3"
    initialize_database(path, seed_path=SEED_PATH)
    return path


@pytest.fixture
def seeded_settings(tmp_path: Path, seeded_template: Path) -> Settings:
    """每个测试复制一份模板库，互不影响，也不读开发库。"""
    import shutil

    target = tmp_path / "campus.sqlite3"
    shutil.copyfile(seeded_template, target)
    return Settings(database_path=target, version="test-version")


@pytest.fixture
def seeded_client(seeded_settings: Settings):
    with TestClient(create_app(seeded_settings)) as test_client:
        yield test_client


@pytest.fixture
def login(seeded_client: TestClient):
    """用演示账号登录，返回同一个已持有会话 Cookie 的客户端。

    客户端只有一个 Cookie：同一测试内切换账号会顶掉上一个会话，
    需要换角色时重新调用 login，并在注释里写清当前身份。
    """

    def _login(username: str, password: str) -> TestClient:
        response = seeded_client.post(
            "/m2/auth/login", json={"username": username, "password": password}
        )
        assert response.status_code == 200, response.text
        return seeded_client

    return _login
