"""
Wardrobe Cataloging Script
Usage: python3 catalog.py <path_to_garment_photo> <path_to_label_photo> [item_name]
"""

import anthropic
import base64
import json
import os
import sys
import uuid
from pathlib import Path
import qrcode


# --- Config ---
DB_FILE = "items.json"
QR_DIR = "qr_codes"
BASE_URL = "https://wardrobe-catalog-production.up.railway.app/item"


EXTRACTION_PROMPT = """
You are a clothing care label parser. Analyze the care label image and extract information strictly as JSON.

Return ONLY a valid JSON object with this exact schema, no other text:

{
  "brand": "brand name or null",
  "item_type": "e.g. Jacket, Sweater, T-Shirt",
  "color": "primary color",
  "material": {
    "shell": "material or null",
    "lining": "material or null",
    "fill": "material or null",
    "primary": "main material if no shell/lining distinction"
  },
  "care": {
    "wash": "exact wash instruction",
    "water_temp": "cold / warm / hot / do not wash",
    "bleach": false,
    "fabric_softener": false,
    "tumble_dry": true,
    "dry_temp": "low / medium / high / do not tumble dry",
    "hang_dry": false,
    "iron": false,
    "dry_clean": false,
    "special_instructions": ["list of any special notes"]
  },
  "alert_level": "safe | caution | danger",
  "alert_reason": "one sentence explaining alert level"
}

Alert levels:
- safe: standard machine washable items
- caution: machine washable but with specific requirements
- danger: dry clean only, hand wash only, or will be damaged by normal washing

Be precise. If something is not visible, use null.
"""


def encode_image(image_path: str) -> tuple[str, str]:
    """Encode image to base64 and detect media type."""
    path = Path(image_path)
    suffix = path.suffix.lower()
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    media_type = media_type_map.get(suffix, "image/jpeg")
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8"), media_type


def extract_care_data(client: anthropic.Anthropic, label_path: str, garment_path: str) -> dict:
    """Send both images to Claude Vision and extract structured care data."""
    label_data, label_type = encode_image(label_path)
    garment_data, garment_type = encode_image(garment_path)

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Here is the garment:"
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": garment_type,
                            "data": garment_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": "Here is its care label:"
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": label_type,
                            "data": label_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": EXTRACTION_PROMPT
                    }
                ],
            }
        ],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw.strip())


def load_db() -> dict:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}


def save_db(db: dict):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)


def generate_qr(item_id: str) -> str:
    """Generate QR code PNG and return file path."""
    os.makedirs(QR_DIR, exist_ok=True)
    url = f"{BASE_URL}/{item_id}"
    img = qrcode.make(url)
    output_path = f"{QR_DIR}/{item_id}.png"
    img.save(output_path)
    return output_path


def print_care_card(item: dict):
    """Print a human-readable care summary."""
    care = item["care"]
    alert = item["alert_level"].upper()
    icons = {"SAFE": "✅", "CAUTION": "⚠️", "DANGER": "🚨"}

    print("\n" + "=" * 50)
    print(f"{icons.get(alert, '❓')}  {alert}: {item.get('alert_reason', '')}")
    print("=" * 50)
    print(f"Item:   {item.get('item_type')} ({item.get('color')})")
    print(f"Brand:  {item.get('brand') or 'Unknown'}")
    print("-" * 50)
    print("CARE INSTRUCTIONS")
    print(f"  Wash:       {care.get('wash', 'N/A')}")
    print(f"  Temp:       {care.get('water_temp', 'N/A')}")
    print(f"  Tumble dry: {'Yes — ' + care.get('dry_temp', '') if care.get('tumble_dry') else 'No'}")
    print(f"  Bleach:     {'Yes' if care.get('bleach') else 'No'}")
    print(f"  Iron:       {'Yes' if care.get('iron') else 'No'}")
    print(f"  Dry clean:  {'Yes' if care.get('dry_clean') else 'No'}")
    if care.get("special_instructions"):
        print("  Notes:")
        for note in care["special_instructions"]:
            print(f"    • {note}")
    print("=" * 50)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 catalog.py <garment_photo> <label_photo> [item_name]")
        sys.exit(1)

    garment_path = sys.argv[1]
    label_path = sys.argv[2]
    item_name = sys.argv[3] if len(sys.argv) > 3 else None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        print("Run: export ANTHROPIC_API_KEY=your_key_here")
        sys.exit(1)

    print("Analyzing care label...")
    client = anthropic.Anthropic(api_key=api_key)
    care_data = extract_care_data(client, label_path, garment_path)

    # Add metadata
    item_id = f"ITEM{str(uuid.uuid4())[:6].upper()}"
    if item_name:
        care_data["name"] = item_name
    care_data["item_id"] = item_id
    care_data["garment_photo"] = garment_path
    care_data["label_photo"] = label_path

    # Save to Supabase
    from db import save_item
    save_item(item_id, care_data)

    # Generate QR code
    qr_path = generate_qr(item_id)

    # Print summary
    print_care_card(care_data)
    print(f"\nItem ID:  {item_id}")
    print(f"QR code:  {qr_path}")
    print(f"Saved to: Supabase")


if __name__ == "__main__":
    main()
