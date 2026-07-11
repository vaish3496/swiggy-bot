"""
Cart agent node — handles add, remove, show, clear cart actions.
"""
import logging

from app.agent.state import BotState
from app.agent.actions import search_and_add_items, get_cart_summary
from app.agent.intent import identify_item_to_remove
import app.db as db
import app.swiggy.client as swiggy

log = logging.getLogger("agent.cart")


async def cart_node(state: BotState) -> dict:
    action = state["action"]
    intent = state["intent"]
    flat = state["flat"]
    flat_id = state["flat_id"]
    username = state["username"]
    token = flat["swiggy_access_token"]

    log.info("[cart_agent] action=%s intent=%s", action, intent)

    if action == "add_items":
        items = intent.get("items", [])
        results = await search_and_add_items(items, flat_id, flat["default_address_id"], token, username)
        return {"reply": f"🛒 *{username}* added to cart:\n" + "\n".join(results)}

    if action == "show_cart":
        return {"reply": await get_cart_summary(flat_id, token)}

    if action == "remove_item":
        name = intent.get("name", "")
        cart_data = await swiggy.get_cart(token)
        swiggy_items = cart_data.get("items", [])
        if not swiggy_items:
            return {"reply": "Your cart is empty."}

        spin_id = await identify_item_to_remove(swiggy_items, name)
        match = next((i for i in swiggy_items if i["spinId"] == spin_id), None)

        if not match:
            if spin_id is None:
                return {"reply": "Sorry, couldn't identify the item right now. Please try again."}
            return {"reply": f"Couldn't find '{name}' in cart."}

        remaining = [
            {"spinId": i["spinId"], "skuId": i.get("skuId", ""), "quantity": i["quantity"]}
            for i in swiggy_items if i["spinId"] != match["spinId"]
        ]
        try:
            if remaining:
                await swiggy.update_cart(remaining, flat["default_address_id"], token)
            else:
                await swiggy.clear_cart(token)
        except Exception as e:
            return {"reply": f"⚠️ Couldn't update cart: {str(e)[:100]}"}
        await db.remove_from_cart(flat_id, match["spinId"])
        return {"reply": f"🗑️ *{username}* removed *{match['itemName']}* from cart."}

    if action == "clear_cart":
        await swiggy.clear_cart(token)
        await db.clear_cart(flat_id)
        return {"reply": f"🗑️ Cart cleared by *{username}*."}

    return {"reply": "Something went wrong with the cart action."}
