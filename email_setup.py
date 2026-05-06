#!/usr/bin/env python3
"""Phase 2: ConvertKit account setup and email funnel."""

import re
import time
from pathlib import Path

from lib.state import load, save, mark_phase_complete, is_phase_complete
from lib.manual import log_item, ManualInterventionRequired
from lib.browser import BrowserSession, human_delay, human_type

EMAIL = "jeffcrooks.ai@gmail.com"
LANDING_URL_FILE = Path("landing_url.txt")
CONVERTKIT_URL = "https://app.convertkit.com"

WELCOME_EMAIL_SUBJECT = "Your free prompts are here 🎯"
SEQUENCE_EMAILS = [
    {
        "day": 1,
        "subject": "One quick tip to double your reply rate",
        "body": (
            "Hey {{subscriber.first_name | default: 'there'}},\n\n"
            "Yesterday you grabbed the free prompt pack. Here's a tip that gets 2-3x more replies:\n\n"
            "Always personalize the first line. Reference something specific about their company or recent news.\n\n"
            "The full pack (50 prompts + follow-up sequences) has a whole category dedicated to this: "
            "[grab it here — link to product].\n\nTalk soon,"
        ),
    },
    {
        "day": 3,
        "subject": "How Sarah booked 12 interviews in one week",
        "body": (
            "Hey {{subscriber.first_name | default: 'there'}},\n\n"
            "Sarah is a recruiter who was struggling with response rates under 5%.\n\n"
            "She started using structured prompt templates and hit 18% reply rate in her first week.\n\n"
            "The difference? Consistency + personalization at scale. "
            "The full prompt pack gives you the exact framework: [product link].\n\nBest,"
        ),
    },
    {
        "day": 5,
        "subject": "Still sending emails that get ignored?",
        "body": (
            "Hey {{subscriber.first_name | default: 'there'}},\n\n"
            "The #1 reason cold emails fail: generic openers.\n\n"
            "The full 50-prompt pack fixes that. Use code LAUNCH20 for 20% off: [product link]\n\n"
            "This offer expires in 48 hours."
        ),
    },
    {
        "day": 7,
        "subject": "Last chance — LAUNCH20 expires tonight",
        "body": (
            "Hey {{subscriber.first_name | default: 'there'}},\n\n"
            "Final reminder: use LAUNCH20 at checkout for 20% off the full 50-prompt pack.\n\n"
            "[product link]\n\nAfter tonight, it's back to full price."
        ),
    },
]


def attempt_convertkit_signup(page) -> bool:
    """Returns True if signup succeeded, raises ManualInterventionRequired if verification needed."""
    page.goto("https://app.convertkit.com/users/signup", wait_until="networkidle")
    human_delay()

    if "dashboard" in page.url or "subscribers" in page.url:
        print("Already logged into ConvertKit.")
        return True

    try:
        human_type(page, 'input[name="user[email]"]', EMAIL)
        human_delay(1, 2)

        if page.query_selector('input[name="user[first_name]"]'):
            state = load()
            persona = state.get("persona", {})
            name = persona.get("name", "Alex Morgan").split()[0]
            human_type(page, 'input[name="user[first_name]"]', name)
            human_delay()

        page.click('button[type="submit"], input[type="submit"]')
        human_delay(3, 5)

        if page.query_selector("iframe[src*='recaptcha'], .h-captcha"):
            log_item(
                "ConvertKit CAPTCHA",
                f"Complete the CAPTCHA at {page.url} in a browser, then re-run.",
                "email_setup.py",
            )
            raise ManualInterventionRequired("CAPTCHA on ConvertKit signup")

        if any(phrase in page.content().lower() for phrase in ["check your email", "verify your email", "confirmation email"]):
            log_item(
                "ConvertKit email verification required",
                f"Check jeffcrooks.ai@gmail.com for a ConvertKit verification email and click the link. Then re-run: python email_setup.py",
                "email_setup.py",
            )
            raise ManualInterventionRequired("Email verification required")

        return True
    except ManualInterventionRequired:
        raise
    except Exception as e:
        log_item(
            f"ConvertKit signup error: {e}",
            f"Manually create a ConvertKit account at https://convertkit.com with {EMAIL}, then save credentials to .env as CONVERTKIT_EMAIL and CONVERTKIT_PASSWORD, then re-run.",
            "email_setup.py",
        )
        raise ManualInterventionRequired(str(e))


def create_landing_page(page, niche: str, free_pdf_path: str) -> str:
    """Creates a landing page and returns its URL."""
    page.goto(f"{CONVERTKIT_URL}/landing_pages", wait_until="networkidle")
    human_delay(2, 4)

    new_btn = page.query_selector('a[href*="new"], button:has-text("New"), button:has-text("Create")')
    if new_btn:
        new_btn.click()
        human_delay(2, 4)

    log_item(
        "ConvertKit landing page creation",
        (
            f"In ConvertKit, create a new landing page with:\n"
            f"  - Title: 'Get 10 Free {niche} Outreach Prompts'\n"
            f"  - Headline: 'Boost Your Reply Rate With These 10 Free Templates'\n"
            f"  - Add the free PDF ({free_pdf_path}) as an incentive/download\n"
            f"  - Save the landing page URL to landing_url.txt\n"
            f"  Then re-run: python email_setup.py"
        ),
        "email_setup.py",
    )
    raise ManualInterventionRequired("Manual landing page creation required")


def run_email_setup() -> None:
    state = load()
    niche = state.get("niche") or "Recruiter Cold Outreach"

    with BrowserSession() as session:
        page = session.page

        attempt_convertkit_signup(page)

        if LANDING_URL_FILE.exists():
            landing_url = LANDING_URL_FILE.read_text().strip()
            print(f"Landing URL already captured: {landing_url}")
        else:
            landing_url = create_landing_page(page, niche, str(Path("assets/free-sample-pack.pdf")))
            LANDING_URL_FILE.write_text(landing_url)

        state["landing_url"] = landing_url
        save(state)

    mark_phase_complete(2)
    print(f"\nPhase 2 complete. Landing URL: {landing_url}")


if __name__ == "__main__":
    if is_phase_complete(2):
        print("Phase 2 already complete.")
    else:
        run_email_setup()
