"""V1 迁移与演示种子的行为验收：外键、约束、幂等和固定授权结果。"""

import sqlite3
from pathlib import Path

import pytest

from app.bootstrap import SEED_PATH, initialize_database
from app.common.db import connect_database


def _query(connection: sqlite3.Connection, sql: str, parameters: tuple = ()) -> list:
    return connection.execute(sql, parameters).fetchall()


def test_d_r03_seed_runs_twice_without_duplicates(tmp_path: Path):
    database = tmp_path / "campus.sqlite3"

    assert initialize_database(database, seed_path=SEED_PATH) == 1
    assert initialize_database(database, seed_path=SEED_PATH) == 1

    with connect_database(database) as connection:
        assert _query(connection, "SELECT COUNT(*) FROM app_user")[0][0] == 6
        assert _query(connection, "SELECT COUNT(*) FROM room")[0][0] == 3
        assert _query(connection, "SELECT COUNT(*) FROM role")[0][0] == 6
        assert _query(connection, "SELECT COUNT(*) FROM permission")[0][0] == 2
        assert _query(connection, "SELECT COUNT(*) FROM user_role")[0][0] == 6
        assert _query(connection, "SELECT COUNT(*) FROM role_permission")[0][0] == 4


def test_d_r02_fixed_roles_map_to_declared_permissions(seeded_settings):
    with connect_database(seeded_settings.database_path) as connection:
        rows = _query(
            connection,
            """
            SELECT r.code, p.code
            FROM role AS r
            JOIN role_permission AS rp ON rp.role_id = r.id
            JOIN permission AS p ON p.id = rp.permission_id
            ORDER BY r.code, p.code
            """,
        )

    assert [tuple(row) for row in rows] == [
        ("admin", "room:approve"),
        ("approver", "room:approve"),
        ("org_leader", "room:apply"),
        ("teacher", "room:apply"),
    ]


def test_d_r02_student_has_no_apply_permission(seeded_settings):
    with connect_database(seeded_settings.database_path) as connection:
        rows = _query(
            connection,
            """
            SELECT p.code
            FROM app_user AS u
            JOIN user_role AS ur ON ur.user_id = u.id
            JOIN role_permission AS rp ON rp.role_id = ur.role_id
            JOIN permission AS p ON p.id = rp.permission_id
            WHERE u.username = 'student01'
            """,
        )

    assert rows == []


def test_d_r01_session_table_stores_only_token_hash(seeded_settings):
    with connect_database(seeded_settings.database_path) as connection:
        columns = {row["name"] for row in _query(connection, "PRAGMA table_info(session)")}

    assert "token_hash" in columns
    assert "token" not in columns


def test_m2_r02_application_status_check_rejects_unknown_value(seeded_settings):
    with connect_database(seeded_settings.database_path) as connection:
        user_id = _query(connection, "SELECT id FROM app_user WHERE username = 'teacher01'")[0][0]
        room_id = _query(connection, "SELECT id FROM room WHERE name = 'A101'")[0][0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO room_application
                  (applicant_id, room_id, start_at, end_at, purpose, attendee_count, status)
                VALUES (?, ?, '2026-11-02T01:00:00Z', '2026-11-02T03:00:00Z', '班会', 10, 'DONE')
                """,
                (user_id, room_id),
            )


def test_m2_r02_application_check_rejects_inverted_period(seeded_settings):
    with connect_database(seeded_settings.database_path) as connection:
        user_id = _query(connection, "SELECT id FROM app_user WHERE username = 'teacher01'")[0][0]
        room_id = _query(connection, "SELECT id FROM room WHERE name = 'A101'")[0][0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                """
                INSERT INTO room_application
                  (applicant_id, room_id, start_at, end_at, purpose, attendee_count)
                VALUES (?, ?, '2026-11-02T03:00:00Z', '2026-11-02T01:00:00Z', '班会', 10)
                """,
                (user_id, room_id),
            )


def test_d_r02_foreign_keys_are_enforced(seeded_settings):
    with connect_database(seeded_settings.database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO user_role (user_id, role_id) VALUES (9999, 1)")
