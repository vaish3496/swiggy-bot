"""
LangGraph graph definition for the Swiggy flat bot.

Flow:
    [router] → (conditional) → [cart_agent | order_agent | info_agent | converse] → END
"""
from langgraph.graph import StateGraph, END

from app.agent.state import BotState
from app.agent.nodes.router import router_node
from app.agent.nodes.cart import cart_node
from app.agent.nodes.order import order_node
from app.agent.nodes.info import info_node
from app.agent.nodes.converse import converse_node

_CART_ACTIONS = {"add_items", "remove_item", "show_cart", "clear_cart"}
_ORDER_ACTIONS = {"place_now", "schedule_once", "schedule_recurring", "cancel_schedule", "show_schedules"}
_INFO_ACTIONS = {"search_item", "track_order", "show_orders", "show_go_to_items", "show_flat_info", "change_address", "help"}


def _route(state: BotState) -> str:
    action = state.get("action", "respond")
    if action in _CART_ACTIONS:
        return "cart_agent"
    if action in _ORDER_ACTIONS:
        return "order_agent"
    if action in _INFO_ACTIONS:
        return "info_agent"
    return "converse"


builder = StateGraph(BotState)

builder.add_node("router", router_node)
builder.add_node("cart_agent", cart_node)
builder.add_node("order_agent", order_node)
builder.add_node("info_agent", info_node)
builder.add_node("converse", converse_node)

builder.set_entry_point("router")

builder.add_conditional_edges(
    "router",
    _route,
    {
        "cart_agent": "cart_agent",
        "order_agent": "order_agent",
        "info_agent": "info_agent",
        "converse": "converse",
    },
)

builder.add_edge("cart_agent", END)
builder.add_edge("order_agent", END)
builder.add_edge("info_agent", END)
builder.add_edge("converse", END)

graph = builder.compile()
