#!/usr/bin/env python3
"""Phase 3: Gumroad account setup and product listing."""

import json
import re
from pathlib import Path

from lib.state import load, save, mark_phase_complete, is_phase_complete
from lib.manual import log_item, ManualInterventionRequired
from lib.browser import BrowserSession, human_delay, human_type
from lib.claude_client import generate

EMAIL = "jeffcrooks.ai@gmail.com"
GUMROAD_URL = "https://app.gumroad.com"


def generate_product_copy(niche: str, price: float, landing_url: str) -> dict:
    raw = generate(
        system="You write high-converting digital product descriptions for Gumroad.",
        prompt=f"""Write a Gumroad product listing for a {niche} prompt pack priced at ${price}.

Return JSON with these exact keys:
- name: product name (max 60 chars)
- tagline: one-line value proposition (max 100 chars)
- description: full description (200-300 words, NO income claims, NO "make $X/month")
- free_teaser: one sentence ending with: "Grab 10 free sample prompts here: {landing_url}"

The description should mention: 50 ready-to-use templates, 5 categories, follow-up sequences bonus, immediate download.""",
        max_tokens=800,
    )
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()
    return json.loads(raw)


def attempt_gumroad_signup(page) -> bool:
    page.goto("https://gumroad.com/signup", wait_until="networkidle")
    human_delay()

    if "dashboard" in page.url or "app.gumroad.com" in page.url:
        print("Already logged into Gumroad.")
        return True

    try:
        human_type(page, 'input[name="email"]', EMAIL)
        human_delay()

        password = "ProfitBot2026!Secure"
        if page.query_selector('input[name="password"]'):
            human_type(page, 'input[name="password"]', password)
            human_delay()

        page.click('button[type="submit"], input[type="submit"]')
        human_delay(3, 5)

        if page.query_selector("iframe[src*='recaptcha'], .h-captcha"):
            log_item(
                "Gumroad CAPTCHA",
                f"Complete the CAPTCHA at {page.url}, then re-run: python gumroad_setup.py",
                "gumroad_setup.py",
            )
            raise ManualInterventionRequired("CAPTCHA on Gumroad signup")

        if any(p in page.content().lower() for p in ["check your email", "verify", "confirmation"]):
            log_item(
                "Gumroad email verification required",
                "Check jeffcrooks.ai@gmail.com for a Gumroad verification email and click the link. Then re-run: python gumroad_setup.py",
                "gumroad_setup.py",
            )
            raise ManualInterventionRequired("Gumroad email verification required")

        env_path = Path(".env")
        existing = env_path.read_text() if env_path.exists() else ""
        if "GUMROAD_PASSWORD" not in existing:
            with open(env_path, "a") as f:
                f.write(f"\nGUMROAD_EMAIL={EMAIL}\nGUMROAD_PASSWORD={password}\n")

        return True
    except ManualInterventionRequired:
        raise
    except Exception as e:
        log_item(
            "Gumroad signup error",
            f"Manually create a Gumroad account at https://gumroad.com/signup with {EMAIL}. Then re-run: python gumroad_setup.py",
            "gumroad_setup.py",
        )
        raise ManualInterventionRequired(str(e))


def create_product_listing(page, copy: dict, price: float) -> str:
    """Attempts to create product listing. Returns product URL or raises ManualInterventionRequired."""
    try:
        page.goto(f"{GUMROAD_URL}/products/new", wait_until="networkidle")
        human_delay(2, 3)

        name_field = page.query_selector('input[name="name"], input[placeholder*="name"], input[placeholder*="Name"]')
        if name_field:
            name_field.click()
            human_delay(0.5, 1)
            name_field.fill(copy["name"])
            human_delay()

        price_field = page.query_selector('input[name="price"], input[placeholder*="price"], input[placeholder*="Price"]')
        if price_field:
            price_field.click()
            human_delay(0.3, 0.8)
            price_field.fill(str(int(price)))
            human_delay()

        pdf_path = Path("assets/full-prompt-pack.pdf")
        if pdf_path.exists():
            file_input = page.query_selector('input[type="file"]')
            if file_input:
                file_input.set_input_files(str(pdf_path))
                human_delay(3, 6)

        desc_field = page.query_selector('textarea[name="description"], [contenteditable="true"]')
        if desc_field:
            full_desc = copy["description"] + "\n\n" + copy["free_teaser"]
            desc_field.click()
            human_delay(0.3, 0.8)
            page.keyboard.type(full_desc, delay=10)
            human_delay()

        save_btn = page.query_selector('button:has-text("Save"), button:has-text("Publish"), button[type="submit"]')
        if save_btn:
            save_btn.click()
            human_delay(3, 5)

        current_url = page.url
        if "gumroad.com" in current_url and "/products/" in current_url:
            return current_url

        raise Exception("Could not determine product URL after creation")

    except ManualInterventionRequired:
        raise
    except Exception as e:
        log_item(
            "Gumroad product creation",
            (
                f"Manually create the product on Gumroad with:\n"
                f"  Name: {copy['name']}\n"
                f"  Price: ${price}\n"
                f"  Description: [see prompts/product_copy.json]\n"
                f"  File: assets/full-prompt-pack.pdf\n"
                f"  Discount codes: LAUNCH20 (20% off, 30 days), SUBSCRIBER30 (30% off)\n"
                f"  Save the product URL to state.json as gumroad_url.\n"
                f"  Then re-run: python gumroad_setup.py"
            ),
            "gumroad_setup.py",
        )
        raise ManualInterventionRequired(str(e))


def run_gumroad_setup() -> None:
    state = load()
    niche = state.get("niche") or "Recruiter Cold Outreach"
    price = float(state.get("price") or 15)
    landing_url = state.get("landing_url") or Path("landing_url.txt").read_text().strip()

    copy = generate_product_copy(niche, price, landing_url)
    Path("prompts/product_copy.json").write_text(json.dumps(copy, indent=2))

    with BrowserSession() as session:
        attempt_gumroad_signup(session.page)

        if not state.get("gumroad_url"):
            product_url = create_product_listing(session.page, copy, price)
            state["gumroad_url"] = product_url
            save(state)
            print(f"Product created: {product_url}")
        else:
            print(f"Product already exists: {state['gumroad_url']}")

    mark_phase_complete(3)
    print("\nPhase 3 complete.")


if __name__ == "__main__":
    if is_phase_complete(3):
        print("Phase 3 already complete.")
    else:
        run_gumroad_setup()
