from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import initialize_database
from app.common.config import PROJECT_ROOT, Settings, get_settings
from app.main import create_app


def test_homepage_describes_three_pending_modules_without_creating_database(
    client: TestClient, settings: Settings
):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "校园资源服务平台" in response.text
    assert "业务功能待接入" in response.text
    for module in ("/m1", "/m2", "/m3"):
        assert module in response.text
    assert not settings.database_path.exists()


def test_stylesheet_is_served(client: TestClient):
    response = client.get("/assets/styles.css")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
    assert "@media" in response.text


def test_health_reports_initialized_database_and_actual_schema_version(
    client: TestClient, settings: Settings, empty_migrations: Path
):
    (empty_migrations / "V1__init.sql").write_text(
        "CREATE TABLE health_probe (id INTEGER PRIMARY KEY);", encoding="utf-8"
    )
    initialize_database(settings.database_path, migrations_dir=empty_migrations)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok", "schema_version": 1}


def test_health_accepts_initialized_version_zero(
    client: TestClient, settings: Settings, empty_migrations: Path
):
    initialize_database(settings.database_path, migrations_dir=empty_migrations)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["schema_version"] == 0


def test_health_rejects_missing_database_and_does_not_create_it(
    client: TestClient, settings: Settings
):
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}
    assert not settings.database_path.exists()


@pytest.mark.parametrize("contents", [b"", b"this is not a SQLite database"])
def test_health_rejects_empty_or_corrupt_files_without_overwriting_them(
    client: TestClient, settings: Settings, contents: bytes
):
    settings.database_path.write_bytes(contents)
    response = client.get("/health")
    assert response.status_code == 503
    assert settings.database_path.read_bytes() == contents
    assert str(settings.database_path) not in response.text


def test_health_rejects_directory_at_database_path(client: TestClient, settings: Settings):
    settings.database_path.mkdir()
    assert client.get("/health").status_code == 503


def test_version_uses_process_environment(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CAMPUS_VERSION", "review-1")
    monkeypatch.setenv("CAMPUS_DATABASE_PATH", str(tmp_path / "environment.sqlite3"))
    with TestClient(create_app()) as client:
        response = client.get("/version")
        assert response.status_code == 200
        assert response.json() == {"version": "review-1"}
    assert not (tmp_path / "environment.sqlite3").exists()


def test_default_configuration_is_stable_across_working_directories(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("CAMPUS_VERSION", raising=False)
    monkeypatch.delenv("CAMPUS_DATABASE_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    settings = get_settings()
    assert settings.database_path == PROJECT_ROOT / "var" / "campus.sqlite3"
    with TestClient(create_app(settings)) as client:
        assert client.get("/version").json() == {"version": "dev"}


def test_relative_database_environment_path_is_anchored_to_repository(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("CAMPUS_DATABASE_PATH", "var/custom.sqlite3")
    monkeypatch.chdir(tmp_path)
    assert get_settings().database_path == PROJECT_ROOT / "var" / "custom.sqlite3"


@pytest.mark.parametrize("path", ["/m1", "/m2", "/m3"])
def test_pending_business_modules_do_not_return_fake_success(client: TestClient, path: str):
    response = client.get(path)
    assert response.status_code == 404
