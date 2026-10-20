"""从进程环境读取配置，不在导入时创建目录或数据库。"""

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    database_path: Path
    version: str = "dev"


def get_settings() -> Settings:
    raw_path = os.environ.get("CAMPUS_DATABASE_PATH")
    database_path = Path(raw_path).expanduser() if raw_path else Path("var/campus.sqlite3")
    if not database_path.is_absolute():
        database_path = PROJECT_ROOT / database_path
    return Settings(
        database_path=database_path.resolve(),
        version=os.environ.get("CAMPUS_VERSION", "dev").strip() or "dev",
    )
