"""
Info agent node — handles search, track, orders, go-to items, flat info, address, help.
"""
import json
import logging

from app.agent.state import BotState
import app.db as db
import app.swiggy.client as swiggy
from app.bot import address as addr_flow

log = logging.getLogger("agent.info")


async def info_node(state: BotState) -> dict:
    action = state["action"]
    intent = state["intent"]
    flat = state["flat"]
    flat_id = state["flat_id"]
    token = flat["swiggy_access_token"]

    log.info("[info_agent] action=%s intent=%s", action, intent)

    if action == "search_item":
        query = intent.get("query", "")
        try:
            result = await swiggy.search_products(query, flat["default_address_id"], token)
            products = result.get("products", [])
            if not products:
                return {"reply": f"No results found for '{query}' on Instamart."}

            display_lines = [f"*Search results for '{query}':*"]
            item_meta: dict[str, dict] = {}  # idx → {spinId, skuId, name}
            idx = 1
            for p in products[:8]:
                name = p.get("displayName", "")
                in_stock_variants = [v for v in p.get("variations", [])[:2] if v.get("isInStockAndAvailable", True)]
                if not in_stock_variants:
                    display_lines.append(f"❌ {name} — out of stock")
                    continue
                for v in in_stock_variants:
                    spin_id = v.get("spinId", "")
                    sku_id = v.get("skuId", "")
                    size = v.get("quantityDescription", "")
                    price_raw = v.get("price", {})
                    offer = price_raw.get("offerPrice", "") if isinstance(price_raw, dict) else price_raw
                    label = f"{name} — {size} @ ₹{offer}" if size else name
                    display_lines.append(f"{idx}. {label}")
                    item_meta[str(idx)] = {"spinId": spin_id, "skuId": sku_id, "name": f"{name} ({size})" if size else name}
                    idx += 1
                    if idx > 8:
                        break
                if idx > 8:
                    break

            display_lines.append("\nSay 'add X' or 'add option 2' to add to cart.")
            reply = "\n".join(display_lines)

            # Save to DB with hidden ITEMS_META so the router LLM can extract spinId/skuId
            # in follow-up messages. Only the clean reply is sent to Telegram.
            db_content = reply + f"\nITEMS_META::{json.dumps(item_meta)}::END_ITEMS_META"
            await db.save_message(flat_id, "assistant", db_content)

            return {"reply": reply, "db_saved": True}
        except Exception as e:
            return {"reply": f"Search failed: {str(e)}"}

    if action == "track_order":
        order_id = intent.get("order_id", "")
        try:
            if not order_id:
                orders_result = await swiggy.get_orders(token)
                orders = orders_result.get("orders", [])
                if not orders:
                    return {"reply": "No recent orders found to track."}
                order_id = orders[0].get("orderId", "")
            if not order_id:
                return {"reply": "Couldn't determine an order to track."}
            result = await swiggy.track_order(order_id, token)
            status = result.get("status") or result.get("text", "No tracking info available.")
            return {"reply": f"📦 *Order status:* {status}"}
        except Exception as e:
            return {"reply": f"Couldn't fetch order status: {str(e)}"}

    if action == "show_orders":
        try:
            result = await swiggy.get_orders(token)
            orders = result.get("orders", [])
            if not orders:
                return {"reply": "No past orders found."}
            lines = ["*Recent orders:*"]
            for o in orders[:5]:
                order_id = o.get("orderId", "")
                total = o.get("total", o.get("orderTotal", ""))
                date_str = (o.get("createdAt") or o.get("date", ""))[:10]
                status = o.get("status", "")
                lines.append(f"• #{order_id} — ₹{total} on {date_str} ({status})")
            return {"reply": "\n".join(lines)}
        except Exception as e:
            return {"reply": f"Couldn't fetch orders: {str(e)}"}

    if action == "show_go_to_items":
        try:
            result = await swiggy.your_go_to_items(flat["default_address_id"], token)
            products = result.get("products", [])
            if not products:
                return {"reply": "No frequently ordered items found yet."}
            lines = ["*Your go-to items:*"]
            for p in products[:10]:
                name = p.get("displayName", "")
                variations = p.get("variations", [])
                if variations:
                    v = variations[0]
                    price = v.get("price", {})
                    offer = price.get("offerPrice", "") if isinstance(price, dict) else price
                    lines.append(f"• {name} — {v.get('quantityDescription', '')} @ ₹{offer}")
                else:
                    lines.append(f"• {name}")
            lines.append("\nSay 'add X' to add any of these to cart.")
            return {"reply": "\n".join(lines)}
        except Exception as e:
            return {"reply": f"Couldn't fetch go-to items: {str(e)}"}

    if action == "show_flat_info":
        return {"reply": (
            f"*Flat info:*\n"
            f"Address: {flat.get('default_address_label', 'not set')}\n"
            f"Swiggy: {'✅ connected' if flat.get('swiggy_access_token') else '❌ not connected'}"
        )}

    if action == "change_address":
        await addr_flow.prompt_address_selection(flat_id, flat)
        return {"reply": ""}

    if action == "help":
        return {"reply": (
            "*Swiggy Flat Bot — Commands*\n\n"
            "🛒 `add 2 onions and 1 bread`\n"
            "📋 `show cart`\n"
            "🗑️ `remove onions` / `clear cart`\n"
            "📦 `place order now`\n"
            "⏰ `order at 10pm`\n"
            "🔁 `order every day at 9pm`\n"
            "❌ `cancel schedule`\n"
            "🔍 `what options for onions are there?`\n"
            "📍 `change address`\n"
            "🔗 `connect swiggy`"
        )}

    return {"reply": "I didn't understand that. Type *help* for commands."}
