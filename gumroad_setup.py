#!/usr/bin/env python3
"""Phase 3: Gumroad product listing via API."""

import json
import os
import re
from pathlib import Path

import requests

from lib.claude_client import generate, _load_shell_env_file
from lib.manual import log_item, ManualInterventionRequired
from lib.state import load, save, mark_phase_complete, is_phase_complete

_load_shell_env_file(Path.home() / ".env.secrets")

GUMROAD_TOKEN = os.environ.get("GUMROAD_ACCESS_TOKEN", "")
GUMROAD_BASE = "https://api.gumroad.com/v2"
PRODUCT_COPY_PATH = Path("prompts/product_copy.json")


def gumroad_headers() -> dict:
    return {"Authorization": f"Bearer {GUMROAD_TOKEN}"}


def verify_token() -> None:
    if not GUMROAD_TOKEN:
        log_item(
            "Gumroad API token required",
            (
                "1. Sign up / log in at https://gumroad.com with jeffcrooks.ai@gmail.com\n"
                "2. Go to https://app.gumroad.com/settings/advanced (scroll to 'Application')\n"
                "3. Click 'Generate access token'\n"
                "4. Add to ~/.env.secrets: export GUMROAD_ACCESS_TOKEN=\"your_token_here\"\n"
                "5. Re-run: python3 gumroad_setup.py"
            ),
            "gumroad_setup.py",
        )
        raise ManualInterventionRequired("GUMROAD_ACCESS_TOKEN not set")

    r = requests.get(f"{GUMROAD_BASE}/user", headers=gumroad_headers())
    if r.status_code != 200:
        raise RuntimeError(f"Gumroad token invalid: {r.status_code} {r.text[:200]}")
    user = r.json().get("user", {})
    print(f"Gumroad account: {user.get('name')} ({user.get('email')})")


def load_or_generate_copy(niche: str, price: float, landing_url: str) -> dict:
    if PRODUCT_COPY_PATH.exists():
        copy = json.loads(PRODUCT_COPY_PATH.read_text())
        print("Using existing product copy from prompts/product_copy.json")
        return copy

    print("Generating product copy...")
    raw = generate(
        system="You write high-converting digital product descriptions for Gumroad.",
        prompt=f"""Write a Gumroad product listing for a {niche} prompt pack priced at ${price}.

Return JSON with these exact keys:
- name: product name (max 60 chars)
- tagline: one-line value proposition (max 100 chars)
- description: full description (250-350 words, NO income claims, plain text not markdown)
- free_teaser: one sentence ending with: "Grab 10 free sample prompts here: {landing_url}"

Cover: who it's for, the pain (generic outreach, low reply rates), what's inside (50 prompts across 5 categories, bonus follow-up sequences), immediate PDF download.""",
        max_tokens=900,
    )
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()
    copy = json.loads(raw)
    PRODUCT_COPY_PATH.parent.mkdir(exist_ok=True)
    PRODUCT_COPY_PATH.write_text(json.dumps(copy, indent=2))
    return copy


def ensure_product(copy: dict, price: float) -> str:
    """Creates the Gumroad product if it doesn't exist. Returns product permalink URL."""
    # Check for existing products
    r = requests.get(f"{GUMROAD_BASE}/products", headers=gumroad_headers())
    r.raise_for_status()
    products = r.json().get("products", [])
    for p in products:
        if p["name"] == copy["name"]:
            url = f"https://app.gumroad.com/l/{p['short_url']}" if p.get("short_url") else p.get("url", "")
            print(f"Product already exists: {url}")
            return url

    # Create the product
    description = copy["description"] + "\n\n" + copy["free_teaser"]
    r = requests.post(
        f"{GUMROAD_BASE}/products",
        headers=gumroad_headers(),
        data={
            "name": copy["name"],
            "price": int(price * 100),  # cents
            "description": description,
        },
    )
    r.raise_for_status()
    product = r.json()["product"]
    product_id = product["id"]
    print(f"Product created: id={product_id} name={product['name']}")

    # Upload the PDF
    pdf_path = Path("assets/full-prompt-pack.pdf")
    if pdf_path.exists():
        with open(pdf_path, "rb") as f:
            upload_r = requests.put(
                f"{GUMROAD_BASE}/products/{product_id}/files",
                headers=gumroad_headers(),
                files={"file": (pdf_path.name, f, "application/pdf")},
            )
        if upload_r.status_code in (200, 201):
            print("PDF uploaded successfully")
        else:
            print(f"PDF upload warning: {upload_r.status_code} {upload_r.text[:200]}")
    else:
        print("Warning: assets/full-prompt-pack.pdf not found, skipping upload")

    # Create discount codes
    for code, percent in [("LAUNCH20", 20), ("SUBSCRIBER30", 30)]:
        disc_r = requests.post(
            f"{GUMROAD_BASE}/products/{product_id}/offer_codes",
            headers=gumroad_headers(),
            data={"name": code, "amount_off": percent, "offer_type": "percent"},
        )
        if disc_r.status_code in (200, 201):
            print(f"Discount code created: {code} ({percent}% off)")
        else:
            print(f"Discount code warning ({code}): {disc_r.status_code} {disc_r.text[:100]}")

    url = product.get("short_url") or product.get("url") or f"https://app.gumroad.com/l/{product_id}"
    return url


def run_gumroad_setup() -> None:
    verify_token()

    state = load()
    niche = state.get("niche") or "Recruiter Cold Outreach"
    price = float(state.get("price") or 15)
    landing_url = state.get("landing_url") or "https://jeff-63.kit.com/freeprompt"

    copy = load_or_generate_copy(niche, price, landing_url)

    if state.get("gumroad_url"):
        print(f"Product already recorded: {state['gumroad_url']}")
    else:
        product_url = ensure_product(copy, price)
        state["gumroad_url"] = product_url
        save(state)
        print(f"Product URL saved: {product_url}")

    mark_phase_complete(3)
    print("\nPhase 3 complete.")


if __name__ == "__main__":
    if is_phase_complete(3):
        print("Phase 3 already complete.")
    else:
        run_gumroad_setup()
