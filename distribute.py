#!/usr/bin/env python3
"""Phase 4: Multi-channel distribution with daily posting scheduler."""

import csv
import random
import time
from datetime import date
from pathlib import Path

from lib.state import load, save, get_day_offset
from lib.manual import log_item, ManualInterventionRequired
from lib.browser import BrowserSession, human_delay, human_type, post_delay
from lib.claude_client import generate

CHANNEL_LOG = Path("logs/channel_log.csv")
EMAIL = "jeffcrooks.ai@gmail.com"

# Posting schedule: list of (earliest_day, label, channel, action_fn_name)
SCHEDULE = [
    (0, "reddit_warmup_day0", "reddit", "reddit_warmup_post"),
    (1, "reddit_warmup_day1", "reddit", "reddit_warmup_post"),
    (2, "reddit_warmup_day2", "reddit", "reddit_warmup_post"),
    (3, "indie_hackers_launch", "indie_hackers", "post_indie_hackers"),
    (4, "x_thread_day4", "twitter", "post_x_thread"),
    (4, "reddit_value_day4", "reddit", "reddit_value_post"),
    (7, "product_hunt_launch", "product_hunt", "post_product_hunt"),
    (7, "reddit_value_day7", "reddit", "reddit_value_post"),
    (10, "reddit_value_day10", "reddit", "reddit_value_post"),
    (14, "reddit_value_day14", "reddit", "reddit_value_post"),
]


def get_due_actions(day_offset: int) -> list[dict]:
    return [
        {"label": label, "channel": channel, "action": action}
        for earliest_day, label, channel, action in SCHEDULE
        if day_offset >= earliest_day
    ]


def was_action_done(label: str) -> bool:
    if not CHANNEL_LOG.exists():
        return False
    with open(CHANNEL_LOG) as f:
        reader = csv.DictReader(f)
        return any(row.get("label") == label for row in reader)


def log_action(label: str, channel: str, description: str, url: str = "") -> None:
    CHANNEL_LOG.parent.mkdir(exist_ok=True)
    is_new = not CHANNEL_LOG.exists()
    with open(CHANNEL_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "label", "channel", "description", "url"])
        if is_new:
            writer.writeheader()
        writer.writerow({
            "date": date.today().isoformat(),
            "label": label,
            "channel": channel,
            "description": description,
            "url": url,
        })


def generate_reddit_warmup_content(niche: str, subreddit: str) -> dict:
    raw = generate(
        system="Write helpful, genuine Reddit posts that provide value without selling anything.",
        prompt=f"""Write a warm-up Reddit post for r/{subreddit} related to {niche}.
This is a genuine value-add post with NO links and NO promotion.
Return JSON: {{"title": "...", "body": "..."}}
Title under 100 chars. Body 150-250 words. Helpful tip or question.""",
        max_tokens=400,
        use_cache=False,
    )
    import json, re
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()
    return json.loads(raw)


def generate_reddit_value_content(niche: str, subreddit: str, landing_url: str) -> dict:
    raw = generate(
        system="Write helpful Reddit posts that naturally lead to a free resource.",
        prompt=f"""Write a value Reddit post for r/{subreddit} about {niche}.
Share 3-4 genuine tips, then end with a soft mention of the free prompt pack at {landing_url}.
Return JSON: {{"title": "...", "body": "..."}}
Title under 100 chars. Body 200-300 words. Natural, not spammy.""",
        max_tokens=500,
        use_cache=False,
    )
    import json, re
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()
    return json.loads(raw)


def generate_x_thread(niche: str, landing_url: str, free_prompts: list[dict]) -> list[str]:
    sample_prompts = "\n".join(f"{i+1}. {p['text']}" for i, p in enumerate(free_prompts[:5]))
    raw = generate(
        system="Write engaging Twitter/X threads that provide value and drive sign-ups.",
        prompt=f"""Write a 10-tweet thread sharing {niche} cold outreach tips.
Include these 5 sample prompts naturally:
{sample_prompts}

End with: "Want all 50 prompts? Grab the free 10-sample pack here: {landing_url}"
Return as JSON array of 10 strings (each tweet under 280 chars).""",
        max_tokens=1500,
        use_cache=False,
    )
    import json, re
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip().rstrip("```").strip()
    return json.loads(raw)


def post_to_reddit(page, subreddit: str, title: str, body: str) -> str:
    """Posts to Reddit. Returns post URL or raises ManualInterventionRequired."""
    page.goto(f"https://www.reddit.com/r/{subreddit}/submit", wait_until="networkidle")
    human_delay(2, 4)

    if "login" in page.url or "register" in page.url:
        log_item(
            f"Reddit login required for r/{subreddit}",
            f"Log into Reddit at https://reddit.com/login with the agent account, then re-run: python distribute.py",
            "distribute.py",
        )
        raise ManualInterventionRequired("Reddit login required")

    if page.query_selector("iframe[src*='recaptcha'], .h-captcha"):
        log_item(
            "Reddit CAPTCHA",
            f"Complete CAPTCHA at {page.url}, then re-run: python distribute.py",
            "distribute.py",
        )
        raise ManualInterventionRequired("Reddit CAPTCHA")

    try:
        title_input = page.query_selector('textarea[placeholder*="Title"], input[placeholder*="Title"]')
        if title_input:
            title_input.click()
            human_delay(0.5, 1)
            title_input.fill(title)
            human_delay()

        body_input = page.query_selector('div[contenteditable="true"], textarea[placeholder*="text"]')
        if body_input:
            body_input.click()
            human_delay(0.5, 1)
            page.keyboard.type(body[:40000], delay=5)
            human_delay()

        submit_btn = page.query_selector('button:has-text("Post"), button[type="submit"]')
        if submit_btn:
            submit_btn.click()
            human_delay(3, 5)
            return page.url
    except Exception as e:
        log_item(
            f"Reddit post failed on r/{subreddit}",
            f"Manually post to r/{subreddit}:\nTitle: {title}\nBody: [see logs for content]\nThen re-run: python distribute.py",
            "distribute.py",
        )
        raise ManualInterventionRequired(str(e))
    return page.url


