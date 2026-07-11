"""
Address selection flow — used during onboarding and when the user requests a change.
State is kept in-memory; only one pending selection per flat at a time.
"""
import logging
import app.swiggy.client as swiggy
import app.db as db
from app.bot.telegram import send_message

log = logging.getLogger("bot.address")

# flat_id -> list of address dicts returned by get_addresses
pending_address_selection: dict[str, list] = {}


async def prompt_address_selection(chat_id: str, flat: dict) -> None:
    token = flat["swiggy_access_token"]
    result = await swiggy.get_addresses(token)
    addresses = result.get("addresses", [])
    if not addresses:
        await send_message(chat_id, "⚠️ No saved addresses on Swiggy. Add one in the Swiggy app first.")
        return
    pending_address_selection[chat_id] = addresses
    lines = ["📍 *Choose a delivery address:*"]
    for i, addr in enumerate(addresses, 1):
        label = addr.get("addressTag") or addr.get("addressCategory", "")
        line = addr.get("addressLine", "")
        lines.append(f"{i}. *{label}* — {line}")
    lines.append("\nReply with the number (e.g. *1*)")
    await send_message(chat_id, "\n".join(lines))


async def handle_address_selection(chat_id: str, message: str, flat: dict) -> None:
    addresses = pending_address_selection.get(chat_id, [])
    try:
        choice = int(message.strip()) - 1
        if choice < 0 or choice >= len(addresses):
            raise ValueError
    except ValueError:
        await send_message(chat_id, f"Please reply with a number between 1 and {len(addresses)}.")
        return

    selected = addresses[choice]
    address_id = selected.get("id")
    label = selected.get("addressTag") or selected.get("addressCategory", "")
    address_line = selected.get("addressLine", "")

    await db.save_default_address(flat["flat_id"], address_id, f"{label} — {address_line}")
    del pending_address_selection[chat_id]
    await send_message(
        chat_id,
        f"✅ Delivery address set to:\n*{label}* — {address_line}\n\nYou're all set!",
    )
