"""
FastAPI application entry point.
Starts Telegram polling, APScheduler, and mounts the OAuth callback route.
"""
import asyncio
import logging

from fastapi import FastAPI

import app.db as db
from app.bot.handlers import register_handlers
from app.bot.oauth import router as oauth_router
from app.bot.telegram import start_polling, stop
from app.scheduler.jobs import scheduler, reload_schedules

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI()
app.include_router(oauth_router)


@app.on_event("startup")
async def startup() -> None:
    await db.init_db()
    scheduler.start()
    await reload_schedules()
    register_handlers()
    asyncio.create_task(start_polling())


@app.on_event("shutdown")
async def shutdown() -> None:
    scheduler.shutdown()
    await stop()
    await db.close_db()
