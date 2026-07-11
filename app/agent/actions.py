"""
Cart actions: searching products and building cart summaries.
Swiggy is the source of truth for cart state.
DB is used only for added_by tracking and variant preferences.
"""
import json
import asyncio
import logging
import httpx

import app.db as db
import app.swiggy.client as swiggy
from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL

log = logging.getLogger("agent.actions")

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

async def _llm_json(system: str, user: str) -> dict | None:
    """Call DeepSeek expecting a JSON object response."""
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            resp = await client.post(
                f"{_DEEPSEEK_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
                json={
                    "model": DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            log.warning("LLM JSON call failed: %s", e)
            return None


async def _resolve_search_query(user_request: str, past_items: list[dict], goto_items: list[dict]) -> str:
    """LLM call 1: Turn user's request into the best Swiggy search query, using order history for context."""
    past_str = "\n".join(
        f"- {i['product_name']} (ordered {i['order_count']}x)" for i in past_items[:15]
    ) or "none"
    goto_str = "\n".join(
        f"- {p.get('displayName', '')}" for p in goto_items[:10]
    ) or "none"

    result = await _llm_json(
        system=(
            "You are a grocery assistant that resolves what item a user wants from Swiggy Instamart. "
            "Given their request and shopping history, return the best Swiggy search query. "
            "Always preserve size/weight hints from the user (like 500g, 1kg, 250ml). "
            "Return only valid JSON."
        ),
        user=(
            f"User wants to add: \"{user_request}\"\n\n"
            f"Previously ordered items (most frequent first):\n{past_str}\n\n"
            f"Go-to items on Swiggy:\n{goto_str}\n\n"
            "Return JSON: {\"search_query\": \"<best search term>\", \"notes\": \"<brief reasoning>\"}"
        ),
    )

    if result and result.get("search_query"):
        q = result["search_query"]
        log.info("LLM 1: resolved '%s' → '%s' (%s)", user_request, q, result.get("notes", ""))
        return q

    return user_request  # fallback: use raw request


async def _pick_best_variant(user_request: str, products: list[dict]) -> dict:
    """
    LLM call 2: Pick the best matching variant from Swiggy search results.
    Returns:
      {"matched": True, "spinId": ..., "skuId": ..., "display": ...}
      {"matched": False, "options": ["option1", "option2", ...]}
    """
    variant_list = []
    for product in products[:6]:
        name = product.get("displayName", "")
        for variant in product.get("variations", [])[:3]:
            if not variant.get("isInStockAndAvailable", True):
                continue
            price_raw = variant.get("price", {})
            price = price_raw.get("offerPrice", "") if isinstance(price_raw, dict) else price_raw
            variant_list.append({
                "idx": len(variant_list) + 1,
                "product": name,
                "spinId": variant.get("spinId", ""),
                "skuId": variant.get("skuId", ""),
                "size": variant.get("quantityDescription", ""),
                "price": price,
            })

    if not variant_list:
        return {"matched": False, "options": [], "out_of_stock": True}

    variants_str = "\n".join(
        f"{v['idx']}. {v['product']} — {v['size']} @ ₹{v['price']}"
        for v in variant_list
    )

    result = await _llm_json(
        system=(
            "You are a grocery assistant matching a user's item request to Swiggy Instamart search results. "
            "Pick the variant that best matches what the user asked for. "
            "If the user specified a size (500g, 1kg, etc.), prioritise that. "
            "Only say no match if there is genuinely nothing close. "
            "Return only valid JSON."
        ),
        user=(
            f"User wants: \"{user_request}\"\n\n"
            f"Available variants:\n{variants_str}\n\n"
            "Return JSON:\n"
            "  If good match found: {\"matched\": true, \"idx\": <number>}\n"
            "  If no good match:    {\"matched\": false, \"top_idxs\": [<up to 4 best option numbers>]}"
        ),
    )

    # LLM failed — fall back to first variant
    if result is None:
        v = variant_list[0]
        log.warning("LLM 2 failed, falling back to first variant: %s", v["product"])
        return {"matched": True, "spinId": v["spinId"], "skuId": v["skuId"], "display": f"{v['product']} ({v['size']})"}

    if result.get("matched"):
        idx = result.get("idx", 1)
        match = next((v for v in variant_list if v["idx"] == idx), variant_list[0])
        log.info("LLM 2: matched variant %d: %s %s", idx, match["product"], match["size"])
        return {
            "matched": True,
            "spinId": match["spinId"],
            "skuId": match["skuId"],
            "display": f"{match['product']} ({match['size']})",
        }
    else:
        top_idxs = result.get("top_idxs", [v["idx"] for v in variant_list[:4]])
        options = [
            f"{v['product']} — {v['size']} @ ₹{v['price']}"
            for v in variant_list if v["idx"] in top_idxs
        ]
        log.info("LLM 2: no match for '%s', returning %d options", user_request, len(options))
        return {"matched": False, "options": options[:4]}


# ---------------------------------------------------------------------------
# Main cart action
# ---------------------------------------------------------------------------

async def search_and_add_items(
    items: list[dict],
    flat_id: str,
    address_id: str,
    access_token: str,
    added_by: str,
) -> list[str]:
    """
    For each item:
      1. LLM resolves what to search (using go-to + order history as context)
      2. Swiggy search
      3. LLM picks best variant — or returns options for the user to choose from
    Matched items are merged into the current cart and update_cart is called once.
    """
    results: list[str] = []
    new_items: dict[str, dict] = {}  # spinId -> {quantity, full_name, sku_id}

    # If all items already have spinId/skuId (picked from search results), skip context fetch entirely
    all_direct = all(item.get("spinId") and item.get("skuId") for item in items)

    if all_direct:
        past_prefs, goto_items = [], []
    else:
        # Fetch context in parallel: past preferences + go-to items
        past_prefs, goto_result = await asyncio.gather(
            db.get_all_item_preferences(flat_id),
            swiggy.your_go_to_items(address_id, access_token),
            return_exceptions=True,
        )
        if isinstance(past_prefs, Exception):
            past_prefs = []
        if isinstance(goto_result, Exception):
            goto_items = []
        else:
            goto_items = goto_result.get("products", [])

    for item in items:
        name = item.get("name", "")
        qty = item.get("quantity", 1)
        try:
            # Fast path: spinId/skuId already known (user picking from a previous search result)
            if item.get("spinId") and item.get("skuId"):
                spin_id = item["spinId"]
                sku_id = item["skuId"]
                log.info("Direct add (from search results): spinId=%s qty=%s", spin_id, qty)
                new_items[spin_id] = {"quantity": qty, "full_name": name, "sku_id": sku_id}
                results.append(f"✅ {qty}x {name}")
                continue

            # LLM call 1: resolve search query
            search_query = await _resolve_search_query(name, past_prefs, goto_items)

            log.info("Searching Swiggy for: %s (qty: %s)", search_query, qty)
            search_result = await swiggy.search_products(search_query, address_id, access_token)
            products = search_result.get("products", [])

            if not products:
                results.append(f"'{name}' not found on Swiggy Instamart.")
                continue

            # LLM call 2: pick best variant
            pick = await _pick_best_variant(name, products)

            if pick["matched"]:
                spin_id = pick["spinId"]
                sku_id = pick["skuId"]
                full_name = pick["display"]
                new_items[spin_id] = {"quantity": qty, "full_name": full_name, "sku_id": sku_id}
                results.append(f"✅ {qty}x {full_name}")
            else:
                if pick.get("out_of_stock"):
                    results.append(f"❌ *{name}* is out of stock at your location.")
                else:
                    options = pick.get("options", [])
                    if options:
                        opts_text = "\n".join(f"  {i+1}. {o}" for i, o in enumerate(options))
                        results.append(
                            f"❓ Couldn't find an exact match for *{name}*. Here's what's available:\n"
                            f"{opts_text}\n"
                            "_Reply with the number or name to add one._"
                        )
                    else:
                        results.append(f"'{name}' not found on Swiggy Instamart.")

        except Exception:
            log.exception("Error adding item: %s", name)
            results.append(f"❌ '{name}' — something went wrong, please try again.")

    if not new_items:
        return results

    # Fetch current Swiggy cart and merge (update_cart replaces the entire cart)
    try:
        current_cart = await swiggy.get_cart(access_token)
        existing: dict[str, dict] = {
            i["spinId"]: {"quantity": i["quantity"], "sku_id": i.get("skuId", "")}
            for i in current_cart.get("items", [])
        }
    except Exception:
        existing = {}

    merged = dict(existing)
    for spin_id, info in new_items.items():
        if spin_id in merged:
            merged[spin_id]["quantity"] += info["quantity"]
        else:
            merged[spin_id] = {"quantity": info["quantity"], "sku_id": info["sku_id"]}

    all_cart_items = [
        {"spinId": sid, "skuId": info["sku_id"], "quantity": info["quantity"]}
        for sid, info in merged.items()
    ]
    try:
        cart_response = await swiggy.update_cart(all_cart_items, address_id, access_token)
    except RuntimeError as e:
        err = str(e)
        if "Max Per Item Quantity Limit" in err:
            log.warning("Cart corrupt (quantity limit), clearing and retrying")
            try:
                await swiggy.clear_cart(access_token)
                await db.clear_cart(flat_id)
                new_only = [
                    {"spinId": sid, "skuId": info["sku_id"], "quantity": info["quantity"]}
                    for sid, info in new_items.items()
                ]
                cart_response = await swiggy.update_cart(new_only, address_id, access_token)
                results.append("⚠️ Previous cart was cleared (Swiggy quantity limit).")
            except RuntimeError as retry_err:
                results.append(f"⚠️ Cart update failed even after reset: {str(retry_err)[:120]}")
                return results
        else:
            results.append(f"⚠️ Cart update failed: {err[:120]}")
            return results

    # Update DB metadata for successfully added items
    for spin_id, info in new_items.items():
        await db.add_to_cart(flat_id, spin_id, info["full_name"], info["quantity"], added_by)
        await db.record_item_preference(flat_id, spin_id, info["full_name"])

    bill_text = _format_bill(cart_response)
    if bill_text:
        results.append(bill_text)
    return results


# ---------------------------------------------------------------------------
# Cart summary
# ---------------------------------------------------------------------------

async def get_cart_summary(flat_id: str, access_token: str) -> str:
    """Return a formatted cart summary. Swiggy is source of truth; DB enriches with added_by."""
    try:
        cart_data = await swiggy.get_cart(access_token)
    except Exception as e:
        log.warning("Could not fetch cart from Swiggy: %s", e)
        return "⚠️ Could not fetch cart from Swiggy. Try *clear cart* to reset and re-add items."

    swiggy_items = cart_data.get("items", [])
    if not swiggy_items:
        return "Your cart is empty."

    db_items = await db.get_cart(flat_id)
    added_by_map = {row["spin_id"]: row["added_by"] for row in db_items}

    lines = ["*Your shared cart:*"]
    for item in swiggy_items:
        spin_id = item.get("spinId", "")
        name = item.get("itemName", spin_id)
        qty = item.get("quantity", 1)
        price = item.get("discountedFinalPrice") or item.get("mrp", "")
        added_by = added_by_map.get(spin_id, "")
        by_str = f" (by {added_by})" if added_by else ""
        price_str = f" — ₹{price}" if price else ""
        lines.append(f"• {qty}x {name}{price_str}{by_str}")

    bill_text = _format_bill(cart_data)
    if bill_text:
        lines.append(bill_text)
    return "\n".join(lines)


def _format_bill(cart_response: dict) -> str:
    bill = cart_response.get("billBreakdown", {})
    if not bill:
        total = cart_response.get("cartTotalAmount", "")
        return f"\n💰 Cart total: *{total}*" if total else ""
    lines = ["\n💰 *Bill breakdown:*"]
    for item in bill.get("lineItems", []):
        lines.append(f"  {item['label']}: {item['value']}")
    to_pay = bill.get("toPay", {})
    if to_pay:
        lines.append("  ━━━━━━━━━━━━")
        lines.append(f"  *{to_pay['label']}: {to_pay['value']}*")
    return "\n".join(lines)
