"""
APScheduler-based order scheduling.
Handles one-time and recurring order placement.
Jobs are persisted in DB and reloaded on restart.
"""
import logging
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

import app.db as db
import app.swiggy.client as swiggy
from app.bot.telegram import send_message

log = logging.getLogger("scheduler")
IST = ZoneInfo("Asia/Kolkata")

scheduler = AsyncIOScheduler(timezone=IST)


async def execute_order(flat_id: str, job_id: str, is_recurring: bool = False) -> None:
    """Place the cart as a COD order. Called by APScheduler or directly for immediate orders."""
    flat = await db.get_flat(flat_id)

    if not flat or not flat.get("swiggy_access_token"):
        log.warning("execute_order: flat %s has no token, skipping", flat_id)
        return

    token = flat["swiggy_access_token"]
    try:
        result = await swiggy.checkout("COD", token)
        order_id = result.get("orderId", "")
        await send_message(
            flat_id,
            f"✅ Order placed!\nOrder ID: `{order_id}`\nPayment: Cash on Delivery",
        )
        await db.clear_cart(flat_id)
        if not is_recurring:
            await db.mark_order_placed(job_id)
            if scheduler.get_job(job_id):
                scheduler.remove_job(job_id)
    except Exception as e:
        await send_message(flat_id, f"❌ Failed to place order: {str(e)}")


def schedule_once(flat_id: str, run_at_str: str, scheduled_by: str) -> tuple[str, str, datetime]:
    """
    Schedule a one-time order.
    run_at_str: "HH:MM" (today/tomorrow auto-resolved) or "YYYY-MM-DD HH:MM".
    Returns (job_id, human description, resolved datetime).
    """
    from datetime import timedelta
    now = datetime.now(IST)

    if len(run_at_str) == 5:  # "HH:MM"
        h, m = map(int, run_at_str.split(":"))
        run_at = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if run_at <= now:
            run_at += timedelta(days=1)
    else:  # "YYYY-MM-DD HH:MM"
        run_at = datetime.strptime(run_at_str, "%Y-%m-%d %H:%M").replace(tzinfo=IST)

    job_id = f"once_{flat_id}_{uuid.uuid4().hex[:8]}"
    scheduler.add_job(
        execute_order,
        trigger=DateTrigger(run_date=run_at),
        args=[flat_id, job_id, False],
        id=job_id,
    )
    description = run_at.strftime("%d %b %Y at %I:%M %p IST")
    return job_id, description, run_at


def schedule_recurring(flat_id: str, cron_expr: str, description: str, scheduled_by: str) -> tuple[str, str]:
    """
    Schedule a recurring order using a cron expression (minute hour day month dow).
    Returns (job_id, description).
    """
    job_id = f"recur_{flat_id}_{uuid.uuid4().hex[:8]}"
    parts = cron_expr.split()
    trigger = CronTrigger(
        minute=parts[0], hour=parts[1],
        day=parts[2], month=parts[3], day_of_week=parts[4],
        timezone=IST,
    )
    scheduler.add_job(execute_order, trigger=trigger, args=[flat_id, job_id, True], id=job_id)
    return job_id, description


def cancel_job(job_id: str) -> bool:
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        return True
    return False


async def reload_schedules() -> None:
    """Re-register all pending scheduled jobs from DB on startup."""
    now = datetime.now(IST)
    from app.db.connection import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM scheduled_orders WHERE status = 'pending'")
        schedules = [dict(r) for r in rows]

    for s in schedules:
        job_id = s["job_id"]
        flat_id = s["flat_id"]

        if s["is_recurring"]:
            cron_expr = s.get("cron_expr")
            if not cron_expr:
                continue
            parts = cron_expr.split()
            trigger = CronTrigger(
                minute=parts[0], hour=parts[1],
                day=parts[2], month=parts[3], day_of_week=parts[4],
                timezone=IST,
            )
            scheduler.add_job(
                execute_order, trigger=trigger,
                args=[flat_id, job_id, True], id=job_id, replace_existing=True,
            )
            log.info("Reloaded recurring job %s", job_id)
        else:
            try:
                run_at = datetime.fromisoformat(s["run_at"])
                if run_at.tzinfo is None:
                    run_at = run_at.replace(tzinfo=IST)
            except (ValueError, TypeError):
                log.warning("Skipping job %s — unparseable run_at: %s", job_id, s["run_at"])
                await db.cancel_scheduled_order(job_id)
                continue

            if run_at <= now:
                log.warning("Skipping past job %s (was %s)", job_id, run_at)
                await db.cancel_scheduled_order(job_id)
                continue

            scheduler.add_job(
                execute_order, trigger=DateTrigger(run_date=run_at),
                args=[flat_id, job_id, False], id=job_id, replace_existing=True,
            )
            log.info("Reloaded one-time job %s for %s", job_id, run_at)
