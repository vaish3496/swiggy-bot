"""
Converse node — sends a natural language reply with no Swiggy action.
"""
import logging

from app.agent.state import BotState

log = logging.getLogger("agent.converse")


async def converse_node(state: BotState) -> dict:
    msg = state["intent"].get("message", "").strip()
    log.info("[converse] reply=%s", (msg or "default")[:80])
    return {"reply": msg or "Hey! How can I help you with your grocery order? Type *help* to see what I can do."}
