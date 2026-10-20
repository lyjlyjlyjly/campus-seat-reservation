"""服务端会话：数据库只保存令牌的 sha256，明文令牌只存在于 Cookie。"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from app.common.db import connect_database
from app.d.auth.users import SessionUser, load_identity


COOKIE_NAME = "campus_session"
SESSION_TTL_MINUTES = 30
UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def format_utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime(UTC_FORMAT)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(
    database_path: Path, user_id: int, *, ttl_minutes: int = SESSION_TTL_MINUTES
) -> tuple[str, str]:
    """返回 (明文令牌, 到期时间)；调用方只把明文写进响应 Cookie。"""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = format_utc(now + timedelta(minutes=ttl_minutes))
    with connect_database(database_path) as connection:
        connection.execute(
            """
            INSERT INTO session (token_hash, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (hash_token(token), user_id, format_utc(now), expires_at),
        )
    return token, expires_at


def find_session_user(database_path: Path, token: str) -> Optional[SessionUser]:
    """过期、已撤销或账号停用的会话一律视为无效。

    过期比较放在 SQL 里，避免进程时区影响判定结果。
    """
    if not token:
        return None
    with connect_database(database_path) as connection:
        row = connection.execute(
            """
            SELECT s.user_id
            FROM session AS s
            JOIN app_user AS u ON u.id = s.user_id
            WHERE s.token_hash = ?
              AND s.revoked_at IS NULL
              AND s.expires_at > strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
              AND u.status = 'ACTIVE'
            """,
            (hash_token(token),),
        ).fetchone()
        if row is None:
            return None
        return load_identity(connection, row["user_id"])


def revoke_session(database_path: Path, token: str) -> bool:
    """已撤销或不存在时返回 False，调用方据此决定是否提示。"""
    if not token:
        return False
    with connect_database(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE session
            SET revoked_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
            WHERE token_hash = ? AND revoked_at IS NULL
            """,
            (hash_token(token),),
        )
        return cursor.rowcount > 0
