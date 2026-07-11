from typing import TypedDict


class BotState(TypedDict, total=False):
    # Inputs — set before graph starts
    user_message: str
    username: str
    flat: dict
    flat_id: str
    history: list[dict]

    # Set by router node
    action: str
    intent: dict

    # Set by agent nodes
    reply: str       # sent to Telegram
    db_saved: bool   # if True, node already saved the assistant message to DB; handlers.py skips saving
