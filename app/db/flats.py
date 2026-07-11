from datetime import datetime
from app.db.connection import get_pool


async def create_flat_if_not_exists(flat_id: str, owner_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO flats (flat_id, owner_id, created_at) VALUES ($1, $2, $3) ON CONFLICT (flat_id) DO NOTHING",
            flat_id, owner_id, int(datetime.utcnow().timestamp()),
        )


async def get_flat(flat_id: str) -> dict | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM flats WHERE flat_id = $1", flat_id)
        return dict(row) if row else None


async def save_swiggy_token(flat_id: str, token: str, expires_at: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE flats SET swiggy_access_token = $1, swiggy_token_expires_at = $2 WHERE flat_id = $3",
            token, expires_at, flat_id,
        )


async def save_default_address(flat_id: str, address_id: str, label: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE flats SET default_address_id = $1, default_address_label = $2 WHERE flat_id = $3",
            address_id, label, flat_id,
        )
