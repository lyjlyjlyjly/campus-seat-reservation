"""M2 数据访问：教室申请与一级审批。

写入集中在显式 `BEGIN IMMEDIATE` 事务里：同一教室的「查冲突 → 落库」必须是原子的，
否则并发的两个申请会同时通过校验。审批同理，状态只在 PENDING_L1 时允许改变。
"""

import sqlite3
from typing import Optional

from app.common.db import connect_database

STATUS_PENDING = "PENDING_L1"
STATUS_APPROVED = "APPROVED"
STATUS_REJECTED = "REJECTED"
# 占用教室时段的状态；REJECTED/CANCELLED/REVOKED 不占用。
OCCUPYING_STATUSES = ("PENDING_L1", "PENDING_L2", "APPROVED")
STATUSES = OCCUPYING_STATUSES + ("REJECTED", "REVOKED", "CANCELLED")

_APPLICATION_SQL = """
    SELECT a.id, a.start_at, a.end_at, a.purpose, a.attendee_count, a.status,
           a.decision_note, a.created_at, a.updated_at,
           a.applicant_id, u.username AS applicant_username, u.display_name AS applicant_name,
           a.room_id, r.name AS room_name, r.capacity AS room_capacity,
           a.decided_by, d.display_name AS decided_by_name
    FROM room_application AS a
    JOIN app_user AS u ON u.id = a.applicant_id
    JOIN room AS r ON r.id = a.room_id
    LEFT JOIN app_user AS d ON d.id = a.decided_by
"""


class ApplicationRejected(Exception):
    """业务拒绝：由路由层转成统一错误体，避免把 HTTP 细节写进数据层。"""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _serialize(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "status": row["status"],
        "start_at": row["start_at"],
        "end_at": row["end_at"],
        "purpose": row["purpose"],
        "attendee_count": row["attendee_count"],
        "room": {
            "id": row["room_id"],
            "name": row["room_name"],
            "capacity": row["room_capacity"],
        },
        "applicant": {
            "id": row["applicant_id"],
            "username": row["applicant_username"],
            "display_name": row["applicant_name"],
        },
        "decided_by": row["decided_by"],
        "decided_by_name": row["decided_by_name"],
        "decision_note": row["decision_note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def list_rooms(database_path) -> list[dict]:
    with connect_database(database_path, read_only=True) as connection:
        rows = connection.execute(
            "SELECT id, name, capacity, is_active FROM room WHERE is_active = 1 ORDER BY name"
        ).fetchall()
    return [dict(row) for row in rows]


def get_application(database_path, application_id: int) -> Optional[dict]:
    with connect_database(database_path, read_only=True) as connection:
        row = connection.execute(
            _APPLICATION_SQL + " WHERE a.id = ?", (application_id,)
        ).fetchone()
    return _serialize(row) if row else None


def list_applications(
    database_path, *, applicant_id: Optional[int] = None, statuses: tuple[str, ...] = ()
) -> list[dict]:
    clauses: list[str] = []
    parameters: list[object] = []
    if applicant_id is not None:
        clauses.append("a.applicant_id = ?")
        parameters.append(applicant_id)
    if statuses:
        placeholders = ", ".join("?" for _ in statuses)
        clauses.append(f"a.status IN ({placeholders})")
        parameters.extend(statuses)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with connect_database(database_path, read_only=True) as connection:
        rows = connection.execute(
            _APPLICATION_SQL + where + " ORDER BY a.start_at, a.id", parameters
        ).fetchall()
    return [_serialize(row) for row in rows]


def create_application(
    database_path,
    *,
    applicant_id: int,
    room_id: int,
    start_at: str,
    end_at: str,
    purpose: str,
    attendee_count: int,
) -> dict:
    with connect_database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        room = connection.execute(
            "SELECT id, name, capacity, is_active FROM room WHERE id = ?", (room_id,)
        ).fetchone()
        if room is None:
            raise ApplicationRejected(404, "not_found", "教室不存在")
        if not room["is_active"]:
            raise ApplicationRejected(409, "conflict", "该教室当前不可借用")
        if attendee_count > room["capacity"]:
            raise ApplicationRejected(
                422, "invalid_request", f"人数超过教室容量（{room['capacity']} 人）"
            )

        placeholders = ", ".join("?" for _ in OCCUPYING_STATUSES)
        clash = connection.execute(
            f"""
            SELECT id FROM room_application
            WHERE room_id = ? AND status IN ({placeholders})
              AND start_at < ? AND end_at > ?
            LIMIT 1
            """,
            (room_id, *OCCUPYING_STATUSES, end_at, start_at),
        ).fetchone()
        if clash is not None:
            raise ApplicationRejected(409, "conflict", "该教室在此时段已被占用")

        cursor = connection.execute(
            """
            INSERT INTO room_application
                (applicant_id, room_id, start_at, end_at, purpose, attendee_count, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (applicant_id, room_id, start_at, end_at, purpose, attendee_count, STATUS_PENDING),
        )
        row = connection.execute(
            _APPLICATION_SQL + " WHERE a.id = ?", (cursor.lastrowid,)
        ).fetchone()
    return _serialize(row)


def decide_application(
    database_path, *, application_id: int, approver_id: int, approved: bool, note: Optional[str]
) -> dict:
    new_status = STATUS_APPROVED if approved else STATUS_REJECTED
    with connect_database(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT id, applicant_id, status FROM room_application WHERE id = ?",
            (application_id,),
        ).fetchone()
        if row is None:
            raise ApplicationRejected(404, "not_found", "申请不存在")
        if row["status"] != STATUS_PENDING:
            raise ApplicationRejected(409, "conflict", "该申请已被处理，不能重复审批")
        if row["applicant_id"] == approver_id:
            raise ApplicationRejected(409, "conflict", "不能审批自己提交的申请")

        cursor = connection.execute(
            """
            UPDATE room_application
            SET status = ?, decided_by = ?, decision_note = ?,
                updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            WHERE id = ? AND status = ?
            """,
            (new_status, approver_id, note, application_id, STATUS_PENDING),
        )
        if cursor.rowcount != 1:  # 并发下被别人抢先处理
            raise ApplicationRejected(409, "conflict", "该申请已被处理，请刷新后重试")
        updated = connection.execute(
            _APPLICATION_SQL + " WHERE a.id = ?", (application_id,)
        ).fetchone()
    return _serialize(updated)
