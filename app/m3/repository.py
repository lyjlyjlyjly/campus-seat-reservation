"""M3 工单存储边界；调用方负责真实身份和业务授权，不在此初始化数据库。"""

from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from app.common.db import connect_database


def _positive_id(value: int, field: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field} 必须为正整数")


def create_repair_order(
    database_path: Path,
    *,
    reporter_id: int,
    room_id: int,
    fault_type: str,
    description: str,
) -> int:
    """写入 REPORTED 并返回 ID；约束失败抛出 sqlite3.IntegrityError。

    参数必须由上层提供，reporter_id 不等于已通过认证。这里只做存储输入
    类型检查和 strip；分类、长度及外键由真实表约束兜底，不强制转换文本。
    使用独立连接和单个事务，异常回滚并关闭连接，不写其他模块表。
    """
    with connect_database(database_path) as connection:
        return insert_repair_order(
            connection, reporter_id=reporter_id, room_id=room_id,
            fault_type=fault_type, description=description,
        )


def insert_repair_order(
    connection: sqlite3.Connection,
    *,
    reporter_id: int,
    room_id: int,
    fault_type: str,
    description: str,
) -> int:
    """在调用方连接中写入；不提交/关闭，事务与权限由调用方管理。"""
    _positive_id(reporter_id, "reporter_id")
    _positive_id(room_id, "room_id")
    if not isinstance(fault_type, str):
        raise ValueError("fault_type 必须为字符串")
    if not isinstance(description, str):
        raise ValueError("description 必须为字符串")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cursor = connection.execute(
        """INSERT INTO repair_order (
            reporter_id, room_id, fault_type, description, status,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'REPORTED', ?, ?)""",
        (reporter_id, room_id, fault_type.strip(), description.strip(), timestamp, timestamp),
    )
    return cursor.lastrowid


def get_repair_order(database_path: Path, order_id: int) -> dict[str, object] | None:
    """通过新的只读连接读取，未知 ID 返回 None；本函数不执行对象级授权。"""
    _positive_id(order_id, "order_id")
    with connect_database(database_path, read_only=True) as connection:
        row = connection.execute(
            """SELECT id, reporter_id, room_id, fault_type, description, status,
                      assigned_to, assigned_by, assigned_at, started_at,
                      created_at, updated_at
               FROM repair_order WHERE id = ?""",
            (order_id,),
        ).fetchone()
        return dict(row) if row is not None else None


def list_owned_orders(connection: sqlite3.Connection, user_id: int) -> list[dict]:
    """服务层先授权；SQL 仅查本人，响应不带正文或共享用户资料。"""
    rows = connection.execute(
        """SELECT o.id, o.room_id, r.name AS room_name, o.fault_type, o.status,
                  o.created_at
           FROM repair_order AS o JOIN room AS r ON r.id = o.room_id
           WHERE o.reporter_id = ? ORDER BY o.created_at DESC, o.id DESC""",
        (user_id,),
    )
    return [dict(row) for row in rows]


def find_visible_order(
    connection: sqlite3.Connection, order_id: int, *, user_id: int,
    allow_management: bool, allow_own: bool, allow_assigned: bool,
) -> dict | None:
    """按已核实权限限定 SQL 对象范围；不存在/不可见均返回 None。"""
    row = connection.execute(
        """SELECT o.id, o.reporter_id, o.room_id, r.name AS room_name,
                  o.fault_type, o.description, o.status, o.assigned_to, o.assigned_by,
                  o.assigned_at, o.started_at, o.created_at, o.updated_at
           FROM repair_order AS o JOIN room AS r ON r.id = o.room_id
           WHERE o.id = ? AND (
               ? OR (? AND o.reporter_id = ?) OR (? AND o.assigned_to = ?)
           )""",
        (order_id, allow_management, allow_own, user_id, allow_assigned, user_id),
    ).fetchone()
    return dict(row) if row is not None else None


def list_dispatch_orders(connection: sqlite3.Connection, status: str) -> list[dict]:
    rows = connection.execute(
        """SELECT o.id, o.room_id, r.name AS room_name, o.fault_type, o.status,
                  o.created_at, o.assigned_to, o.assigned_at
           FROM repair_order AS o JOIN room AS r ON r.id = o.room_id
           WHERE o.status = ? ORDER BY o.created_at DESC, o.id DESC""", (status,),
    )
    return [dict(row) | {"detail_url": f"/m3/orders/{row['id']}"} for row in rows]


def list_assigned_orders(connection: sqlite3.Connection, user_id: int, status: str | None) -> list[dict]:
    """固定 SQL 本人范围；状态过滤不改变受理人条件。"""
    sql = """SELECT o.id, o.room_id, r.name AS room_name, o.fault_type, o.status,
                    o.created_at, o.assigned_at, o.started_at, o.updated_at
             FROM repair_order AS o JOIN room AS r ON r.id = o.room_id
             WHERE o.assigned_to = ?"""
    parameters = (user_id,)
    if status is not None:
        sql += " AND o.status = ?"
        parameters += (status,)
    return [dict(row) for row in connection.execute(sql + " ORDER BY o.created_at DESC, o.id DESC", parameters)]


def find_start_target(connection: sqlite3.Connection, order_id: int) -> dict | None:
    """只供已通过 start 功能授权的服务做对象/状态判断，不授予正文读取权。"""
    row = connection.execute(
        "SELECT id, status, assigned_to FROM repair_order WHERE id = ?", (order_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def start_assigned_order(connection: sqlite3.Connection, order_id: int, user_id: int) -> int:
    """由调用者管理事务；本人、ASSIGNED 条件防止重复覆盖首次开始时间。"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return connection.execute(
        """UPDATE repair_order SET status='IN_REPAIR', started_at=?, updated_at=?
           WHERE id=? AND status='ASSIGNED' AND assigned_to=?""",
        (timestamp, timestamp, order_id, user_id),
    ).rowcount


def eligible_repairers(connection: sqlite3.Connection, user_id: int | None = None) -> list[dict]:
    """候选/写事务共用资格条件；角色与权限分别检查，允许合法多角色组合。"""
    if user_id is not None and user_id > 9223372036854775807:
        return []
    sql = """SELECT u.id, u.display_name FROM app_user AS u
             WHERE u.status = 'ACTIVE'
             AND EXISTS (SELECT 1 FROM user_role AS ur JOIN role AS r ON r.id = ur.role_id
                         WHERE ur.user_id = u.id AND r.code = 'repairer')
             AND EXISTS (SELECT 1 FROM user_role AS ur
                         JOIN role_permission AS rp ON rp.role_id = ur.role_id
                         JOIN permission AS p ON p.id = rp.permission_id
                         WHERE ur.user_id = u.id AND p.code = 'repair:start')"""
    parameters = ()
    if user_id is not None:
        sql += " AND u.id = ?"
        parameters = (user_id,)
    return [dict(row) for row in connection.execute(sql + " ORDER BY u.display_name, u.id", parameters)]


def assign_reported_order(connection: sqlite3.Connection, order_id: int, assigned_to: int, assigned_by: int) -> int:
    """调用者负责事务/授权；条件更新防止覆盖，时间由服务端统一生成。"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return connection.execute(
        """UPDATE repair_order SET status='ASSIGNED', assigned_to=?, assigned_by=?,
                  assigned_at=?, updated_at=?, started_at=NULL
           WHERE id=? AND status='REPORTED'""",
        (assigned_to, assigned_by, timestamp, timestamp, order_id),
    ).rowcount
