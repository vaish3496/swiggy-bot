# Swiggy Flat Bot

Telegram-based shared grocery ordering bot for a flat, backed by Swiggy Instamart via MCP.

## Stack

- **Python 3.11** (conda env: `swiggy`)
- **FastAPI** — server + OAuth callback
- **Telegram** (`python-telegram-bot`) — group chat bot via polling
- **LangGraph** (`StateGraph`) — agent orchestration: router → cart/order/info/converse nodes
- **DeepSeek** (`deepseek-v4-pro`) — all LLM calls via direct `httpx` to `https://api.deepseek.com` (no OpenAI SDK)
- **Swiggy MCP** — `https://mcp.swiggy.com/im` (Instamart), OAuth 2.1 + PKCE
- **APScheduler** — one-time and recurring order scheduling (IST timezone)
- **Supabase (PostgreSQL)** via asyncpg — `DATABASE_URL` in `.env`

## Running

```bash
./start.sh
# or manually:
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Local dev uses `swiggy_flat_test_bot` (test token in `.env`)
- Prod uses the real bot token (in `.prod.env` and GitHub Secrets)
- **Never run both locally and EC2 at the same time** — Telegram only allows one polling connection per token

## Branch Strategy & CI/CD

- `main` — development branch, push freely
- `prod` — production branch, auto-deploys to EC2 on every push via GitHub Actions

**Deploy flow:**
```
push/merge to prod → GitHub Actions (.github/workflows/deploy.yml) → SSH into EC2 → git pull → pip install → systemctl restart swiggy-bot
```

Can also trigger manually: GitHub → Actions → Deploy to EC2 → Run workflow.

## Infrastructure

- **EC2**: `t3.micro`, Ubuntu 26.04, `ap-southeast-2` (Sydney), IP: `3.107.234.77`
- **SSH key**: `~/.ssh/swiggy-bot-key.pem`
- **App path on EC2**: `/home/ubuntu/swiggy-bot`
- **Python venv on EC2**: `/home/ubuntu/swiggy-bot/venv`
- **Systemd service**: `swiggy-bot` (auto-starts on boot, auto-restarts on crash)
- **Security group**: `sg-0601066a3084887de` (`launch-wizard-1`) — ports 22, 80, 443 open

### Useful EC2 commands
```bash
# SSH in
ssh -i ~/.ssh/swiggy-bot-key.pem ubuntu@3.107.234.77

# View live logs
sudo journalctl -u swiggy-bot -f

# Restart service
sudo systemctl restart swiggy-bot

# Check status
sudo systemctl status swiggy-bot
```

## File Map

```
app/
├── main.py              FastAPI app, startup/shutdown, mounts routes
├── config.py            All env var loading
├── swiggy/
│   └── client.py        All 12 MCP tool wrappers (call_tool via httpx)
├── db/
│   ├── connection.py    asyncpg pool, init_db (CREATE TABLE IF NOT EXISTS)
│   ├── flats.py         Flat CRUD
│   ├── cart.py          Cart items + item preferences
│   ├── messages.py      Chat history (LLM context)
│   ├── schedules.py     Scheduled order CRUD
│   └── __init__.py      Re-exports all db helpers
├── agent/
│   ├── graph.py         LangGraph StateGraph definition
│   ├── state.py         BotState TypedDict
│   ├── tools.py         SYSTEM_PROMPT (JSON schema for router)
│   ├── intent.py        identify_item_to_remove, _conv_log (DeepSeek)
│   ├── actions.py       search_and_add_items, get_cart_summary, _format_bill
│   └── nodes/
│       ├── router.py    router_node — DeepSeek JSON mode intent parsing
│       ├── cart.py      cart_node — add/remove/show/clear cart
│       ├── order.py     order_node — place/schedule/cancel/show schedules
│       ├── info.py      info_node — search, track, orders, go-to, flat info, address, help
│       └── converse.py  converse_node — small talk replies
├── bot/
│   ├── telegram.py      send_message, start_polling, stop, application
│   ├── oauth.py         PKCE flow, /auth/callback FastAPI route
│   ├── address.py       Address selection flow + pending_address_selection state
│   └── handlers.py      _handle_message, _handle_bot_added, graph invocation
└── scheduler/
    └── jobs.py          AsyncIOScheduler, execute_order, schedule_once/recurring, reload_schedules
