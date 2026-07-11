import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        raise RuntimeError("DB pool not initialized — call init_db() first")
    return _pool


async def init_db() -> None:
    global _pool
    _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)

    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS flats (
                flat_id                 TEXT PRIMARY KEY,
                owner_id                TEXT NOT NULL,
                swiggy_access_token     TEXT,
                swiggy_token_expires_at BIGINT,
                default_address_id      TEXT,
                default_address_label   TEXT,
                created_at              BIGINT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cart_items (
                id           SERIAL PRIMARY KEY,
                flat_id      TEXT NOT NULL REFERENCES flats(flat_id),
                spin_id      TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity     INTEGER NOT NULL DEFAULT 1,
                added_by     TEXT NOT NULL,
                added_at     BIGINT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS item_preferences (
                flat_id         TEXT NOT NULL REFERENCES flats(flat_id),
                spin_id         TEXT NOT NULL,
                product_name    TEXT NOT NULL,
                order_count     INTEGER NOT NULL DEFAULT 1,
                last_ordered_at BIGINT NOT NULL,
                PRIMARY KEY (flat_id, spin_id)
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id         SERIAL PRIMARY KEY,
                flat_id    TEXT NOT NULL REFERENCES flats(flat_id),
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at BIGINT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scheduled_orders (
                id           SERIAL PRIMARY KEY,
                flat_id      TEXT NOT NULL REFERENCES flats(flat_id),
                scheduled_by TEXT NOT NULL,
                run_at       TEXT NOT NULL,
                is_recurring INTEGER NOT NULL DEFAULT 0,
                cron_expr    TEXT,
                job_id       TEXT UNIQUE,
                status       TEXT NOT NULL DEFAULT 'pending',
                created_at   BIGINT NOT NULL
            );
        """)


async def close_db() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
