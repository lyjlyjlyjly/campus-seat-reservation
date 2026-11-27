from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException

from app.common.config import Settings
from app.common.db import connect_database
from app.main import create_app
from app.m3 import identity as m3_identity
from app.m3.identity import authenticated_reporter
from app.m3.repository import get_repair_order


def payload(**changes):
    return dict(room_id=10, fault_type="ELECTRICAL", description="灯管闪烁", **changes)


def count(database):
    with connect_database(database, read_only=True) as connection:
        return connection.execute("SELECT count(*) FROM repair_order").fetchone()[0]


def test_m3_r01_post_commits_server_identity_state_time_and_normalized_text(report_client, report_database):
    before = datetime.now(timezone.utc).replace(microsecond=0)
    response = report_client.post("/m3/work-orders", json={
        "room_id": 10, "fault_type": "\t WATER \n", "description": "\u3000洗手台  漏水\n第二处也漏'; DROP TABLE room; -- \n",
    }, headers={"X-User-Id": "2"})
    after = datetime.now(timezone.utc).replace(microsecond=0)
    assert response.status_code == 201
    result = response.json()
    assert set(result) == {"id", "status", "created_at"}
    assert result["status"] == "REPORTED"
    assert before <= datetime.fromisoformat(result["created_at"].replace("Z", "+00:00")) <= after
    saved = get_repair_order(report_database, result["id"])
    assert saved["reporter_id"] == 1
    assert saved["fault_type"] == "WATER"
    assert saved["description"] == "洗手台  漏水\n第二处也漏'; DROP TABLE room; --"
    assert saved["created_at"] == saved["updated_at"] == result["created_at"]
    assert all(saved[field] is None for field in ("assigned_to", "assigned_by", "assigned_at", "started_at"))
    assert count(report_database) == 1


def test_m3_r01_real_room_list_and_inactive_room_creation(report_client, report_database):
    response = report_client.get("/m3/rooms")
    assert response.status_code == 200
    assert sorted(response.json()["items"], key=lambda row: row["id"]) == [
        {"id": 10, "name": "测试教室", "is_active": 1},
        {"id": 20, "name": "测试停借教室", "is_active": 0},
    ]
    response = report_client.post("/m3/work-orders", json={"room_id": 20, "fault_type": "OTHER", "description": "窗户破损"})
    assert response.status_code == 201
    assert get_repair_order(report_database, response.json()["id"])["room_id"] == 20
    with connect_database(report_database) as connection:
        assert connection.execute("SELECT is_active FROM room WHERE id=20").fetchone()[0] == 0


@pytest.mark.parametrize("kind,expected", [("unauthenticated", 401), ("no-permission", 403), ("disabled", 401), ("missing", 401)])
def test_m3_r01_reject_identity_and_permission_for_list_and_create(report_app, report_client, report_database, kind, expected):
    if kind == "unauthenticated":
        def unauthenticated():
            raise HTTPException(401, "private G2 diagnostic")
        report_app.dependency_overrides[authenticated_reporter] = unauthenticated
    elif kind == "missing":
        report_app.dependency_overrides[authenticated_reporter] = lambda: 9999
    else:
        with connect_database(report_database) as connection:
            if kind == "disabled":
                connection.execute("UPDATE app_user SET status='DISABLED' WHERE id=1")
            else:
                connection.execute("DELETE FROM user_role WHERE user_id=1")
    for response in [report_client.get("/m3/rooms"), report_client.post("/m3/work-orders", json=payload())]:
        assert response.status_code == expected
        assert set(response.json()) == {"error", "message"}
        assert "private" not in response.text
    assert count(report_database) == 0


@pytest.mark.parametrize("change,expected", [("revoke", 403), ("disable", 401)])
def test_m3_r01_transaction_rechecks_changes_after_authentication(report_app, report_client, report_database, change, expected):
    def identity_snapshot_then_change():
        # 模拟真实认证已经得到了身份快照，随后另一连接已提交撤权/禁用。
        with connect_database(report_database) as connection:
            if change == "revoke":
                connection.execute("DELETE FROM role_permission WHERE permission_id=(SELECT id FROM permission WHERE code='repair:report')")
            else:
                connection.execute("UPDATE app_user SET status='DISABLED' WHERE id=1")
        return 1
    report_app.dependency_overrides[authenticated_reporter] = identity_snapshot_then_change
    response = report_client.post("/m3/work-orders", json=payload())
    assert response.status_code == expected
    assert count(report_database) == 0


@pytest.mark.parametrize("field,value", [
    ("room_id", True), ("room_id", 10.0), ("room_id", "10"), ("room_id", 0), ("room_id", -1), ("room_id", None),
    ("room_id", 9999), ("room_id", 2**80),
    ("fault_type", None), ("fault_type", 1), ("fault_type", True), ("fault_type", []),
    ("fault_type", "electrical"), ("fault_type", "UNKNOWN"), ("fault_type", "  "),
    ("description", None), ("description", 1), ("description", False), ("description", {}),
    ("description", " \n\t\u3000"), ("description", "x\x00y"), ("description", "中" * 1001),
])
def test_m3_r01_invalid_request_does_not_insert(report_client, report_database, field, value):
    data = payload()
    data[field] = value
    response = report_client.post("/m3/work-orders", json=data)
    assert response.status_code == 422
    assert set(response.json()) == {"error", "message"}
    assert count(report_database) == 0


