from datetime import datetime
from app.db.connection import get_pool


# ---------------------------------------------------------------------------
# Cart tracking (added_by metadata — Swiggy is source of truth for quantities)
# ---------------------------------------------------------------------------

async def add_to_cart(flat_id: str, spin_id: str, product_name: str, quantity: int, added_by: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id, quantity FROM cart_items WHERE flat_id = $1 AND spin_id = $2",
            flat_id, spin_id,
        )
        if existing:
            await conn.execute(
                "UPDATE cart_items SET quantity = $1 WHERE id = $2",
                existing["quantity"] + quantity, existing["id"],
            )
        else:
            await conn.execute(
                "INSERT INTO cart_items (flat_id, spin_id, product_name, quantity, added_by, added_at) "
                "VALUES ($1, $2, $3, $4, $5, $6)",
                flat_id, spin_id, product_name, quantity, added_by, int(datetime.utcnow().timestamp()),
            )


async def get_cart(flat_id: str) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM cart_items WHERE flat_id = $1 ORDER BY added_at", flat_id
        )
        return [dict(r) for r in rows]


async def remove_from_cart(flat_id: str, spin_id: str) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM cart_items WHERE flat_id = $1 AND spin_id = $2", flat_id, spin_id
        )
        return result == "DELETE 1"


async def clear_cart(flat_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM cart_items WHERE flat_id = $1", flat_id)


# ---------------------------------------------------------------------------
# Item preferences (variant auto-selection)
# ---------------------------------------------------------------------------

async def record_item_preference(flat_id: str, spin_id: str, product_name: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT order_count FROM item_preferences WHERE flat_id = $1 AND spin_id = $2",
            flat_id, spin_id,
        )
        now = int(datetime.utcnow().timestamp())
        if existing:
            await conn.execute(
                "UPDATE item_preferences SET order_count = $1, last_ordered_at = $2, product_name = $3 "
                "WHERE flat_id = $4 AND spin_id = $5",
                existing["order_count"] + 1, now, product_name, flat_id, spin_id,
            )
        else:
            await conn.execute(
                "INSERT INTO item_preferences (flat_id, spin_id, product_name, order_count, last_ordered_at) "
                "VALUES ($1, $2, $3, 1, $4)",
                flat_id, spin_id, product_name, now,
            )


async def get_all_item_preferences(flat_id: str) -> list[dict]:
    """Return all previously ordered items sorted by order_count desc."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT spin_id, product_name, order_count FROM item_preferences "
            "WHERE flat_id = $1 ORDER BY order_count DESC LIMIT 30",
            flat_id,
        )
        return [dict(r) for r in rows]


async def get_preferred_spin_ids(flat_id: str, spin_ids: list[str]) -> list[tuple[str, int]]:
    """Return [(spin_id, order_count)] sorted by order_count desc for the given spin_ids."""
    if not spin_ids:
        return []
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT spin_id, order_count FROM item_preferences "
            "WHERE flat_id = $1 AND spin_id = ANY($2) ORDER BY order_count DESC",
            flat_id, spin_ids,
        )
        return [(r["spin_id"], r["order_count"]) for r in rows]
