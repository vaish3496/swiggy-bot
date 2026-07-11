"""
Swiggy OAuth 2.1 + PKCE flow.
Generates the auth URL, handles the /auth/callback redirect, saves the token.
"""
import base64
import hashlib
import logging
import secrets
from datetime import datetime
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

import app.db as db
import app.swiggy.client as swiggy
from app.bot.telegram import send_message
from app.bot import address as addr_flow
from app.config import SWIGGY_MCP_URL, OAUTH_REDIRECT_BASE

log = logging.getLogger("bot.oauth")

router = APIRouter()

# state token -> {flat_id, code_verifier}
_oauth_states: dict[str, dict] = {}


async def start_oauth(chat_id: str) -> None:
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {"flat_id": chat_id, "code_verifier": code_verifier}

    params = {
        "response_type": "code",
        "client_id": "swiggy-flat-bot",
        "redirect_uri": f"{OAUTH_REDIRECT_BASE}/auth/callback",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "scope": "mcp:tools",
    }
    auth_url = f"{SWIGGY_MCP_URL}/auth/authorize?{urlencode(params)}"
    await send_message(
        chat_id,
        f"🔗 [Click here to connect your Swiggy account]({auth_url})\n\n"
        "After logging in you'll be redirected back automatically.",
    )


@router.get("/auth/callback")
async def auth_callback(code: str, state: str):
    state_data = _oauth_states.pop(state, None)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    flat_id = state_data["flat_id"]
    code_verifier = state_data["code_verifier"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SWIGGY_MCP_URL}/auth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": f"{OAUTH_REDIRECT_BASE}/auth/callback",
                "code_verifier": code_verifier,
                "client_id": "swiggy-flat-bot",
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 432000)
    expires_at = int(datetime.utcnow().timestamp()) + expires_in
    await db.save_swiggy_token(flat_id, access_token, expires_at)

    flat = await db.get_flat(flat_id)
    await send_message(flat_id, "✅ Swiggy connected! Now let's set your delivery address.")
    await addr_flow.prompt_address_selection(flat_id, flat)

    return HTMLResponse("<h2>Swiggy connected! You can close this tab.</h2>")
