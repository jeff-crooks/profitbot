#!/usr/bin/env python3
"""Phase 2: Kit (ConvertKit) funnel setup via API."""

import os
import re
from pathlib import Path

import requests

from lib.claude_client import _load_shell_env_file
from lib.manual import log_item, ManualInterventionRequired
from lib.state import load, save, mark_phase_complete, is_phase_complete

_load_shell_env_file(Path.home() / ".env.secrets")

KIT_API_KEY = os.environ.get("KIT_API_KEY", "")
KIT_BASE = "https://api.kit.com/v4"
LANDING_URL_FILE = Path("landing_url.txt")

SEQUENCE_NAME = "Recruiter Outreach Nurture"
SEQUENCE_EMAILS = [
    {
        "subject": "One quick tip to double your reply rate",
        "content": (
            "Hey {{subscriber.first_name | default: 'there'}},\n\n"
            "Yesterday you grabbed the free prompt pack. Here's a tip that gets 2-3x more replies:\n\n"
            "Always personalize the first line. Reference something specific about their company or recent news.\n\n"
            "The full pack (50 prompts + follow-up sequences) has a whole category dedicated to this: "
            "grab it here — [product link].\n\nTalk soon,\nDanielle"
        ),
        "delay_value": 1,
        "delay_unit": "days",
    },
    {
        "subject": "How Sarah booked 12 interviews in one week",
        "content": (
            "Hey {{subscriber.first_name | default: 'there'}},\n\n"
            "Sarah is a recruiter who was struggling with response rates under 5%.\n\n"
            "She started using structured prompt templates and hit 18% reply rate in her first week.\n\n"
            "The difference? Consistency + personalization at scale. "
            "The full prompt pack gives you the exact framework: [product link].\n\nBest,\nDanielle"
        ),
        "delay_value": 3,
        "delay_unit": "days",
    },
    {
        "subject": "Still sending emails that get ignored?",
        "content": (
            "Hey {{subscriber.first_name | default: 'there'}},\n\n"
            "The #1 reason cold emails fail: generic openers.\n\n"
            "The full 50-prompt pack fixes that. Use code LAUNCH20 for 20% off: [product link]\n\n"
            "This offer expires in 48 hours.\n\nDanielle"
        ),
        "delay_value": 5,
        "delay_unit": "days",
    },
    {
        "subject": "Last chance — LAUNCH20 expires tonight",
        "content": (
            "Hey {{subscriber.first_name | default: 'there'}},\n\n"
            "Final reminder: use LAUNCH20 at checkout for 20% off the full 50-prompt pack.\n\n"
            "[product link]\n\nAfter tonight, it's back to full price.\n\nDanielle"
        ),
        "delay_value": 7,
        "delay_unit": "days",
    },
]


def kit_headers() -> dict:
    return {"X-Kit-Api-Key": KIT_API_KEY, "Accept": "application/json", "Content-Type": "application/json"}


def kit_get(path: str) -> dict:
    r = requests.get(f"{KIT_BASE}{path}", headers=kit_headers())
    r.raise_for_status()
    return r.json()


def kit_post(path: str, data: dict) -> dict:
    r = requests.post(f"{KIT_BASE}{path}", headers=kit_headers(), json=data)
    r.raise_for_status()
    return r.json()


def verify_api_key() -> None:
    if not KIT_API_KEY:
        raise RuntimeError("KIT_API_KEY not set in ~/.env.secrets")
    account = kit_get("/account")
    print(f"Kit account: {account['account']['name']} ({account['account']['primary_email_address']})")


def ensure_sequence() -> int:
    """Returns sequence ID, creating it if it doesn't exist."""
    sequences = kit_get("/sequences").get("sequences", [])
    for seq in sequences:
        if seq["name"] == SEQUENCE_NAME:
            print(f"Sequence already exists: id={seq['id']}")
            return seq["id"]

    seq = kit_post("/sequences", {"name": SEQUENCE_NAME})["sequence"]
    print(f"Created sequence: id={seq['id']}")
    return seq["id"]


def ensure_sequence_emails(seq_id: int) -> None:
    """Adds emails to the sequence if not already present."""
    existing = kit_get(f"/sequences/{seq_id}/emails").get("emails", [])
    existing_subjects = {e["subject"] for e in existing}

    for email in SEQUENCE_EMAILS:
        if email["subject"] in existing_subjects:
            print(f"  Email already exists: {email['subject']}")
            continue
        result = kit_post(f"/sequences/{seq_id}/emails", email)
        print(f"  Created email: day={email['delay_value']} — {email['subject']}")


def ensure_landing_url(niche: str) -> str:
    """Returns landing URL from file, or logs manual item and raises."""
    if LANDING_URL_FILE.exists():
        url = LANDING_URL_FILE.read_text().strip()
        if url:
            print(f"Landing URL: {url}")
            return url

    log_item(
        "Kit landing page required",
        (
            f"The Kit API does not support creating landing pages — use the UI:\n"
            f"1. Go to https://app.kit.com/landing_pages/new\n"
            f"2. Choose any template\n"
            f"3. Set headline: 'Get 10 Free {niche} Prompts'\n"
            f"4. Set subheadline: 'Boost your reply rate with these ready-to-use templates'\n"
            f"5. Under Incentive, upload: assets/free-sample-pack.pdf\n"
            f"6. Connect sequence: '{SEQUENCE_NAME}'\n"
            f"7. Publish and copy the URL\n"
            f"8. Run: echo 'YOUR_URL' > landing_url.txt\n"
            f"9. Re-run: python email_setup.py"
        ),
        "email_setup.py",
    )
    raise ManualInterventionRequired("Landing page must be created in Kit UI")


def run_email_setup() -> None:
    verify_api_key()

    state = load()
    niche = state.get("niche") or "Recruiter Cold Outreach"

    seq_id = ensure_sequence()
    ensure_sequence_emails(seq_id)
    state["kit_sequence_id"] = seq_id
    save(state)

    landing_url = ensure_landing_url(niche)

    state["landing_url"] = landing_url
    save(state)

    mark_phase_complete(2)
    print(f"\nPhase 2 complete. Sequence ID: {seq_id}, Landing URL: {landing_url}")


if __name__ == "__main__":
    if is_phase_complete(2):
        print("Phase 2 already complete.")
    else:
        run_email_setup()
