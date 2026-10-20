"""D-R01 登录与会话、D-R02 固定角色权限的会话侧行为。

拒绝路径覆盖：口令错误、账号不存在、账号停用、会话过期、退出后重放旧 Cookie。
"""

import hashlib

from fastapi.testclient import TestClient

from app.common.db import connect_database


def _session_rows(settings) -> list:
    with connect_database(settings.database_path, read_only=True) as connection:
        return connection.execute(
            "SELECT token_hash, expires_at FROM session"
        ).fetchall()


def test_d_r01_login_sets_httponly_cookie_and_stores_only_hash(seeded_client: TestClient, seeded_settings):
    response = seeded_client.post(
        "/m2/auth/login", json={"username": "student01", "password": "Student#2026"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "student01"
    assert body["roles"] == ["student"]
    assert "room:apply" not in body["permissions"]

    token = response.cookies["campus_session"]
    assert response.headers["set-cookie"].lower().startswith("campus_session=")
    assert "httponly" in response.headers["set-cookie"].lower()

    rows = _session_rows(seeded_settings)
    assert len(rows) == 1
    stored = rows[0]["token_hash"]
    assert stored != token
    assert stored == hashlib.sha256(token.encode("utf-8")).hexdigest()


def test_d_r01_wrong_password_is_rejected_without_creating_session(seeded_client: TestClient, seeded_settings):
    response = seeded_client.post(
        "/m2/auth/login", json={"username": "student01", "password": "wrong-password"}
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "unauthenticated"
    assert "campus_session" not in response.cookies
    assert _session_rows(seeded_settings) == []


def test_d_r01_unknown_user_and_wrong_password_share_the_same_message(seeded_client: TestClient):
    unknown = seeded_client.post(
        "/m2/auth/login", json={"username": "no-such-user", "password": "Student#2026"}
    )
    wrong = seeded_client.post(
        "/m2/auth/login", json={"username": "student01", "password": "bad"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["message"] == wrong.json()["message"]


def test_d_r01_disabled_account_cannot_login(seeded_client: TestClient, seeded_settings):
    with connect_database(seeded_settings.database_path) as connection:
        connection.execute(
            "UPDATE app_user SET status = 'DISABLED' WHERE username = 'teacher01'"
        )
    response = seeded_client.post(
        "/m2/auth/login", json={"username": "teacher01", "password": "Teacher#2026"}
    )
    assert response.status_code == 401
    assert _session_rows(seeded_settings) == []


def test_d_r01_logout_makes_the_old_cookie_useless(seeded_client: TestClient):
    seeded_client.post(
        "/m2/auth/login", json={"username": "teacher01", "password": "Teacher#2026"}
    )
    assert seeded_client.get("/m2/auth/me").status_code == 200

    stale_token = seeded_client.cookies["campus_session"]
    logout = seeded_client.post("/m2/auth/logout")
    assert logout.status_code == 200
    assert logout.json()["revoked"] is True

    # 浏览器已删 Cookie，这里模拟有人重放旧值。
    seeded_client.cookies.set("campus_session", stale_token)
    replay = seeded_client.get("/m2/auth/me")
    assert replay.status_code == 401
    assert replay.json()["error"] == "unauthenticated"


def test_d_r01_expired_session_is_rejected(seeded_client: TestClient, seeded_settings):
    seeded_client.post(
        "/m2/auth/login", json={"username": "approver01", "password": "Approver#2026"}
    )
    with connect_database(seeded_settings.database_path) as connection:
        connection.execute(
            "UPDATE session SET expires_at = '2000-01-01T00:00:00Z'"
        )
    response = seeded_client.get("/m2/auth/me")
    assert response.status_code == 401
    assert response.json()["error"] == "unauthenticated"
