from datetime import datetime
from app.db.connection import get_pool


async def save_message(flat_id: str, role: str, content: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO chat_messages (flat_id, role, content, created_at) VALUES ($1, $2, $3, $4)",
            flat_id, role, content, int(datetime.utcnow().timestamp()),
        )


async def get_recent_messages(flat_id: str, limit: int = 100) -> list[dict]:
    """Return the most recent messages for a chat, oldest first (for LLM history)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT role, content FROM chat_messages "
            "WHERE flat_id = $1 ORDER BY created_at DESC LIMIT $2",
            flat_id, limit,
        )
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
