from datetime import datetime, timezone
import sqlite3

import pytest

from app.common.db import connect_database
from app.m3.repository import create_repair_order, get_repair_order


def create(database, **overrides):
    values = {"reporter_id": 1, "room_id": 10,
              "fault_type": "ELECTRICAL", "description": "灯管闪烁"}
    values.update(overrides)
    return create_repair_order(database, **values)


def count_orders(database):
    with connect_database(database, read_only=True) as connection:
        return connection.execute("SELECT COUNT(*) FROM repair_order").fetchone()[0]


def test_m3_r01_create_commits_normalized_text_and_server_time_across_connections(database):
    before = datetime.now(timezone.utc).replace(microsecond=0)
    text = "第一排  左侧\n灯管闪烁'; DROP TABLE room; --"
    order_id = create(database, fault_type=" \tELECTRICAL\n", description="\u3000" + text + "\r\n")
    after = datetime.now(timezone.utc).replace(microsecond=0)
    order = get_repair_order(database, order_id)
    timestamp = datetime.strptime(order["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert before <= timestamp <= after
    assert order == {
        "id": order_id, "reporter_id": 1, "room_id": 10,
        "fault_type": "ELECTRICAL", "description": text, "status": "REPORTED",
        "assigned_to": None, "assigned_by": None, "assigned_at": None, "started_at": None,
        "created_at": order["created_at"], "updated_at": order["created_at"],
    }
    # create 已退出连接；再次独立连接验证提交、参数绑定和共享数据未被改写。
    with connect_database(database, read_only=True) as connection:
        assert connection.execute("SELECT description FROM repair_order WHERE id = ?", (order_id,)).fetchone()[0] == text
        assert connection.execute("SELECT COUNT(*) FROM room").fetchone()[0] == 2


@pytest.mark.parametrize("category", ["ELECTRICAL", "WATER", "FURNITURE", "OTHER"])
def test_m3_r01_all_four_categories_persist(database, category):
    order_id = create(database, fault_type=category)
    assert get_repair_order(database, order_id)["fault_type"] == category


@pytest.mark.parametrize("text", ["中", "中" * 1000, "\U0001f4a1" * 1000], ids=["one", "1000-chinese", "1000-non-bmp"])
def test_m3_r01_length_is_unicode_codepoints_after_strip(database, text):
    order_id = create(database, description="\x1c\u00a0" + text + "\u3000\n")
    assert get_repair_order(database, order_id)["description"] == text


@pytest.mark.parametrize(
    "field,value",
    [("description", " \t\n\u3000"), ("description", "中" * 1001),
     ("description", "a\x00b"), ("fault_type", "UNKNOWN")],
    ids=["blank", "too-long", "nul", "unknown-category"],
)
def test_m3_r01_rejected_create_preserves_existing_data(database, field, value):
    order_id = create(database)
    before = get_repair_order(database, order_id)
    with pytest.raises(sqlite3.IntegrityError):
        create(database, **{field: value})
    assert get_repair_order(database, order_id) == before
    assert count_orders(database) == 1


@pytest.mark.parametrize(
    "field,value",
    [("fault_type", None), ("description", 42), ("description", True),
     ("description", ["text"]), ("reporter_id", True), ("room_id", 0), ("reporter_id", "1")],
)
def test_m3_r01_repository_rejects_coercion_before_writing(database, field, value):
    with pytest.raises(ValueError, match=field):
        create(database, **{field: value})
    assert count_orders(database) == 0


@pytest.mark.parametrize("field", ["reporter_id", "room_id"])
def test_m3_r01_repository_connections_enforce_foreign_keys(database, field):
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        create(database, **{field: 9999})
    assert count_orders(database) == 0


def test_m3_r01_inactive_but_existing_room_can_be_reported(database):
    order_id = create(database, room_id=20)
    assert get_repair_order(database, order_id)["room_id"] == 20
    with connect_database(database, read_only=True) as connection:
        assert connection.execute("SELECT is_active FROM room WHERE id = 20").fetchone()[0] == 0


def test_m3_r01_read_unknown_id_returns_none_and_rejects_invalid_id(database):
    assert get_repair_order(database, 9999) is None
    with pytest.raises(ValueError, match="order_id"):
        get_repair_order(database, "1 OR 1=1")
    assert count_orders(database) == 0


def test_m3_r01_repository_rolls_back_after_a_real_sqlite_failure(database):
    original_id = create(database)
    before = get_repair_order(database, original_id)
    with connect_database(database) as connection:
        # 临时库故障注入：RAISE(FAIL) 本身不会撤销本语句先前的写入，
        # 必须由 repository 的连接事务回滚；这里没有 mock 被测逻辑。
        connection.execute(
            """CREATE TRIGGER m3_test_fail AFTER INSERT ON repair_order
               WHEN NEW.description = '触发真实失败'
               BEGIN
                   UPDATE repair_order SET description = '不应保留的更新'
                   WHERE id <> NEW.id;
                   SELECT RAISE(FAIL, 'test storage failure');
               END"""
        )
    with pytest.raises(sqlite3.IntegrityError, match="test storage failure"):
        create(database, description="触发真实失败")
    assert count_orders(database) == 1
    assert get_repair_order(database, original_id) == before


def test_m3_r01_repository_does_not_create_missing_database(tmp_path):
    path = tmp_path / "not-initialized.sqlite3"
    with pytest.raises(sqlite3.OperationalError):
        create(path)
    with pytest.raises(sqlite3.OperationalError):
        get_repair_order(path, 1)
    assert not path.exists()


def test_m3_r01_repository_does_not_install_schema_in_v1_database(v1_database):
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        create(v1_database)
    with pytest.raises(sqlite3.OperationalError, match="no such table"):
        get_repair_order(v1_database, 1)
    with connect_database(v1_database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("SELECT name FROM sqlite_master WHERE name = 'repair_order'").fetchone() is None
