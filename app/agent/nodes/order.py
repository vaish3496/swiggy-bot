"""
Order agent node — handles place, schedule, cancel, show schedule actions.
"""
import uuid
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.agent.state import BotState
import app.db as db
import app.scheduler.jobs as scheduler_jobs
from app.bot.telegram import send_message

log = logging.getLogger("agent.order")
IST = ZoneInfo("Asia/Kolkata")


async def order_node(state: BotState) -> dict:
    action = state["action"]
    intent = state["intent"]
    flat_id = state["flat_id"]
    username = state["username"]

    log.info("[order_agent] action=%s intent=%s", action, intent)

    if action == "place_now":
        await send_message(flat_id, "⏳ Placing order now...")
        await scheduler_jobs.execute_order(flat_id, f"manual_{uuid.uuid4().hex[:8]}")
        return {"reply": ""}

    if action == "schedule_once":
        time_str = intent.get("time", "")
        date_str = intent.get("date", "today")
        now = datetime.now(IST)
        if date_str == "tomorrow":
            run_at = f"{(now + timedelta(days=1)).date().isoformat()} {time_str}"
        elif date_str == "today" or not date_str:
            run_at = time_str
        else:
            run_at = f"{date_str} {time_str}"
        job_id, desc, run_at_dt = scheduler_jobs.schedule_once(flat_id, run_at, username)
        await db.save_scheduled_order(flat_id, username, run_at_dt.isoformat(), False, None, job_id)
        return {"reply": f"⏰ Order scheduled for *{desc}* by {username}."}

    if action == "schedule_recurring":
        cron = intent.get("cron", "")
        description = intent.get("description", cron)
        job_id, desc = scheduler_jobs.schedule_recurring(flat_id, cron, description, username)
        await db.save_scheduled_order(flat_id, username, desc, True, cron, job_id)
        return {"reply": f"🔁 Recurring order set: *{desc}* (by {username})"}

    if action == "cancel_schedule":
        schedules = await db.get_pending_schedules(flat_id)
        if not schedules:
            return {"reply": "No pending schedules to cancel."}
        latest = schedules[-1]
        scheduler_jobs.cancel_job(latest["job_id"])
        await db.cancel_scheduled_order(latest["job_id"])
        return {"reply": f"❌ Schedule cancelled by {username}."}

    if action == "show_schedules":
        schedules = await db.get_pending_schedules(flat_id)
        if not schedules:
            return {"reply": "No pending schedules."}
        lines = ["*Pending schedules:*"]
        for s in schedules:
            tag = "🔁" if s["is_recurring"] else "⏰"
            lines.append(f"{tag} {s['run_at']} (by {s['scheduled_by']})")
        return {"reply": "\n".join(lines)}

    return {"reply": "Something went wrong with the order action."}
