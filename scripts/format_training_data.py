"""
Merges all synthetic_data/*.json files into a single train.jsonl
in the OpenAI function-calling messages format, ready for Unsloth SFTTrainer.

Output format per line:
{
  "messages": [
    {"role": "system",    "content": "<SYSTEM_PROMPT>"},
    {"role": "user",      "content": "<user message>"},
    {"role": "assistant", "content": null,
     "tool_calls": [{"type": "function", "function": {"name": "...", "arguments": "{...}"}}]}
  ]
}
"""
import json
import random
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent.parent
SYNTHETIC_DIR = ROOT / "synthetic_data"
OUTPUT_FILE = ROOT / "synthetic_data" / "train.jsonl"

SYSTEM_PROMPT = (
    "You are a grocery ordering assistant for a shared flat Telegram group connected to Swiggy Instamart. "
    "Always call the most specific tool available. "
    "IMPORTANT: If the message is a standalone greeting (hey, hi, hello, sup, hola, namaste, etc.) with NO grocery intent, "
    "always use `respond` — never infer a grocery action from a greeting, even if recent history mentions items. "
    "Use `respond` for: greetings, thanks, compliments, questions unrelated to groceries, or anything ambiguous. "
    "The users often write in Hindi or Hinglish — understand their intent and call the right tool regardless of language."
)

# All expected files — must match the tool_call names inside each file
EXPECTED_FILES = [
    "add_items.json",
    "remove_item.json",
    "show_cart.json",
    "clear_cart.json",
    "place_order.json",
    "schedule_order_once.json",
    "schedule_order_recurring.json",
    "cancel_schedule.json",
    "show_schedules.json",
    "search_item.json",
    "track_order.json",
    "show_orders.json",
    "show_go_to_items.json",
    "show_flat_info.json",
    "change_address.json",
    "show_help.json",
    "respond.json",
]


def validate_entry(entry: dict, filename: str) -> str | None:
    """Returns an error string if the entry is invalid, else None."""
    if "message" not in entry:
        return "missing 'message' field"
    if not isinstance(entry["message"], str) or not entry["message"].strip():
        return "'message' is empty or not a string"
    tc = entry.get("tool_call")
    if not tc:
        return "missing 'tool_call' field"
    if "name" not in tc:
        return "tool_call missing 'name'"
    if "arguments" not in tc:
        return "tool_call missing 'arguments'"
    if not isinstance(tc["arguments"], dict):
        return f"tool_call 'arguments' is not a dict (got {type(tc['arguments']).__name__})"

    # add_items specific: all quantities must be int
    if tc["name"] == "add_items":
        items = tc["arguments"].get("items", [])
        for item in items:
            qty = item.get("quantity", 1)
            if not isinstance(qty, int):
                return f"add_items item '{item.get('name')}' has non-integer quantity: {qty!r}"

    return None


def to_training_example(entry: dict) -> dict:
    tc = entry["tool_call"]
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": entry["message"].strip()},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"], ensure_ascii=False),
                        },
                    }
                ],
            },
        ]
    }


def main():
    all_examples = []
    stats = defaultdict(int)
    skipped = 0

    for filename in EXPECTED_FILES:
        path = SYNTHETIC_DIR / filename
        if not path.exists():
            print(f"  MISSING: {filename} — skipping")
            continue

        with open(path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"  JSON ERROR in {filename}: {e}")
                continue

        if not isinstance(data, list):
            print(f"  ERROR: {filename} is not a JSON array — skipping")
            continue

        file_ok = 0
        for i, entry in enumerate(data):
            err = validate_entry(entry, filename)
            if err:
                print(f"  SKIP [{filename} #{i+1}]: {err}")
                skipped += 1
                continue

            example = to_training_example(entry)
            all_examples.append(example)
            stats[entry["tool_call"]["name"]] += 1
            file_ok += 1

        print(f"  {filename}: {file_ok} examples loaded")

    # Shuffle so actions are mixed (important for training)
    random.seed(42)
    random.shuffle(all_examples)

    # Write JSONL
    with open(OUTPUT_FILE, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    # Summary
    print(f"\n{'='*50}")
    print(f"Total examples : {len(all_examples)}")
    print(f"Skipped        : {skipped}")
    print(f"Output         : {OUTPUT_FILE}")
    print(f"\nBreakdown by action:")
    for action, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {action:<30} {count}")


if __name__ == "__main__":
    main()
