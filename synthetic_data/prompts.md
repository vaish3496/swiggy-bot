---                                                                                                                         
  Prompt 1 — add_items                                                                                                        
                                                                                                                              
  You are generating training data for a Telegram grocery bot that serves a shared flat in India.                             
  The bot understands English, Hindi, and Hinglish.

  Generate 40 diverse user messages that should trigger the action: **add_items**
  This action is for adding one or more grocery items to a shared cart.

  Rules:
  - Vary the phrasing heavily — no two messages should sound alike
  - Mix English, Hindi, and Hinglish freely
  - Include realistic flat scenarios (flatmates messaging in a group)
  - Some messages should have multiple items, some just one
  - Vary quantities (1, 2, half kg, etc.)
  - Include casual phrasing: "daaldo", "daal do", "daalo", "chahiye", "le aao", "get me", "add", "put"
  - Include natural typos and casual speech
  - Items: milk, eggs, bread, chips, coke, maggi, atta, rice, dal, butter, curd, biscuits, namkeen, etc.

  For each message, also provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "bhai 2 ande aur ek doodh daal do cart mein",
      "tool_call": {
        "name": "add_items",
        "arguments": {"items": [{"name": "eggs", "quantity": 2}, {"name": "milk", "quantity": 1}]}
      }
    }
  ]

  ---
  Prompt 2 — remove_item

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 30 diverse user messages that should trigger the action: **remove_item**
  This action is for removing a specific item from the shared cart.

  Rules:
  - Vary the phrasing heavily — no two messages should sound alike
  - Mix English, Hindi, and Hinglish
  - Include casual phrasing: "hata do", "remove", "nikaal do", "don't want", "cancel karo", "drop"
  - Each message should clearly mention one item name
  - Include realistic flat scenarios

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "bhai milk hata do cart se",
      "tool_call": {
        "name": "remove_item",
        "arguments": {"name": "milk"}
      }
    }
  ]

  ---
  Prompt 3 — show_cart

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 30 diverse user messages that should trigger the action: **show_cart**
  This action shows the current cart contents, bill breakdown, delivery charges, and total.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "show cart", "cart dikhao", "kya kya hai cart mein", "total kitna", "kitna paisa lagega",
    "bill kya hai", "delivery charges", "how much will it cost", "what's in the cart", "cart check karo"
  - Some messages ask specifically about price/total, some about contents

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "cart dikhao bhai kitna total hua",
      "tool_call": {
        "name": "show_cart",
        "arguments": {}
      }
    }
  ]

  ---
  Prompt 4 — clear_cart

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 25 diverse user messages that should trigger the action: **clear_cart**
  This action removes ALL items from the cart and starts fresh.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "clear cart", "cart khali karo", "sab hata do", "empty the cart", "start fresh",
    "cart reset karo", "remove everything", "saari cheezein hata do"
  - These should be clearly about wiping the whole cart, not just one item

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "yaar cart khali kar do sab kuch",
      "tool_call": {
        "name": "clear_cart",
        "arguments": {}
      }
    }
  ]

  ---
  Prompt 5 — place_order

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 30 diverse user messages that should trigger the action: **place_order**
  This action places the current cart as an order RIGHT NOW — no specific time is mentioned.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "order karo", "place order", "order now", "abhi order karo", "le lo", "order dedo",
    "bhejo", "checkout", "order place karo"
  - IMPORTANT: These messages must NOT mention any specific time (no "9pm", "tonight", "kal")
  - If a time is mentioned, that would be schedule_order_once, not this action

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "bhai abhi order kar do",
      "tool_call": {
        "name": "place_order",
        "arguments": {}
      }
    }
  ]

  ---
  Prompt 6 — schedule_order_once

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 35 diverse user messages that should trigger the action: **schedule_order_once**
  This action schedules the cart to be ordered at a specific future time (one-time only).

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - ALWAYS include a specific time in the message (9pm, 10:30am, raat 9 baje, kal subah 8 baje, etc.)
  - Include "today" and "tomorrow" scenarios
  - Include: "schedule for", "order at", "raat ko 9 baje order karna", "kal subah order karo",
    "set order for 10pm", "9 baje karna order"
  - The arguments must include "time" in HH:MM 24-hour format and "date" as "today" or "tomorrow"

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "bhai aaj raat 9 baje order kar dena",
      "tool_call": {
        "name": "schedule_order_once",
        "arguments": {"time": "21:00", "date": "today"}
      }
    },
    {
      "message": "kal subah 8:30 baje order schedule karo",
      "tool_call": {
        "name": "schedule_order_once",
        "arguments": {"time": "08:30", "date": "tomorrow"}
      }
    }
  ]

  ---
  Prompt 7 — schedule_order_recurring

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 30 diverse user messages that should trigger the action: **schedule_order_recurring**
  This action sets up a REPEATING order (every day, every week, etc.).

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "roz", "har din", "daily", "every day", "every morning", "every night",
    "every Monday", "weekly", "roz raat ko", "roz subah"
  - The cron expression must match the schedule (e.g., "0 22 * * *" = every day at 10pm)
  - Include a human-readable description field

  Common cron patterns:
  - Every day at 9pm → "0 21 * * *"
  - Every day at 8am → "0 8 * * *"
  - Every Monday at 10am → "0 10 * * 1"
  - Every day at 10:30pm → "30 22 * * *"

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "roz raat 10 baje order set kar do",
      "tool_call": {
        "name": "schedule_order_recurring",
        "arguments": {"cron": "0 22 * * *", "description": "every day at 10pm"}
      }
    }
  ]

  ---
  Prompt 8 — cancel_schedule

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 25 diverse user messages that should trigger the action: **cancel_schedule**
  This action cancels the most recent pending scheduled order.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "cancel schedule", "scheduled order cancel karo", "mat karna order",
    "schedule hatao", "scheduled order rok do", "cancel kar do woh order"
  - These should be about cancelling a previously scheduled order, not a live/placed order

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "yaar woh scheduled order cancel kar do",
      "tool_call": {
        "name": "cancel_schedule",
        "arguments": {}
      }
    }
  ]

  ---
  Prompt 9 — show_schedules

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 25 diverse user messages that should trigger the action: **show_schedules**
  This action shows all pending scheduled orders (one-time and recurring).

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "show schedules", "kaunse orders scheduled hain", "scheduled orders dikhao",
    "kab ka order set hai", "pending schedules", "recurring orders dikhao"

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "bhai kaunse orders scheduled hain abhi",
      "tool_call": {
        "name": "show_schedules",
        "arguments": {}
      }
    }
  ]

  ---
  Prompt 10 — search_item

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 35 diverse user messages that should trigger the action: **search_item**
  This action searches for a product — used for checking price, availability, or browsing variants.
  It is NOT for adding to cart — just browsing/checking.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "what's the price of X", "X kitne ka hai", "do you have X", "X available hai",
    "show me options for X", "X ka rate kya hai", "kaunsa brand acha hai for X",
    "how much is X", "X milega kya", "X ke variants dikhao"
  - The query argument should be a clean product search string

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "bhai amul butter kitne ka hai",
      "tool_call": {
        "name": "search_item",
        "arguments": {"query": "amul butter"}
      }
    },
    {
      "message": "kaunse brand ka atta acha rahega",
      "tool_call": {
        "name": "search_item",
        "arguments": {"query": "atta"}
      }
    }
  ]

  ---
  Prompt 11 — track_order

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 25 diverse user messages that should trigger the action: **track_order**
  This action tracks the delivery status of the most recently placed order.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "track order", "order kahan hai", "delivery kab aayegi", "order status",
    "kitni der mein aayega", "where is my order", "kya hua order ka", "order track karo"
  - Most messages won't specify an order_id — leave it as null/omit it
  - Arguments should be {} (empty) for most cases since order_id is optional

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "bhai order kahan tak pahuncha",
      "tool_call": {
        "name": "track_order",
        "arguments": {}
      }
    }
  ]

  ---
  Prompt 12 — show_orders

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 25 diverse user messages that should trigger the action: **show_orders**
  This action shows past order history from Swiggy.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "show orders", "past orders", "order history", "pichle orders dikhao",
    "what did we order last time", "purane orders", "kya kya order kiya tha"
  - These are about PAST orders, not the current cart or active delivery

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "pichli baar kya kya order kiya tha dikhao",
      "tool_call": {
        "name": "show_orders",
        "arguments": {}
      }
    }
  ]

  ---
  Prompt 13 — show_go_to_items

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 25 diverse user messages that should trigger the action: **show_go_to_items**
  This action shows the user's frequently ordered / go-to items from Swiggy.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "show my go-to items", "what do I usually order", "suggest items",
    "frequently ordered items", "mere favourite items dikhao", "what should we get",
    "jo hamesha order karte hain woh dikhao", "recommendations do"

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "bhai jo items hamesha order karte hain woh dikhao",
      "tool_call": {
        "name": "show_go_to_items",
        "arguments": {}
      }
    }
  ]

  ---
  Prompt 14 — show_flat_info

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 20 diverse user messages that should trigger the action: **show_flat_info**
  This action shows the flat's current delivery address and Swiggy connection status.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "show flat info", "kaunsa address set hai", "delivery address kya hai",
    "swiggy connected hai", "flat details dikhao", "current address batao"

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "bhai abhi kaunsa address set hai delivery ke liye",
      "tool_call": {
        "name": "show_flat_info",
        "arguments": {}
      }
    }
  ]

  ---
  Prompt 15 — change_address

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 20 diverse user messages that should trigger the action: **change_address**
  This action changes the flat's delivery address to a different saved Swiggy address.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "change address", "address badlo", "delivery address update karo",
    "naya address set karo", "address change karna hai", "different address pe deliver karo"

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "bhai address badal do delivery ka",
      "tool_call": {
        "name": "change_address",
        "arguments": {}
      }
    }
  ]

  ---
  Prompt 16 — show_help

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 20 diverse user messages that should trigger the action: **show_help**
  This action shows available commands and usage instructions for the bot.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include: "help", "what can you do", "commands", "how to use", "kya kya kar sakte ho",
    "bot kaise use karte hain", "instructions do", "guide me", "features kya hain"

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "bhai yeh bot kya kya kar sakta hai",
      "tool_call": {
        "name": "show_help",
        "arguments": {}
      }
    }
  ]

  ---
  Prompt 17 — respond (most important — hardest to get right)

  You are generating training data for a Telegram grocery bot that serves a shared flat in India.
  The bot understands English, Hindi, and Hinglish.

  Generate 40 diverse user messages that should trigger the action: **respond**
  This action is for messages that are NOT grocery-related — the bot just sends a conversational reply.

  Rules:
  - Vary the phrasing heavily
  - Mix English, Hindi, and Hinglish
  - Include ONLY: greetings, thanks, compliments, random questions, off-topic chat, gibberish
  - Examples: "hey", "thanks bot", "tu bahut acha hai", "what is 2+2", "aaj mausam kaisa hai",
    "nice", "ok done", "haha", "lol", "bhai kya haal hai", "good morning", "namaste",
    "shukriya", "you're the best", "random gibberish like aksdjf"
  - IMPORTANT: Do NOT include any grocery intent in these messages
  - The "message" field in arguments should be a short, friendly bot reply

  For each message, provide the correct tool call output as JSON.

  Return ONLY a JSON array like this, no explanation:
  [
    {
      "message": "haha nice bot hai yaar",
      "tool_call": {
        "name": "respond",
        "arguments": {"message": "Haha thanks! Let me know if you need anything from Instamart 😄"}
      }
    }
  ]

  ---
  After Running All 17 Prompts

  Save each ChatGPT output as a separate JSON file (add_items.json, remove_item.json, etc.), then I'll write a formatter
  script to:
  - Merge all files
  - Convert to JSONL training format with the system prompt
  - Validate structure and remove bad entries

  Just paste the outputs into files and share them (or describe any issues) and we'll proceed from there.

