#!/usr/bin/env python3
"""Phase 5: Daily metrics collection and decision tree."""

import csv
import json
from datetime import date
from pathlib import Path

from lib.state import load, save, get_day_offset
from lib.claude_client import generate

LOGS_DIR = Path("logs")
DECISIONS_LOG = LOGS_DIR / "decisions_log.txt"
SPEND_LOG = LOGS_DIR / "spend_log.csv"


def run_decision_tree(day: int, metrics: dict) -> list[dict]:
    decisions = []

    if day >= 3:
        if metrics.get("conversion_rate", 1) < 0.005:
            decisions.append({
                "action": "upgrade_cover",
                "reason": f"Conversion rate {metrics['conversion_rate']:.1%} < 0.5%",
                "budget": 30,
            })
        if metrics.get("email_signups", 99) < 5:
            decisions.append({
                "action": "rewrite_landing_copy",
                "reason": f"Only {metrics['email_signups']} signups after 3 days",
                "budget": 0,
            })
        if not metrics.get("reddit_traction", True):
            decisions.append({
                "action": "expand_subreddits",
                "reason": "No Reddit posts gaining traction",
                "budget": 0,
            })

    if day >= 7:
        sales = metrics.get("sales", 0)
        if sales == 0:
            decisions.append({
                "action": "flash_sale",
                "reason": "Zero sales by Day 7 — pivot with price drop + ad spend",
                "budget": 70,
            })
        elif sales >= 5:
            decisions.append({
                "action": "raise_price",
                "reason": f"{sales} sales by Day 7 — raise price 30%",
                "budget": 0,
            })

    if day >= 10:
        decisions.append({
            "action": "subscriber_campaign",
            "reason": "Day 10 — send SUBSCRIBER30 email to list",
            "budget": 0,
        })

    if day >= 14:
        decisions.append({
            "action": "generate_retrospective",
            "reason": "Day 14 — generate full retrospective",
            "budget": 0,
        })

    return decisions


def collect_metrics(state: dict) -> dict:
    """Collects what metrics we can without paid API access."""
    metrics = {
        "conversion_rate": 1.0,
        "email_signups": 99,
        "sales": 0,
        "reddit_traction": False,
        "gumroad_url": state.get("gumroad_url", ""),
        "landing_url": state.get("landing_url", ""),
    }

    channel_log = LOGS_DIR / "channel_log.csv"
    if channel_log.exists():
        with open(channel_log) as f:
            rows = list(csv.DictReader(f))
            reddit_posts = [r for r in rows if r.get("channel") == "reddit" and r.get("url")]
            metrics["reddit_traction"] = len(reddit_posts) > 0

    sales_log = LOGS_DIR / "sales_log.csv"
    if sales_log.exists():
        with open(sales_log) as f:
            rows = list(csv.DictReader(f))
            metrics["sales"] = len(rows)

    return metrics


def log_decision(day: int, decision: dict) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    with open(DECISIONS_LOG, "a") as f:
        f.write(f"[{date.today().isoformat()}] Day {day}: {decision['action']} — {decision['reason']}\n")
    print(f"  Decision: {decision['action']} — {decision['reason']}")


def log_spend(amount: float, category: str, reason: str) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    is_new = not SPEND_LOG.exists()
    with open(SPEND_LOG, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "amount", "category", "reason"])
        if is_new:
            writer.writeheader()
        writer.writerow({"date": date.today().isoformat(), "amount": amount, "category": category, "reason": reason})


def generate_retrospective(state: dict, metrics: dict) -> None:
    spend = 0.0
    if SPEND_LOG.exists():
        with open(SPEND_LOG) as f:
            spend = sum(float(r.get("amount", 0)) for r in csv.DictReader(f))

    retro = generate(
        system="Write honest, data-driven business retrospectives.",
        prompt=f"""Write a 14-day launch retrospective for a {state.get('niche', 'prompt pack')} digital product.

Data:
- Total spend: ${spend:.2f}
- Sales: {metrics.get('sales', 0)}
- Email signups: {metrics.get('email_signups', 0)}
- Gumroad URL: {state.get('gumroad_url', 'N/A')}
- Channels used: Reddit, X/Twitter, Indie Hackers, Product Hunt (attempted)

Include sections: Summary, What Worked, What Didn't, Net Profit, Top Channel, Lessons Learned.
Then write next_product_recommendations with 3 specific follow-up product ideas using the same playbook.""",
        max_tokens=2000,
    )

    report_path = LOGS_DIR / f"retrospective_{date.today().isoformat()}.md"
    report_path.write_text(retro)
    Path("next_product_recommendations.md").write_text(retro)
    print(f"Retrospective saved to {report_path}")


def write_daily_report(day: int, metrics: dict, decisions: list[dict]) -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    report = (
        f"# Daily Report — {date.today().isoformat()} (Day {day})\n\n"
        f"## Metrics\n"
        f"- Sales: {metrics.get('sales', 0)}\n"
        f"- Email signups: {metrics.get('email_signups', 0)}\n"
        f"- Conversion rate: {metrics.get('conversion_rate', 0):.2%}\n"
        f"- Reddit traction: {metrics.get('reddit_traction', False)}\n\n"
        f"## Decisions\n"
        + "\n".join(f"- {d['action']}: {d['reason']}" for d in decisions)
        + "\n"
    )
    path = LOGS_DIR / f"daily_report_{date.today().isoformat()}.txt"
    path.write_text(report)
    print(f"Daily report saved to {path}")


def run_monitoring() -> None:
    LOGS_DIR.mkdir(exist_ok=True)
    state = load()
    day = get_day_offset()

    print(f"Monitor run — Day {day}")

    metrics = collect_metrics(state)
    decisions = run_decision_tree(day, metrics)

    for decision in decisions:
        log_decision(day, decision)
        if decision.get("budget", 0) > 0:
            log_spend(decision["budget"], decision["action"], decision["reason"])

    if day >= 14:
        generate_retrospective(state, metrics)

    write_daily_report(day, metrics, decisions)
    print("Monitoring complete.")


if __name__ == "__main__":
    run_monitoring()
