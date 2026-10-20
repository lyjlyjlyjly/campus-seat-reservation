"""账号与授权查询：只读取，不写其他模块的表。"""

import sqlite3
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Credentials:
    """登录校验所需的最小字段，不含展示信息。"""

    id: int
    password_hash: str
    status: str


@dataclass(frozen=True)
class SessionUser:
    """一次请求内的身份快照：角色与权限在认证时展开，便于直接判断。"""

    id: int
    username: str
    display_name: str
    roles: tuple[str, ...]
    permissions: tuple[str, ...]

    def can(self, permission: str) -> bool:
        return permission in self.permissions


def find_credentials(connection: sqlite3.Connection, username: str) -> Optional[Credentials]:
    row = connection.execute(
        "SELECT id, password_hash, status FROM app_user WHERE username = ?", (username,)
    ).fetchone()
    if row is None:
        return None
    return Credentials(id=row["id"], password_hash=row["password_hash"], status=row["status"])


def load_identity(connection: sqlite3.Connection, user_id: int) -> Optional[SessionUser]:
    row = connection.execute(
        "SELECT id, username, display_name, status FROM app_user WHERE id = ?", (user_id,)
    ).fetchone()
    if row is None or row["status"] != "ACTIVE":
        return None
    roles = tuple(
        item["code"]
        for item in connection.execute(
            """
            SELECT r.code
            FROM user_role AS ur
            JOIN role AS r ON r.id = ur.role_id
            WHERE ur.user_id = ?
            ORDER BY r.code
            """,
            (user_id,),
        )
    )
    permissions = tuple(
        item["code"]
        for item in connection.execute(
            """
            SELECT DISTINCT p.code
            FROM user_role AS ur
            JOIN role_permission AS rp ON rp.role_id = ur.role_id
            JOIN permission AS p ON p.id = rp.permission_id
            WHERE ur.user_id = ?
            ORDER BY p.code
            """,
            (user_id,),
        )
    )
    return SessionUser(
        id=row["id"],
        username=row["username"],
        display_name=row["display_name"],
        roles=roles,
        permissions=permissions,
    )
