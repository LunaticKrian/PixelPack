"""轻量幂等迁移：create_all 不会 ALTER 已存在的表，故需要手动补列。

仅依赖 SQLite 的 PRAGMA table_info / ALTER TABLE ADD COLUMN，可重入。
"""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def ensure_column(conn: AsyncConnection, table: str, column: str, ddl: str) -> bool:
    """若 `table` 不存在 `column`，则 ADD COLUMN。返回是否实际新增。"""
    res = await conn.execute(text(f"PRAGMA table_info({table})"))
    existing = {row[1] for row in res.fetchall()}
    if column in existing:
        return False
    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
    return True