def post_indie_hackers(state: dict) -> None:
    niche = state.get("niche", "Recruiter Cold Outreach")
    persona = state.get("persona", {})
    gumroad_url = state.get("gumroad_url", "[gumroad_url]")
    landing_url = state.get("landing_url", "[landing_url]")

    raw = generate(
        system="Write authentic Indie Hackers launch posts.",
        prompt=f"""Write an Indie Hackers launch post for a {niche} prompt pack.
Persona name: {persona.get('name', 'Alex')}
Backstory: {persona.get('backstory', 'Former professional turned digital product creator')}
Gumroad URL: {gumroad_url}
Free sample URL: {landing_url}

Format: founder story (3-4 sentences), the problem, the solution, ask for feedback.
Include both links naturally. 300-400 words.""",
        max_tokens=600,
        use_cache=False,
    )

    log_item(
        "Post to Indie Hackers Launches",
        (
            f"Post the following to https://www.indiehackers.com/post/new in the Launches section:\n"
            f"Title: Launching: {niche} Prompt Pack\n\n"
            f"Body:\n{raw}\n\n"
            f"Then re-run: python distribute.py (it will log as complete)"
        ),
        "distribute.py",
    )
    log_action("indie_hackers_launch", "indie_hackers", "Logged for manual posting", "")


def post_product_hunt(state: dict) -> None:
    niche = state.get("niche", "Recruiter Cold Outreach")
    gumroad_url = state.get("gumroad_url", "[gumroad_url]")

    log_item(
        "Product Hunt launch",
        (
            f"Launch on Product Hunt at https://www.producthunt.com/posts/new:\n"
            f"  Name: {niche} Prompt Pack\n"
            f"  Tagline: 50 cold outreach templates for {niche.lower()} professionals\n"
            f"  Link: {gumroad_url}\n"
            f"  Upload cover image: assets/cover.png\n"
            f"  Best launch day: Tuesday or Wednesday\n"
            f"  Then send an email blast to your ConvertKit list asking for upvotes.\n"
            f"  Then re-run: python distribute.py (it will mark as done)"
        ),
        "distribute.py",
    )
    log_action("product_hunt_launch", "product_hunt", "Logged for manual launch", "")


def run_distribution() -> None:
    Path("logs").mkdir(exist_ok=True)
    state = load()
    day_offset = get_day_offset()
    niche = state.get("niche", "Recruiter Cold Outreach")
    landing_url = state.get("landing_url", "")
    subreddits = state.get("target_subreddits", ["sales", "Entrepreneur", "freelance"])

    print(f"Distribution run — Day {day_offset}")
    due = get_due_actions(day_offset)

    for action in due:
        label = action["label"]
        if was_action_done(label):
            print(f"  Skipping {label} (already done)")
            continue

        print(f"  Running: {label}")

        try:
            if action["action"] == "reddit_warmup_post":
                subreddit = subreddits[day_offset % len(subreddits)]
                content = generate_reddit_warmup_content(niche, subreddit)
                with BrowserSession() as session:
                    url = post_to_reddit(session.page, subreddit, content["title"], content["body"])
                log_action(label, "reddit", f"Warmup post on r/{subreddit}", url)
                post_delay()

            elif action["action"] == "reddit_value_post":
                subreddit = subreddits[day_offset % len(subreddits)]
                content = generate_reddit_value_content(niche, subreddit, landing_url)
                with BrowserSession() as session:
                    url = post_to_reddit(session.page, subreddit, content["title"], content["body"])
                log_action(label, "reddit", f"Value post on r/{subreddit}", url)
                post_delay()

            elif action["action"] == "post_x_thread":
                import json as _json
                prompts_file = Path("prompts/prompts.json")
                free_prompts = _json.loads(prompts_file.read_text())[:10] if prompts_file.exists() else []
                tweets = generate_x_thread(niche, landing_url, free_prompts)
                log_item(
                    "Post X/Twitter thread",
                    f"Post this {len(tweets)}-tweet thread on X from the @{state.get('persona', {}).get('username', 'agent')} account:\n\n"
                    + "\n\n---\n".join(f"Tweet {i+1}: {t}" for i, t in enumerate(tweets))
                    + f"\n\nThen re-run: python distribute.py",
                    "distribute.py",
                )
                log_action(label, "twitter", "X thread logged for manual posting", "")

            elif action["action"] == "post_indie_hackers":
                post_indie_hackers(state)

            elif action["action"] == "post_product_hunt":
                post_product_hunt(state)

        except ManualInterventionRequired:
            print(f"  Manual intervention required for {label} — see manual_work.md")
            continue

    state["last_distribute_date"] = date.today().isoformat()
    save(state)
    print("Distribution run complete.")


if __name__ == "__main__":
    run_distribution()
