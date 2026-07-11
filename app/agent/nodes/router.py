"""
Router node — calls DeepSeek in JSON mode to determine intent and route to the right agent.
Uses response_format: json_object instead of tool calling to prevent hallucinated responses.
"""
import json
import logging
import httpx

from app.agent.state import BotState
from app.agent.tools import SYSTEM_PROMPT
from app.agent.intent import _conv_log, _DEEPSEEK_BASE_URL
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL

log = logging.getLogger("agent.router")

_VALID_ACTIONS = {
    "add_items", "remove_item", "show_cart", "clear_cart",
    "search_item", "place_now", "schedule_once", "schedule_recurring",
    "cancel_schedule", "show_schedules", "track_order", "show_orders",
    "show_go_to_items", "show_flat_info", "change_address", "help", "respond",
}


async def router_node(state: BotState) -> dict:
    user_message = state["user_message"]
    history = state.get("history", [])

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    log.info("Router: calling DeepSeek (%s)", DEEPSEEK_MODEL)

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                f"{_DEEPSEEK_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
                json={
                    "model": DEEPSEEK_MODEL,
                    "response_format": {"type": "json_object"},
                    "messages": messages,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                log.warning("Router: rate limit (429)")
                return _respond("Sorry, I'm a bit busy right now. Please try again in a moment!")
            if e.response.status_code == 402:
                log.error("Router: insufficient balance (402)")
                return _respond("Sorry, the bot is out of credits. Please top up DeepSeek.")
            if e.response.status_code >= 500:
                log.warning("Router: server error (%s)", e.response.status_code)
                return _respond("Sorry, I couldn't process that. Please try again.")
            raise

    raw = resp.json()
    _conv_log(user_message, messages, raw)

    content = raw["choices"][0].get("message", {}).get("content", "")
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        log.error("Router: invalid JSON from model: %r", content[:200])
        return _respond("Sorry, I couldn't understand that.")

    action = data.get("action", "respond")

    if action not in _VALID_ACTIONS:
        log.warning("Router: unknown action %r, falling back to respond", action)
        action = "respond"

    intent = _build_intent(action, data)
    log.info("Router: action=%s intent=%s", action, intent)
    return {"action": action, "intent": intent}


def _build_intent(action: str, data: dict) -> dict:
    intent = {"action": action}
    if action == "add_items":
        intent["items"] = data.get("items", [])
    elif action == "remove_item":
        intent["name"] = data.get("name", "")
    elif action == "search_item":
        intent["query"] = data.get("query", "")
    elif action == "schedule_once":
        intent["time"] = data.get("time", "")
        intent["date"] = data.get("date", "today")
    elif action == "schedule_recurring":
        intent["cron"] = data.get("cron", "")
        intent["description"] = data.get("description", "")
    elif action == "track_order":
        intent["order_id"] = data.get("order_id", "")
    elif action == "respond":
        intent["message"] = data.get("message", "")
    return intent


def _respond(message: str) -> dict:
    return {"action": "respond", "intent": {"action": "respond", "message": message}}
