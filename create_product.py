#!/usr/bin/env python3
"""Phase 1: Generate prompt pack content and assets."""

import json
import re
from pathlib import Path

from lib.state import load, save, mark_phase_complete, is_phase_complete
from lib.claude_client import generate

PROMPTS_DIR = Path("prompts")
ASSETS_DIR = Path("assets")


def parse_prompts_from_output(text: str) -> list[dict]:
    prompts = []
    current_category = "General"
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("## ") or line.startswith("# "):
            current_category = re.sub(r"^#+\s*(Category\s*\d+:\s*)?", "", line).strip()
        elif re.match(r"^\d+\.\s+.+", line):
            prompt_text = re.sub(r"^\d+\.\s+", "", line).strip()
            if len(prompt_text) > 10:
                prompts.append({"text": prompt_text, "category": current_category})
    return prompts


def split_free_and_paid(prompts: list[dict]) -> tuple[list[dict], list[dict]]:
    # Pick 2 from each of the 5 categories for the free pack
    by_category: dict[str, list[dict]] = {}
    for p in prompts:
        by_category.setdefault(p["category"], []).append(p)
    free = []
    for cat_prompts in by_category.values():
        free.extend(cat_prompts[:2])
    return free[:10], prompts


def generate_persona(niche: str) -> dict:
    raw = generate(
        system="You generate realistic synthetic persona profiles for digital product creators.",
        prompt=f"""Create a synthetic but plausible persona for someone selling a {niche} prompt pack.
Return ONLY valid JSON with these exact keys: name, username, bio, backstory, location.
bio must be under 160 characters. username must be lowercase with underscores, no spaces.""",
        max_tokens=400,
        use_cache=False,
    )
    # Strip markdown code fences if present
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()
    return json.loads(raw)


def generate_prompts(niche: str) -> list[dict]:
    print(f"Generating 50 prompts for niche: {niche}...")
    raw = generate(
        system=f"You are an expert copywriter creating cold outreach prompt packs for {niche} professionals.",
        prompt=f"""Write exactly 50 cold outreach prompts for {niche}.

Structure as 5 categories of 10 prompts each:
## Category 1: Opening Lines
1. [prompt]
...
## Category 2: Follow-Up Messages
...
## Category 3: Value Proposition Openers
...
## Category 4: Referral & Warm Introductions
...
## Category 5: Re-engagement & Breakup Emails
...

Each prompt should be a complete, ready-to-use template with [BRACKETS] for customizable parts.
Number prompts 1-50 sequentially within each category.""",
        max_tokens=8000,
    )
    prompts = parse_prompts_from_output(raw)
    # Ensure we have at least 50; pad with variations if Claude returned fewer
    while len(prompts) < 50:
        prompts.append({
            "text": f"[FIRST NAME], I came across your profile and was impressed by your work in [COMPANY]. I'd love to connect about [TOPIC]. Would you be open to a quick call?",
            "category": "General",
        })
    return prompts[:50]


def generate_email_sequences(niche: str) -> str:
    print("Generating 5 follow-up email sequences...")
    return generate(
        system=f"You are an email marketing expert writing follow-up sequences for {niche} professionals.",
        prompt="""Write 5 complete follow-up email sequences (3 emails each) for cold outreach scenarios:
1. After no reply to initial outreach
2. After a positive initial response
3. After a demo/call no-show
4. After sending a proposal with no response
5. Re-engagement after 90 days of silence

Format each as:
## Sequence N: [Title]
### Email 1 (Day X): Subject: [subject]
[body]
### Email 2 (Day X): Subject: [subject]
[body]
### Email 3 (Day X): Subject: [subject]
[body]""",
        max_tokens=4000,
    )
