"""
Thin wrapper around all 13 Swiggy Instamart MCP tools via streamable HTTP.
Endpoint: POST https://mcp.swiggy.com/im
Auth: OAuth 2.1 bearer token
"""
import json
import logging
import httpx
from app.config import SWIGGY_MCP_URL

log = logging.getLogger("swiggy.client")

MCP_ENDPOINT = f"{SWIGGY_MCP_URL}/im"


async def call_tool(tool_name: str, arguments: dict, access_token: str) -> dict:
    """Call a Swiggy MCP tool and return the result dict."""
    log.info("MCP call: %s %s", tool_name, arguments)
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(MCP_ENDPOINT, json=payload, headers=headers)
        log.info("MCP response status: %s", resp.status_code)
        resp.raise_for_status()
        data = resp.json()

    log.debug("MCP raw response: %s", data)

    if "error" in data:
        log.error("MCP error for %s: %s", tool_name, data["error"])
        raise RuntimeError(f"MCP error: {data['error']}")

    result = data.get("result", {})

    if result.get("isError"):
        content = result.get("content", [])
        msg = content[0].get("text", "Unknown error") if content else "Unknown error"
        log.error("MCP isError for %s: %s", tool_name, msg[:200])
        raise RuntimeError(f"Swiggy error: {msg[:200]}")

    # Prefer structuredContent if present
    structured = result.get("structuredContent")
    if structured:
        log.info("MCP %s success (structuredContent)", tool_name)
        return structured

    content = result.get("content", [])
    if content and content[0].get("type") == "text":
        try:
            parsed = json.loads(content[0]["text"])
            log.info("MCP %s success (parsed text)", tool_name)
            return parsed
        except json.JSONDecodeError:
            log.warning("Could not parse MCP text as JSON: %s", content[0]["text"][:300])
            return {"text": content[0]["text"]}
    return result


# ---------------------------------------------------------------------------
# Discover
# ---------------------------------------------------------------------------

async def get_addresses(access_token: str) -> dict:
    return await call_tool("get_addresses", {}, access_token)


async def create_address(address: dict, access_token: str) -> dict:
    """Create a new delivery address. address dict per Swiggy MCP schema."""
    return await call_tool("create_address", {"address": address}, access_token)


async def delete_address(address_id: str, access_token: str) -> dict:
    return await call_tool("delete_address", {"addressId": address_id}, access_token)


async def search_products(query: str, address_id: str, access_token: str) -> dict:
    return await call_tool("search_products", {"query": query, "addressId": address_id}, access_token)


async def your_go_to_items(address_id: str, access_token: str) -> dict:
    return await call_tool("your_go_to_items", {"addressId": address_id}, access_token)


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------

async def get_cart(access_token: str) -> dict:
    """Returns cart dict. Returns {"items": []} when cart is empty or in an invalid state."""
    try:
        return await call_tool("get_cart", {}, access_token)
    except RuntimeError:
        return {"items": []}


async def update_cart(items: list[dict], address_id: str, access_token: str) -> dict:
    """Replace entire cart. items = [{"spinId": "...", "quantity": N}, ...]"""
    return await call_tool("update_cart", {"items": items, "selectedAddressId": address_id}, access_token)


async def clear_cart(access_token: str) -> dict:
    return await call_tool("clear_cart", {}, access_token)


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

async def checkout(payment_method: str, access_token: str) -> dict:
    return await call_tool("checkout", {"paymentMethod": payment_method}, access_token)


# ---------------------------------------------------------------------------
# Track
# ---------------------------------------------------------------------------

async def get_orders(access_token: str) -> dict:
    return await call_tool("get_orders", {}, access_token)


async def get_order_details(order_id: str, access_token: str) -> dict:
    return await call_tool("get_order_details", {"orderId": order_id}, access_token)


async def track_order(order_id: str, access_token: str) -> dict:
    return await call_tool("track_order", {"orderId": order_id}, access_token)
