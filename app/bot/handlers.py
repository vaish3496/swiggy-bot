"""
Telegram message handlers — pre-processing (auth, address) then graph invocation.
"""
import re
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ChatMemberHandler, MessageHandler, filters

import app.db as db
from app.agent.graph import graph
from app.bot.telegram import application, send_message
from app.bot import address as addr_flow
from app.bot.oauth import start_oauth

log = logging.getLogger("bot.handlers")

IST = ZoneInfo("Asia/Kolkata")
_MAX_HISTORY = 100


def register_handlers() -> None:
    application.add_handler(ChatMemberHandler(_handle_bot_added, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, _handle_message))


# ---------------------------------------------------------------------------
# Telegram event handlers
# ---------------------------------------------------------------------------

async def _handle_bot_added(update: Update, context) -> None:
    member = update.my_chat_member
    if member.new_chat_member.status in ("member", "administrator"):
        chat_id = str(update.effective_chat.id)
        admin_id = str(update.effective_user.id)
        chat_title = update.effective_chat.title or "your group"
        await db.create_flat_if_not_exists(chat_id, admin_id)
        await send_message(
            chat_id,
            f"👋 Hi! I'm your Swiggy Instamart bot for *{chat_title}*.\n\n"
            "Type *connect swiggy* to link a Swiggy account and get started.",
        )


async def _handle_message(update: Update, context) -> None:
    if not update.message or not update.message.text:
        return

    chat_id = str(update.effective_chat.id)
    username = update.effective_user.first_name or str(update.effective_user.id)
    message = update.message.text.strip()
    log.info("[%s] %s: %s", chat_id, username, message)

    await db.create_flat_if_not_exists(chat_id, str(update.effective_user.id))
    flat = await db.get_flat(chat_id)

    # Address selection in progress
    if chat_id in addr_flow.pending_address_selection:
        await addr_flow.handle_address_selection(chat_id, message, flat)
        return

    # Connect Swiggy
    if "connect swiggy" in message.lower():
        await start_oauth(chat_id)
        return

    # Token check
    token = flat.get("swiggy_access_token")
    token_expired = (
        flat.get("swiggy_token_expires_at")
        and int(datetime.utcnow().timestamp()) >= flat["swiggy_token_expires_at"]
    )
    if not token or token_expired:
        reason = "expired" if token_expired else "not connected"
        await send_message(
            chat_id,
            f"⚠️ Swiggy session {reason}. Type *connect swiggy* to re-authenticate.",
        )
        return

    # Address check
    if not flat.get("default_address_id"):
        await addr_flow.prompt_address_selection(chat_id, flat)
        return

    # Run the LangGraph agent
    history = await db.get_recent_messages(chat_id, _MAX_HISTORY)

    state = await graph.ainvoke({
        "user_message": message,
        "username": username,
        "flat": flat,
        "flat_id": chat_id,
        "history": history,
        "action": "",
        "intent": {},
        "reply": "",
    })

    reply = state.get("reply", "")
    # Strip any metadata blocks that should never reach Telegram
    telegram_reply = re.sub(r'\n?ITEMS_META::.*?::END_ITEMS_META', '', reply, flags=re.DOTALL).strip()
    telegram_reply = re.sub(r'\n?\[ITEMS:.*?\]', '', telegram_reply, flags=re.DOTALL).strip()
    await db.save_message(chat_id, "user", message)
    if telegram_reply:
        await send_message(chat_id, telegram_reply)
        if not state.get("db_saved"):
            await db.save_message(chat_id, "assistant", telegram_reply)
