"""
Telegram bot interface — send helpers and polling loop.
Handlers are registered from main.py to avoid circular imports.
"""
import logging
from telegram.ext import Application
from app.config import TELEGRAM_BOT_TOKEN

log = logging.getLogger("bot.telegram")

application: Application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


async def send_message(chat_id: str | int, text: str) -> None:
    try:
        await application.bot.send_message(
            chat_id=int(chat_id),
            text=text,
            parse_mode="Markdown",
        )
    except Exception:
        try:
            await application.bot.send_message(chat_id=int(chat_id), text=text)
        except Exception as e:
            log.error("Failed to send message to %s: %s", chat_id, e)


async def start_polling() -> None:
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    log.info("Telegram bot polling started")


async def stop() -> None:
    if application.updater.running:
        await application.updater.stop()
    await application.stop()
    await application.shutdown()
