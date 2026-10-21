"""M2-R01/R02/R03（部分）行为测试：权限门槛、申请校验、一级审批。

时间全部取“本地明天”的整点，避免测试随时钟漂移。
拒绝路径覆盖：无 room:apply、超容量、非整点、超 4 小时、时段冲突、无 room:approve、重复审批、驳回无理由、自己批自己。
"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.common.db import connect_database
from app.m2.times import LOCAL_ZONE

ACCOUNTS = {
    "student": ("student01", "Student#2026"),
    "teacher": ("teacher01", "Teacher#2026"),
    "leader": ("leader01", "Leader#2026"),
    "approver": ("approver01", "Approver#2026"),
    "admin": ("admin01", "Admin#2026"),
}


def _slot(hour: int, hours: int = 2) -> tuple[str, str]:
    day = (datetime.now(LOCAL_ZONE) + timedelta(days=1)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    return day.isoformat(), (day + timedelta(hours=hours)).isoformat()


def _body(room_id: int, *, hour: int = 9, hours: int = 2, attendees: int = 10) -> dict:
    start, end = _slot(hour, hours)
    return {
        "room_id": room_id,
        "start_at": start,
        "end_at": end,
        "purpose": "社团例会",
        "attendee_count": attendees,
    }


def _as(client: TestClient, login, role: str) -> TestClient:
    username, password = ACCOUNTS[role]
    return login(username, password)


def _rooms(client: TestClient) -> list[dict]:
    return client.get("/m2/rooms").json()["items"]


def test_m2_r01_student_without_apply_permission_is_rejected(seeded_client: TestClient, login):
    client = _as(seeded_client, login, "student")
    room = _rooms(client)[0]
    response = client.post("/m2/applications", json=_body(room["id"]))
    assert response.status_code == 403
    assert response.json()["error"] == "forbidden"
    # 拒绝后不留下任何记录。
    assert client.get("/m2/applications/pending").status_code == 403


def test_m2_r01_unauthenticated_request_is_rejected(seeded_client: TestClient):
    room = seeded_client.get("/health")
    assert room.status_code == 200
    response = seeded_client.post("/m2/applications", json=_body(1))
    assert response.status_code == 401
    assert response.json()["error"] == "unauthenticated"


def test_m2_r02_teacher_submits_application_pending_l1(seeded_client: TestClient, login):
    client = _as(seeded_client, login, "teacher")
    room = _rooms(client)[0]
    response = client.post("/m2/applications", json=_body(room["id"], hour=9, hours=2))
    assert response.status_code == 201
    item = response.json()
    assert item["status"] == "PENDING_L1"
    assert item["hours"] == 2
    assert item["applicant"]["username"] == "teacher01"
    assert item["room"]["id"] == room["id"]
    assert item["decided_by"] is None
    assert item["start_at"].endswith("Z")


def test_m2_r02_leader_can_also_apply(seeded_client: TestClient, login):
    client = _as(seeded_client, login, "leader")
    room = _rooms(client)[1]
    response = client.post("/m2/applications", json=_body(room["id"], hour=14))
    assert response.status_code == 201
    assert response.json()["applicant"]["username"] == "leader01"


def test_m2_r02_attendees_over_capacity_is_rejected(seeded_client: TestClient, login):
    client = _as(seeded_client, login, "teacher")
    room = _rooms(client)[0]
    response = client.post(
        "/m2/applications", json=_body(room["id"], attendees=room["capacity"] + 1)
    )
    assert response.status_code == 422
    assert "容量" in response.json()["message"]


def test_m2_r02_non_integral_hour_is_rejected(seeded_client: TestClient, login):
    client = _as(seeded_client, login, "teacher")
    room = _rooms(client)[0]
    start, end = _slot(9, 2)
    payload = _body(room["id"])
    payload["start_at"] = start.replace("09:00:00", "09:30:00")
    payload["end_at"] = end
    response = client.post("/m2/applications", json=payload)
    assert response.status_code == 422
    assert "整点" in response.json()["message"]


def test_m2_r02_more_than_four_hours_is_rejected(seeded_client: TestClient, login):
    client = _as(seeded_client, login, "teacher")
    room = _rooms(client)[0]
    too_long = client.post("/m2/applications", json=_body(room["id"], hour=9, hours=5))
    assert too_long.status_code == 422
    assert "4 小时" in too_long.json()["message"]

    longest_ok = client.post("/m2/applications", json=_body(room["id"], hour=9, hours=4))
    assert longest_ok.status_code == 201


def test_m2_r02_overlapping_slot_in_same_room_is_conflict(seeded_client: TestClient, login):
    client = _as(seeded_client, login, "teacher")
    other = _as(seeded_client, login, "leader")
    room = _rooms(client)[0]
    assert client.post("/m2/applications", json=_body(room["id"], hour=10, hours=2)).status_code == 201

    clash = other.post("/m2/applications", json=_body(room["id"], hour=11, hours=2))
    assert clash.status_code == 409
    assert clash.json()["error"] == "conflict"

    # 相邻但不重叠的时段可以申请。
    assert other.post("/m2/applications", json=_body(room["id"], hour=12, hours=2)).status_code == 201


def test_m2_r02_same_slot_in_other_room_is_allowed(seeded_client: TestClient, login):
    client = _as(seeded_client, login, "teacher")
    rooms = _rooms(client)
    assert client.post("/m2/applications", json=_body(rooms[0]["id"], hour=9)).status_code == 201
    assert client.post("/m2/applications", json=_body(rooms[1]["id"], hour=9)).status_code == 201


def test_m2_r03_only_approver_can_decide(seeded_client: TestClient, login):
    teacher = _as(seeded_client, login, "teacher")
    room = _rooms(teacher)[0]
    application_id = teacher.post("/m2/applications", json=_body(room["id"])).json()["id"]

    forbidden = teacher.post(f"/m2/applications/{application_id}/approve", json={})
    assert forbidden.status_code == 403
    assert forbidden.json()["error"] == "forbidden"


def test_m2_r03_approver_approves_once_then_conflict(seeded_client: TestClient, login):
    teacher = _as(seeded_client, login, "teacher")
    room = _rooms(teacher)[0]
    application_id = teacher.post("/m2/applications", json=_body(room["id"])).json()["id"]

    approver = _as(seeded_client, login, "approver")
    pending = approver.get("/m2/applications/pending").json()
    assert [item["id"] for item in pending["items"]] == [application_id]

    approved = approver.post(
        f"/m2/applications/{application_id}/approve", json={"note": "教室空闲"}
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["decided_by_name"] == "演示审批员"

    again = approver.post(f"/m2/applications/{application_id}/approve", json={})
    assert again.status_code == 409
    assert "重复审批" in again.json()["message"]
    assert approver.get("/m2/applications/pending").json()["items"] == []


def test_m2_r03_reject_requires_reason_and_records_it(seeded_client: TestClient, login):
    teacher = _as(seeded_client, login, "teacher")
    room = _rooms(teacher)[0]
    application_id = teacher.post("/m2/applications", json=_body(room["id"])).json()["id"]

    approver = _as(seeded_client, login, "approver")
    missing = approver.post(f"/m2/applications/{application_id}/reject", json={})
    assert missing.status_code == 422

    rejected = approver.post(
        f"/m2/applications/{application_id}/reject", json={"note": "该时段教室维护"}
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "REJECTED"
    assert rejected.json()["decision_note"] == "该时段教室维护"

    # 驳回后该时段释放，可以重新申请。
    _as(seeded_client, login, "teacher")
    again = teacher.post("/m2/applications", json=_body(room["id"]))
    assert again.status_code == 201


def test_m2_r03_approver_cannot_approve_own_application(seeded_client: TestClient, seeded_settings, login):
    # 演示账号默认不同时持有 room:apply 与 room:approve；这里在临时库里补授权，
    # 专门验证“自己不能批自己”这条护栏。
    with connect_database(seeded_settings.database_path) as connection:
        connection.execute(
            """
            INSERT INTO role_permission (role_id, permission_id)
            SELECT r.id, p.id FROM role AS r JOIN permission AS p
            WHERE r.code = 'admin' AND p.code = 'room:apply'
            """
        )

    admin = _as(seeded_client, login, "admin")
    room = _rooms(admin)[0]
    created = admin.post("/m2/applications", json=_body(room["id"], hour=15))
    assert created.status_code == 201

    response = admin.post(f"/m2/applications/{created.json()['id']}/approve", json={})
    assert response.status_code == 409
    assert "自己" in response.json()["message"]


def test_m2_r02_applicant_sees_only_own_applications(seeded_client: TestClient, login):
    client = _as(seeded_client, login, "teacher")
    rooms = _rooms(client)
    client.post("/m2/applications", json=_body(rooms[0]["id"], hour=9))

    _as(seeded_client, login, "leader")
    leader_item = client.post("/m2/applications", json=_body(rooms[0]["id"], hour=13)).json()

    _as(seeded_client, login, "teacher")
    mine = client.get("/m2/applications").json()
    assert mine["total"] == 1
    assert mine["items"][0]["applicant"]["username"] == "teacher01"

    # 别人的申请详情对普通申请人不可见。
    assert client.get(f"/m2/applications/{leader_item['id']}").status_code == 403
