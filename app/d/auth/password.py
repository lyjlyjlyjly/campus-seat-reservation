"""口令派生与校验；只用标准库，散列格式由本模块单独解释。

数据库只保存派生结果，不保存明文口令。补丁说明见 docs/specs/001-auth-session-rbac.md。
"""

import hashlib
import hmac
import secrets
import sys
from typing import Optional


ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 200_000
SALT_BYTES = 16


def hash_password(password: str, *, iterations: int = ITERATIONS) -> str:
    """返回 pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>。"""
    if not isinstance(password, str) or not password:
        raise ValueError("口令不能为空")
    if iterations < 1:
        raise ValueError("迭代次数必须为正整数")
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """对畸形记录一律返回 False，不抛出异常，避免登录路径泄漏内部状态。"""
    if not isinstance(password, str) or not isinstance(stored, str):
        return False
    try:
        algorithm, iterations_text, salt_text, digest_text = stored.split("$")
        iterations = int(iterations_text)
        salt = bytes.fromhex(salt_text)
        expected = bytes.fromhex(digest_text)
    except ValueError:
        return False
    if algorithm != ALGORITHM or iterations < 1 or not salt or not expected:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def _read_password(prompt: str) -> str:
    # 命令行参数会留在 shell 历史里，因此只从终端或标准输入读取。
    import getpass

    if sys.stdin is not None and sys.stdin.isatty():
        return getpass.getpass(prompt)
    return sys.stdin.readline().rstrip("\n")


def main(argv: Optional[list[str]] = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "--check":
        if len(arguments) != 2:
            print("用法：python -m app.d.auth.password --check <存储的散列>", file=sys.stderr)
            return 2
        password = _read_password("口令：")
        matched = verify_password(password, arguments[1])
        print("匹配" if matched else "不匹配")
        return 0 if matched else 1
    if arguments:
        print("用法：python -m app.d.auth.password [--check <存储的散列>]", file=sys.stderr)
        return 2
    password = _read_password("口令：")
    try:
        print(hash_password(password))
    except ValueError as error:
        print(f"失败：{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
