from datetime import datetime
from app.db.connection import get_pool


async def save_scheduled_order(
    flat_id: str,
    scheduled_by: str,
    run_at: str,
    is_recurring: bool,
    cron_expr: str | None,
    job_id: str,
) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row_id = await conn.fetchval(
            "INSERT INTO scheduled_orders "
            "(flat_id, scheduled_by, run_at, is_recurring, cron_expr, job_id, status, created_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, 'pending', $7) RETURNING id",
            flat_id, scheduled_by, run_at, int(is_recurring), cron_expr, job_id,
            int(datetime.utcnow().timestamp()),
        )
        return row_id


async def get_pending_schedules(flat_id: str) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM scheduled_orders WHERE flat_id = $1 AND status = 'pending' ORDER BY created_at",
            flat_id,
        )
        return [dict(r) for r in rows]


async def cancel_scheduled_order(job_id: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE scheduled_orders SET status = 'cancelled' WHERE job_id = $1", job_id
        )
        return result == "UPDATE 1"


async def mark_order_placed(job_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE scheduled_orders SET status = 'placed' WHERE job_id = $1", job_id
        )
