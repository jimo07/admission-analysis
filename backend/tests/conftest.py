"""pytest 配置：沙箱拒写 %TEMP%（WinError 5），把 tmp_path 重定向到工作区。

仅覆盖 tmp_path 工厂，返回工作区内 .pytest_tmp 目录，测试无需 danger-full-access。
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

_WORKSPACE_TMP = Path(__file__).resolve().parent / ".pytest_tmp"


@pytest.fixture()
def tmp_path(request: pytest.FixtureRequest) -> Path:
    """替代 pytest 内建 tmp_path，落在工作区而非系统 %TEMP%。"""
    name = request.node.name.replace("[", "_").replace("]", "_").replace("/", "_")
    target = _WORKSPACE_TMP / name
    if target.exists():
        shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    return target


@pytest.fixture()
def sqlite_session():
    """每个冒烟用例使用独立内存 SQLite；绝不连接本机 MySQL。"""
    from app.models import Base

    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()
