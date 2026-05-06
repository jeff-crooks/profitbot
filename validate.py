#!/usr/bin/env python3
"""Phase 0: Market validation via Gumroad + Reddit scraping."""

import csv
import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from lib.state import load, save, mark_phase_complete, is_phase_complete
from lib.claude_client import generate

VALIDATION_DIR = Path("validation")
GUMROAD_CSV = VALIDATION_DIR / "gumroad_competitors.csv"
REDDIT_CSV = VALIDATION_DIR / "reddit_demand.csv"
REPORT_MD = VALIDATION_DIR / "validation_report.md"

NICHES = {
    "recruiter": {
        "label": "Recruiter Cold Outreach",
        "queries": ["recruiter cold email", "recruiting outreach", "recruiter message template"],
        "subreddits": ["recruiting", "humanresources", "cscareerquestions"],
    },
    "generic_sales": {
        "label": "Generic Sales Outreach",
        "queries": ["cold email", "sales outreach", "email templates"],
        "subreddits": ["sales", "Entrepreneur", "startups"],
    },
    "freelancer": {
        "label": "Freelancer Pitching",
        "queries": ["freelance pitch", "freelance outreach", "client acquisition"],
        "subreddits": ["freelance", "forhire", "Entrepreneur"],
    },
    "b2b_saas": {
        "label": "B2B SaaS Outbound",
        "queries": ["b2b cold email", "saas outreach", "b2b lead generation"],
        "subreddits": ["saas", "sales", "Entrepreneur"],
    },
    "real_estate": {
        "label": "Real Estate Outreach",
        "queries": ["real estate cold email", "realtor outreach", "real estate prospecting"],
        "subreddits": ["realestate", "RealEstateInvesting", "realtors"],
    },
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}


def scrape_gumroad_products(query: str) -> list[dict]:
    url = f"https://gumroad.com/discover?query={query.replace(' ', '+')}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        products = []
        for item in soup.select("[data-permalink]")[:20]:
            title_el = item.select_one("h3, .product-name, [class*='title']")
            price_el = item.select_one("[class*='price']")
            products.append({
                "title": title_el.text.strip() if title_el else "unknown",
                "price": price_el.text.strip() if price_el else "unknown",
                "url": item.get("data-permalink", ""),
            })
        return products
    except Exception as e:
        print(f"Gumroad scrape failed for '{query}': {e}")
        return []


def fetch_reddit_posts(subreddit: str, query: str) -> dict:
    url = f"https://www.reddit.com/r/{subreddit}/search.json"
    params = {"q": query, "sort": "relevance", "t": "year", "limit": 25}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        return resp.json()
    except Exception as e:
        print(f"Reddit fetch failed for r/{subreddit} '{query}': {e}")
        return {"data": {"children": []}}


def parse_reddit_results(data: dict) -> list[dict]:
    posts = []
    for child in data.get("data", {}).get("children", []):
        d = child.get("data", {})
        posts.append({
            "title": d.get("title", ""),
            "score": d.get("score", 0),
            "num_comments": d.get("num_comments", 0),
            "subreddit": d.get("subreddit", ""),
        })
    return posts


def score_niche(posts: list[dict]) -> dict:
    return {
        "total_score": sum(p["score"] for p in posts),
        "total_comments": sum(p["num_comments"] for p in posts),
        "post_count": len(posts),
    }


def select_best_niche(scores: dict) -> str:
    if not scores:
        return "recruiter"
    return max(scores, key=lambda k: scores[k]["total_score"])


def run_validation() -> None:
    VALIDATION_DIR.mkdir(exist_ok=True)

    # Scrape Gumroad
    print("Scraping Gumroad...")
    gumroad_rows = []
    for query in ["prompts", "cold email", "outreach templates"]:
        products = scrape_gumroad_products(query)
        for p in products:
            p["search_query"] = query
            gumroad_rows.append(p)
        time.sleep(2)

    with open(GUMROAD_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["search_query", "title", "price", "url"])
        writer.writeheader()
        writer.writerows(gumroad_rows)
    print(f"Saved {len(gumroad_rows)} Gumroad products to {GUMROAD_CSV}")

    # Scrape Reddit
    print("Scanning Reddit demand signals...")
    all_posts = []
    niche_scores = {}

    for niche_key, niche_data in NICHES.items():
        niche_posts = []
        for subreddit in niche_data["subreddits"][:2]:
            for query in niche_data["queries"][:2]:
                data = fetch_reddit_posts(subreddit, query)
                posts = parse_reddit_results(data)
                for p in posts:
                    p["niche"] = niche_key
                    all_posts.append(p)
                    niche_posts.append(p)
                time.sleep(1)
        niche_scores[niche_key] = score_niche(niche_posts)
        print(f"  {niche_data['label']}: score={niche_scores[niche_key]['total_score']}")

    with open(REDDIT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["niche", "subreddit", "title", "score", "num_comments"])
        writer.writeheader()
        writer.writerows(all_posts)
    print(f"Saved {len(all_posts)} Reddit posts to {REDDIT_CSV}")

    # Select best niche
    best_niche_key = select_best_niche(niche_scores)
    best_niche = NICHES[best_niche_key]

    # Determine price from Gumroad competitor median
    prices = []
    for row in gumroad_rows:
        try:
            price_str = row["price"].replace("$", "").replace("free", "0").strip()
            if price_str:
                prices.append(float(price_str.split()[0]))
        except (ValueError, IndexError):
            pass
    competitor_median = sorted(prices)[len(prices) // 2] if prices else 15.0
    recommended_price = min([7, 9, 15, 19, 29], key=lambda p: abs(p - competitor_median))

    # Generate report with Claude
    print("Generating validation report...")
    scores_summary = "\n".join(
        f"- {NICHES[k]['label']}: score={v['total_score']}, comments={v['total_comments']}, posts={v['post_count']}"
        for k, v in niche_scores.items()
    )
    report_text = generate(
        system="You are a digital product market analyst. Be concise and data-driven.",
        prompt=f"""Based on these Reddit demand scores for prompt pack niches:

{scores_summary}

Gumroad competitor median price: ${competitor_median:.2f}

Write a validation_report.md with these exact sections:
## Recommended Niche
## Optimal Price Point
## Top 3 Messaging Angles
## Target Subreddits (list 5)

The recommended niche is {best_niche['label']}. Price recommendation: ${recommended_price}.""",
        max_tokens=1000,
    )

    REPORT_MD.write_text(report_text)
    print(f"Validation report saved to {REPORT_MD}")

    # Update state
    state = load()
    state["niche"] = best_niche["label"]
    state["price"] = recommended_price
    state["niche_key"] = best_niche_key
    state["target_subreddits"] = best_niche["subreddits"]
    save(state)
    mark_phase_complete(0)
    print(f"\nPhase 0 complete. Niche: {best_niche['label']}, Price: ${recommended_price}")


if __name__ == "__main__":
    if is_phase_complete(0):
        print("Phase 0 already complete. Delete state.json to re-run.")
    else:
        run_validation()
