import os
import asyncpg
from typing import Optional, Any

_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = os.environ["DATABASE_URL"]
        # Pool kecil untuk serverless: min_size=1, max_size=3
        # statement_cache_size=0 wajib untuk PgBouncer transaction mode
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=1,
            max_size=3,
            command_timeout=30,
            statement_cache_size=0,
        )
    return _pool

async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

async def fetch(query: str, *args, timeout: float = 20.0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args, timeout=timeout)

async def fetchrow(query: str, *args, timeout: float = 20.0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args, timeout=timeout)

async def fetchval(query: str, *args, timeout: float = 20.0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(query, *args, timeout=timeout)

async def execute(query: str, *args, timeout: float = 20.0):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args, timeout=timeout)