.github/
└── workflows/
    └── deploy.yml       GitHub Actions — deploy to EC2 on push to prod
swiggy-bot.service       systemd unit file (installed at /etc/systemd/system/)
```

## Database Schema (Supabase/PostgreSQL)

- `flats` — flat_id (Telegram chat_id), owner_id, swiggy_access_token, swiggy_token_expires_at, default_address_id, default_address_label, created_at
- `cart_items` — flat_id, spin_id, product_name, quantity, added_by, added_at (tracking only — Swiggy is source of truth)
- `item_preferences` — flat_id, spin_id, product_name, order_count, last_ordered_at (used to auto-pick preferred variants)
- `scheduled_orders` — flat_id, job_id, scheduled_by, run_at, is_recurring, cron_expr, status, created_at
- `chat_messages` — flat_id, role, content, created_at (last 100 loaded as LLM history)

## Environment Variables

| File | Purpose | Git |
|------|---------|-----|
| `.env` | Local dev (test bot token) | Ignored |
| `.prod.env` | Prod values reference (local only) | Ignored |
| `.env.example` | Template for new contributors | Committed |

GitHub Secrets mirror `.prod.env` values and are injected into EC2 `.env` on every deploy.

```
TELEGRAM_BOT_TOKEN=...
DEEPSEEK_API_KEY=...
DEEPSEEK_MODEL=deepseek-v4-pro
GEMINI_API_KEY=...
GEMINI_MODEL=gemma-4-31b-it
SWIGGY_MCP_URL=https://mcp.swiggy.com
APP_BASE_URL=http://3.107.234.77
OAUTH_REDIRECT_BASE=http://localhost:8000   # local | http://3.107.234.77 on EC2
SECRET_KEY=...
DATABASE_URL=postgresql://...
SUPABASE_URL=https://...supabase.co
SUPABASE_KEY=...
DATABASE_PASSWORD=...
```

## Key Behaviours

### Onboarding flow
1. Bot added to Telegram group → auto-creates flat entry, prompts `connect swiggy`
2. Owner sends `connect swiggy` → OAuth PKCE flow → token saved to Supabase
3. After auth: bot prompts address selection (numbered list), owner picks one
4. User can later say `change address` to re-run address selection at any time

### LangGraph agent flow
```
[router_node] → conditional edge → [cart_node | order_node | info_node | converse_node] → END
```
- **router_node**: DeepSeek JSON mode parses intent from user message + history → sets `action` + `intent` on state
- **cart_node**: handles `add_items`, `remove_item`, `show_cart`, `clear_cart`
- **order_node**: handles `place_now`, `schedule_once`, `schedule_recurring`, `cancel_schedule`, `show_schedules`
- **info_node**: handles `search_item`, `track_order`, `show_orders`, `show_go_to_items`, `show_flat_info`, `change_address`, `help`
- **converse_node**: handles `respond` (small talk)

### Intent parsing — DeepSeek JSON mode
- `router_node` sends SYSTEM_PROMPT + history + user message to DeepSeek with `response_format: json_object`
- No tool calling — model must output a strict JSON action object
- Greetings ("hey", "hi", "hello") always route to `respond` regardless of prior conversation history (rule 7 in SYSTEM_PROMPT)
- 429 → "Sorry, I'm a bit busy right now. Please try again in a moment!"
- 402 → "Sorry, the bot is out of credits. Please top up DeepSeek."
- 5xx → "Sorry, I couldn't process that. Please try again."
- All DeepSeek calls logged to `conversation.log` in project root (gitignored)

### Swiggy MCP
- Endpoint: `https://mcp.swiggy.com/im`
- **Required header**: `Accept: application/json, text/event-stream` (missing this returns -32000 error)
- All responses: prefer `structuredContent` over `content[0]["text"]`
- `update_cart` **replaces** the entire cart — must send all items every time
- `get_cart` returns `isError: true` if cart is empty/expired — caught, returns `{"items": []}`
- Product fields: `displayName`, `variations`, `inStock` (bool), `isAvail` (bool)
- Variation fields: `spinId`, `skuId`, `quantityDescription`, `price` {mrp, offerPrice}, `isInStockAndAvailable` (bool)
- Cart item fields: `spinId`, `itemName`, `quantity`, `discountedFinalPrice`

