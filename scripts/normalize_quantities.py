"""
Normalize quantity fields in add_items training data.

Rule:
- If quantity is an integer → keep as-is (it's a count)
- If quantity is a weight/volume string (e.g. "500 g", "1 kg", "2 litre") →
  move it into the item name, set quantity to 1
"""
import json
import re
from pathlib import Path

SYNTHETIC_DIR = Path(__file__).parent.parent / "synthetic_data"


def normalize_quantity(name: str, quantity) -> tuple[str, int]:
    """
    Returns (normalized_name, normalized_quantity).
    If quantity is already an int, return as-is.
    If quantity is a weight/volume string, append to name and set qty=1.
    """
    if isinstance(quantity, int):
        return name, quantity

    if not isinstance(quantity, str):
        return name, 1

    q = quantity.strip().lower()

    # Match patterns like: "500 g", "1 kg", "2 litre", "1.5 l", "0.5 kg", "250ml"
    weight_pattern = re.compile(
        r"^(\d+(?:\.\d+)?)\s*(kg|g|gm|gram|grams|litre|litres|liter|liters|l|ml)$"
    )
    match = weight_pattern.match(q)
    if match:
        amount = match.group(1)
        unit = match.group(2)

        # Normalize unit labels
        unit_map = {
            "g": "g", "gm": "g", "gram": "g", "grams": "g",
            "kg": "kg",
            "l": "L", "litre": "L", "litres": "L", "liter": "L", "liters": "L",
            "ml": "ml",
        }
        normalized_unit = unit_map.get(unit, unit)

        # Format amount: drop trailing ".0"
        if amount.endswith(".0"):
            amount = amount[:-2]

        new_name = f"{name} {amount}{normalized_unit}"
        return new_name, 1

    # Unrecognized string quantity — keep name, default qty to 1
    print(f"  WARNING: unrecognized quantity string '{quantity}' for item '{name}' — defaulting to 1")
    return name, 1


def normalize_add_items_file(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)

    fixed = 0
    for entry in data:
        tool = entry.get("tool_call", {})
        if tool.get("name") != "add_items":
            continue

        items = tool.get("arguments", {}).get("items", [])
        for item in items:
            original_name = item.get("name", "")
            original_qty = item.get("quantity", 1)

            new_name, new_qty = normalize_quantity(original_name, original_qty)

            if new_name != original_name or new_qty != original_qty:
                print(f"  FIX: '{original_name}' qty={original_qty!r} → name='{new_name}' qty={new_qty}")
                item["name"] = new_name
                item["quantity"] = new_qty
                fixed += 1

    print(f"  {fixed} item(s) fixed in {path.name}")
    return data


def main():
    target = SYNTHETIC_DIR / "add_items.json"
    if not target.exists():
        print(f"File not found: {target}")
        return

    print(f"Normalizing {target.name}...")
    normalized = normalize_add_items_file(target)

    with open(target, "w") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Saved to {target}")


if __name__ == "__main__":
    main()
