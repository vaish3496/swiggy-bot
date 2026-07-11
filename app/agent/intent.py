"""
Shared utilities for DeepSeek calls and conversation logging.
Used by router node and cart node.
"""
import json
import logging
import pathlib
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL

log = logging.getLogger("agent.intent")

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
_CONV_LOG = pathlib.Path("conversation.log")
_IST = ZoneInfo("Asia/Kolkata")


def _conv_log(user_message: str, messages: list[dict], raw_response: dict) -> None:
    now = datetime.now(_IST).strftime("%Y-%m-%d %H:%M:%S IST")
    choice = raw_response.get("choices", [{}])[0]
    msg = choice.get("message", {})
    tool_calls = msg.get("tool_calls", [])
    thinking = msg.get("reasoning_content", "")

    if tool_calls:
        fn = tool_calls[0]["function"]
        output = f"TOOL: {fn['name']}({fn['arguments']})"
    else:
        output = f"TEXT: {msg.get('content', '').strip()}"

    history_lines = [
        f"  [{m['role'].upper()}] {m['content'][:120]}{'...' if len(m.get('content', '')) > 120 else ''}"
        for m in messages if m["role"] != "system"
    ]

    lines = [
        f"\n{'='*70}",
        f"[{now}]",
        f"USER INPUT : {user_message}",
        f"HISTORY    : {len(history_lines)} messages in context",
        *history_lines,
        f"MODEL INPUT: {DEEPSEEK_MODEL} | mode=json_object",
        f"THINKING   : {thinking[:300] + '...' if len(thinking) > 300 else thinking or '(none)'}",
        f"OUTPUT     : {output}",
        f"USAGE      : {raw_response.get('usage', {})}",
    ]
    with _CONV_LOG.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


async def identify_item_to_remove(cart_items: list[dict], user_request: str) -> str | None:
    """Ask DeepSeek which spinId the user wants to remove. Returns spinId or None."""
    cart_list = "\n".join(
        f"- spinId: {i['spinId']}, name: {i.get('itemName', '')}"
        for i in cart_items
    )
    prompt = (
        f"Cart items:\n{cart_list}\n\n"
        f"The user wants to remove: \"{user_request}\"\n\n"
        "Reply with ONLY the spinId of the best matching item. "
        "If nothing matches, reply with the word: none"
    )
    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(2):
            try:
                resp = await client.post(
                    f"{_DEEPSEEK_BASE_URL}/chat/completions",
                    headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
                    json={
                        "model": DEEPSEEK_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                break
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt == 0:
                    log.warning("identify_item_to_remove: 500 on attempt 1, retrying")
                    continue
                return None
            except (httpx.ReadTimeout, httpx.TimeoutException):
                return None
        else:
            return None

    text = resp.json()["choices"][0]["message"]["content"].strip()
    log.info("identify_item_to_remove: %s -> %s", user_request, text)
    return None if text.lower() == "none" else text