### Available MCP tools (12 implemented)
| Category | Tools |
|----------|-------|
| Discover | `get_addresses`, `create_address`, `delete_address`, `search_products`, `your_go_to_items` |
| Cart     | `get_cart`, `update_cart`, `clear_cart` |
| Order    | `checkout` |
| Track    | `get_orders`, `get_order_details`, `track_order` |

### Out-of-stock handling
- Variants with `isInStockAndAvailable: false` are filtered out before LLM variant picking
- If all variants are OOS: `❌ *{name}* is out of stock at your location.`
- In search results (`search_item`): OOS variants skipped from numbered list; fully OOS products shown as `❌ {name} — out of stock` with no number (not addable)

### Cart source of truth
Swiggy is authoritative for cart state. DB `cart_items` stores only `added_by` metadata and preferences.
- **Adding**: fetch current Swiggy cart → merge new items → `update_cart` with full merged list
- **Removing**: fetch Swiggy cart → pass items + user request to DeepSeek (`identify_item_to_remove`) → get spinId → `update_cart` with remaining items
- **Showing**: fetch from Swiggy, enrich with `added_by` from DB

### Item preferences
When adding items, search results are checked against `item_preferences`.
The variant with the highest `order_count` for this flat is auto-preferred by the LLM context.
Count is incremented each time an item is successfully added to cart.

### Track order
If no `order_id` is provided, `get_orders` is called first to fetch the latest order ID,
then `track_order` is called with that ID.

### Search results + follow-up adds
When `search_item` is called, results are shown as a numbered list. An `ITEMS_META::{}::END_ITEMS_META` block is saved to `chat_messages` (hidden from Telegram) so the router can extract `spinId`/`skuId` for follow-up "add option 2" messages. The `db_saved: True` flag on state tells `handlers.py` to skip re-saving the message.

## Useful Debug Queries

```bash
# View live prod logs
ssh -i ~/.ssh/swiggy-bot-key.pem ubuntu@3.107.234.77 "sudo journalctl -u swiggy-bot -f"

# Check conversation log (local)
tail -50 /Users/vaishnav/Documents/swiggy-mcp/conversation.log
```

```python
# Query Supabase via asyncpg (prod):
/opt/anaconda3/envs/swiggy/bin/python3 -c "
import asyncio, asyncpg, os
from dotenv import load_dotenv
load_dotenv('.prod.env')
async def main():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    rows = await conn.fetch('SELECT flat_id, owner_id, swiggy_token_expires_at, default_address_label FROM flats')
    for r in rows: print(dict(r))
    await conn.close()
asyncio.run(main())
"
```

## AWS / GitHub Config

- **AWS region**: `ap-southeast-2` (Sydney)
- **AWS account ID**: `246100042194`
- **GitHub repo**: `vaish3496/swiggy-bot` (public)
- **GitHub Secrets**: 15 secrets set — EC2_HOST, EC2_SSH_KEY + all env vars
- **Security group**: `sg-0601066a3084887de` — port 22 open to `0.0.0.0/0` (required for GitHub Actions SSH deploy)