@pytest.mark.parametrize("field", ["reporter_id", "status", "assigned_to", "assigned_by", "created_at", "updated_at", "seat_id"])
def test_m3_r01_forbids_identity_state_time_and_unsupported_extra_fields(report_client, report_database, field):
    data = payload()
    data[field] = 2
    response = report_client.post("/m3/work-orders", json=data)
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"
    assert count(report_database) == 0


@pytest.mark.parametrize("field", ["room_id", "fault_type", "description"])
def test_m3_r01_missing_fields(report_client, report_database, field):
    data = payload()
    del data[field]
    assert report_client.post("/m3/work-orders", json=data).status_code == 422
    assert count(report_database) == 0


@pytest.mark.parametrize("text", ["中", "中" * 1000, "💡" * 1000, "第一排  左侧\n\n灯管闪烁", "\ufeff"])
def test_m3_r01_unicode_codepoints_and_internal_whitespace(report_client, report_database, text):
    data = payload()
    data["description"] = "\x1c\u0085" + text + "\u3000\n"
    response = report_client.post("/m3/work-orders", json=data)
    assert response.status_code == 201
    assert get_repair_order(report_database, response.json()["id"])["description"] == text


@pytest.mark.parametrize("body", ['{', '[]', '{"room_id":10,"fault_type":"OTHER","description":"\\ud800"}'])
def test_m3_r01_bad_json_or_unencodable_unicode_is_422(report_client, report_database, body):
    response = report_client.post("/m3/work-orders", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert count(report_database) == 0


def test_m3_r01_failed_real_sql_transaction_preserves_existing_data(report_client, report_database):
    original = report_client.post("/m3/work-orders", json=payload()).json()["id"]
    before = get_repair_order(report_database, original)
    with connect_database(report_database) as connection:
        connection.execute("""CREATE TRIGGER fail_create AFTER INSERT ON repair_order
            BEGIN
              UPDATE repair_order SET description='不应保留' WHERE id <> NEW.id;
              SELECT RAISE(FAIL, 'secret SQL failure');
            END""")
    response = report_client.post("/m3/work-orders", json=payload())
    assert response.status_code == 500
    assert response.json()["error"] == "internal_error"
    assert "secret" not in response.text and str(report_database) not in response.text
    assert count(report_database) == 1
    assert get_repair_order(report_database, original) == before


@pytest.mark.parametrize("phase", ["begin", "commit"])
def test_m3_r01_real_lock_conflict_never_returns_success(report_client, report_database, phase):
    with connect_database(report_database) as blocker:
        blocker.execute("BEGIN IMMEDIATE" if phase == "begin" else "BEGIN")
        blocker.execute("SELECT * FROM repair_order").fetchall()
        response = report_client.post("/m3/work-orders", json=payload())
        assert response.status_code == 503
        assert response.json()["error"] == "database_busy"
    assert count(report_database) == 0


def test_m3_r01_missing_auth_fails_closed_without_affecting_app(report_database, monkeypatch):
    # 明确模拟外部认证模块缺失，不依赖 G2 是否合入。
    def missing_auth_module(name):
        assert name == "app.d.auth.dependencies"
        raise ModuleNotFoundError(
            "shared authentication module unavailable",
            name="app.d.auth.dependencies",
        )

    monkeypatch.setattr(m3_identity, "import_module", missing_auth_module)
    application = create_app(Settings(database_path=report_database))
    with TestClient(application) as client:
        assert client.get("/").status_code == 200
        assert client.get("/health").status_code == 200
        assert client.get("/version").status_code == 200
        assert client.get("/m2").status_code == 404
        for response in [client.get("/m3/rooms"), client.post("/m3/work-orders", json=payload(), headers={"X-User-Id": "1"})]:
            assert response.status_code == 503
            assert response.json()["error"] == "auth_unavailable"
    assert count(report_database) == 0


@pytest.mark.parametrize("database_fixture", ["v1_database", "missing"])
def test_m3_r01_missing_schema_or_database_is_explicit_and_not_auto_created(request, tmp_path, database_fixture):
    path = tmp_path / "absent.sqlite3" if database_fixture == "missing" else request.getfixturevalue(database_fixture)
    application = create_app(Settings(database_path=path))
    application.dependency_overrides[authenticated_reporter] = lambda: 1
    with TestClient(application) as client:
        response = client.post("/m3/work-orders", json=payload())
    assert response.status_code == 503
    assert response.json()["error"] in {"schema_unavailable", "storage_unavailable"}
    if database_fixture == "missing":
        assert not path.exists()
    else:
        with connect_database(path) as connection:
            assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
