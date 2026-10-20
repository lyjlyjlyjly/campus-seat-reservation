"""单个 FastAPI 入口，装配三组路由；启动不隐式初始化数据库。"""

import sqlite3
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.common.config import PROJECT_ROOT, Settings, get_settings
from app.common.db import connect_database
from app.m1.router import router as m1_router
from app.m2.router import router as m2_router
from app.m3.router import router as m3_router


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(title="校园资源服务平台", version=settings.version)
    application.state.settings = settings
    application.include_router(m1_router, prefix="/m1", tags=["M1 自习座位预约"])
    application.include_router(m2_router, prefix="/m2", tags=["M2 教室借用审批"])
    application.include_router(m3_router, prefix="/m3", tags=["M3 设施报修"])
    application.mount(
        "/assets", StaticFiles(directory=PROJECT_ROOT / "web" / "assets"), name="assets"
    )

    @application.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(PROJECT_ROOT / "web" / "templates" / "index.html")

    @application.get("/health", tags=["基础设施"])
    def health() -> JSONResponse:
        try:
            if not settings.database_path.is_file() or settings.database_path.stat().st_size == 0:
                raise OSError("数据库尚未初始化")
            with connect_database(settings.database_path, read_only=True) as connection:
                connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
                version = connection.execute("PRAGMA user_version").fetchone()[0]
        except (OSError, sqlite3.Error):
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable", "database": "unavailable"},
            )
        return JSONResponse(
            content={"status": "ok", "database": "ok", "schema_version": version}
        )

    @application.get("/version", tags=["基础设施"])
    def version() -> dict[str, str]:
        return {"version": settings.version}

    return application


app = create_app()
