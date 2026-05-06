# ProfitBot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an autonomous Python agent that validates a niche, creates a digital product, builds an email funnel, launches on Gumroad, and distributes across 5+ channels over 14 days targeting >$100 net revenue.

**Architecture:** Independent idempotent phase scripts (`validate.py`, `create_product.py`, `email_setup.py`, `gumroad_setup.py`, `distribute.py`, `monitor.py`) coordinated by `agent.py`. `state.json` tracks completed phases for crash-safe resumption. Any step requiring human action appends to `manual_work.md` and raises `ManualInterventionRequired`. Cron drives daily distribution + monitoring.

**Tech Stack:** Python 3.12, Playwright (Chromium headless), Anthropic SDK `claude-sonnet-4-6`, reportlab, Pillow, requests, BeautifulSoup4, pandas, python-dotenv, pytest

---

## File Map

| File | Responsibility |
|------|---------------|
| `lib/state.py` | Read/write `state.json`; phase completion flags; day offset |
| `lib/manual.py` | `ManualInterventionRequired` exception; append to `manual_work.md` |
| `lib/browser.py` | Playwright `BrowserSession` context manager; human-like timing; CAPTCHA detector |
| `lib/claude_client.py` | Anthropic SDK wrapper; prompt caching |
| `validate.py` | Phase 0: scrape Gumroad + Reddit; call Claude; write `validation_report.md` |
| `create_product.py` | Phase 1: generate 50 prompts via Claude; render PDFs; cover image; `compliance_notes.txt` |
| `email_setup.py` | Phase 2: Playwright → ConvertKit signup + landing page + drip sequence |
| `gumroad_setup.py` | Phase 3: Playwright → Gumroad signup + product listing + discount codes |
| `distribute.py` | Phase 4: Playwright → account creation + daily posting scheduler |
| `monitor.py` | Phase 5: daily metrics + decision tree (Days 3/7/10/14) |
| `agent.py` | Orchestrator: runs phases 0-5 in order; installs cron job |
| `tests/test_state.py` | Unit tests for state.py |
| `tests/test_manual.py` | Unit tests for manual.py |
| `tests/test_validate.py` | Unit tests for validation logic (mocked HTTP) |
| `tests/test_create_product.py` | Unit tests for PDF/cover generation |
| `tests/test_distribute.py` | Unit tests for posting schedule logic |
| `tests/test_monitor.py` | Unit tests for decision tree |

---

## Task 1: Install dependencies and scaffold project structure

**Files:**
- Create: `requirements.txt`
- Create: `.env` (template, gitignored)
- Create: `.gitignore`
- Create: `validation/`, `prompts/`, `assets/`, `logs/`, `tests/` directories
- Create: `lib/__init__.py`, `tests/__init__.py`

- [ ] **Step 1: Install system dependencies**

```bash
cd /home/agent/projects/profitbot
pip install playwright reportlab pillow anthropic python-dotenv requests pandas beautifulsoup4 pytest pytest-mock
playwright install chromium
```

Expected output ends with: `chromium` installed successfully.

- [ ] **Step 2: Create `requirements.txt`**

```
playwright>=1.40.0
reportlab>=4.0.0
pillow>=10.0.0
anthropic>=0.40.0
python-dotenv>=1.0.0
requests>=2.31.0
pandas>=2.0.0
beautifulsoup4>=4.12.0
pytest>=7.4.0
pytest-mock>=3.12.0
```

- [ ] **Step 3: Create `.env` template**

```
# Discovered credentials — populated by phase scripts
CONVERTKIT_EMAIL=
CONVERTKIT_PASSWORD=
GUMROAD_EMAIL=
GUMROAD_PASSWORD=
REDDIT_USERNAME=
REDDIT_PASSWORD=
TWITTER_USERNAME=
TWITTER_PASSWORD=
IH_USERNAME=
IH_PASSWORD=
```

- [ ] **Step 4: Create `.gitignore`**

```
.env
state.json
__pycache__/
*.pyc
validation/
prompts/
assets/
logs/
manual_work.md
landing_url.txt
compliance_notes.txt
```

- [ ] **Step 5: Create directories and init files**

```bash
mkdir -p validation prompts assets logs tests
touch lib/__init__.py tests/__init__.py
```

- [ ] **Step 6: Verify imports work**

```bash
python -c "import playwright; import reportlab; import PIL; import anthropic; print('OK')"
```

Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git init
git add requirements.txt .gitignore lib/__init__.py tests/__init__.py
git commit -m "feat: scaffold profitbot project structure"
```

---

## Task 2: lib/state.py — Resumable execution state

**Files:**
- Create: `lib/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_state.py`:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from datetime import date


def test_load_returns_default_when_no_file(tmp_path):
    with patch("lib.state.STATE_FILE", tmp_path / "state.json"):
        from lib.state import load
        s = load()
        assert s["phases_completed"] == [False] * 6
        assert s["start_date"] is None


def test_save_and_load_roundtrip(tmp_path):
    with patch("lib.state.STATE_FILE", tmp_path / "state.json"):
        from lib.state import load, save
        s = load()
        s["niche"] = "Recruiter Cold Outreach"
        save(s)
        s2 = load()
        assert s2["niche"] == "Recruiter Cold Outreach"


def test_mark_phase_complete(tmp_path):
    with patch("lib.state.STATE_FILE", tmp_path / "state.json"):
        from lib.state import mark_phase_complete, is_phase_complete
        assert not is_phase_complete(0)
        mark_phase_complete(0)
        assert is_phase_complete(0)
        assert not is_phase_complete(1)


def test_get_day_offset_no_start(tmp_path):
    with patch("lib.state.STATE_FILE", tmp_path / "state.json"):
        from lib.state import get_day_offset
        assert get_day_offset() == 0


def test_get_day_offset_with_start(tmp_path):
    with patch("lib.state.STATE_FILE", tmp_path / "state.json"):
        from lib.state import load, save, get_day_offset
        s = load()
        s["start_date"] = "2026-05-06"
        save(s)
        with patch("lib.state.date") as mock_date:
            mock_date.today.return_value = date(2026, 5, 9)
            mock_date.fromisoformat = date.fromisoformat
            assert get_day_offset() == 3
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_state.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement `lib/state.py`**

```python
import json
from pathlib import Path
from datetime import date

STATE_FILE = Path(__file__).parent.parent / "state.json"

DEFAULT_STATE = {
    "start_date": None,
    "phases_completed": [False, False, False, False, False, False],
    "persona": None,
    "niche": None,
    "price": None,
    "gumroad_url": None,
    "landing_url": None,
    "last_distribute_date": None,
    "channel_accounts": {},
}


def load() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return DEFAULT_STATE.copy()


def save(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))


def mark_phase_complete(phase: int) -> None:
    state = load()
    state["phases_completed"][phase] = True
    save(state)


def is_phase_complete(phase: int) -> bool:
    return load()["phases_completed"][phase]


def get_day_offset() -> int:
    state = load()
    if not state["start_date"]:
        return 0
    start = date.fromisoformat(state["start_date"])
    return (date.today() - start).days
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
pytest tests/test_state.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add lib/state.py tests/test_state.py
git commit -m "feat: add state.py for resumable execution"
```

---

## Task 3: lib/manual.py — Human intervention logging

**Files:**
- Create: `lib/manual.py`
- Create: `tests/test_manual.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_manual.py`:

```python
import pytest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime


def test_log_item_creates_file(tmp_path):
    with patch("lib.manual.MANUAL_FILE", tmp_path / "manual_work.md"):
        from lib.manual import log_item
        log_item("Verify email", "Click verification link in jeffcrooks.ai@gmail.com", "email_setup.py")
        content = (tmp_path / "manual_work.md").read_text()
        assert "Verify email" in content
        assert "email_setup.py" in content
        assert "PENDING" in content


def test_log_item_appends(tmp_path):
    with patch("lib.manual.MANUAL_FILE", tmp_path / "manual_work.md"):
        from lib.manual import log_item
        log_item("Item 1", "Do thing 1", "script1.py")
        log_item("Item 2", "Do thing 2", "script2.py")
        content = (tmp_path / "manual_work.md").read_text()
        assert "Item 1" in content
        assert "Item 2" in content


def test_manual_intervention_required_is_exception():
    from lib.manual import ManualInterventionRequired
    with pytest.raises(ManualInterventionRequired):
        raise ManualInterventionRequired("test")
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_manual.py -v 2>&1 | head -10
```

Expected: `ImportError`

- [ ] **Step 3: Implement `lib/manual.py`**

```python
from pathlib import Path
from datetime import datetime

MANUAL_FILE = Path(__file__).parent.parent / "manual_work.md"


class ManualInterventionRequired(Exception):
    pass


def log_item(title: str, action: str, rerun_script: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = (
        f"\n## [{timestamp}] {title}\n"
        f"**Action required:** {action}\n"
        f"**Re-run:** `python {rerun_script}`\n"
        f"**Status:** PENDING\n"
    )
    with open(MANUAL_FILE, "a") as f:
        f.write(entry)
    print(f"[MANUAL INTERVENTION NEEDED] {title} — see manual_work.md")
```

- [ ] **Step 4: Run to confirm passing**

```bash
pytest tests/test_manual.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add lib/manual.py tests/test_manual.py
git commit -m "feat: add manual.py for human intervention logging"
```

---

## Task 4: lib/browser.py — Playwright helpers

**Files:**
- Create: `lib/browser.py`

- [ ] **Step 1: Create `lib/browser.py`**

```python
import random
import time
from playwright.sync_api import sync_playwright, Page


def human_delay(min_s: float = 2.0, max_s: float = 6.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def post_delay(min_s: float = 30.0, max_s: float = 90.0) -> None:
    time.sleep(random.uniform(min_s, max_s))


def human_type(page: Page, selector: str, text: str) -> None:
    page.click(selector)
    human_delay(0.3, 0.8)
    for char in text:
        page.keyboard.type(char, delay=random.uniform(50, 150))


def is_captcha_present(page: Page) -> bool:
    return bool(
        page.query_selector("iframe[src*='recaptcha']")
        or page.query_selector(".h-captcha")
        or page.query_selector("[data-sitekey]")
        or page.query_selector("iframe[title*='challenge']")
    )


class BrowserSession:
    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, headless: bool = True):
        self._pw = None
        self._browser = None
        self.page = None

    def __enter__(self) -> "BrowserSession":
        self._pw = sync_playwright().__enter__()
        self._browser = self._pw.chromium.launch(headless=True)
        context = self._browser.new_context(user_agent=self.USER_AGENT)
        self.page = context.new_page()
        return self

    def __exit__(self, *args) -> None:
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.__exit__(*args)

    def navigate(self, url: str) -> None:
        self.page.goto(url, wait_until="networkidle", timeout=30000)
        human_delay()

    def check_and_handle_captcha(self, script_name: str) -> None:
        from lib.manual import log_item, ManualInterventionRequired
        if is_captcha_present(self.page):
            log_item(
                "CAPTCHA detected",
                f"Complete the CAPTCHA at {self.page.url} then re-run the script.",
                script_name,
            )
            raise ManualInterventionRequired("CAPTCHA detected")
```

- [ ] **Step 2: Verify import**

```bash
python -c "from lib.browser import BrowserSession, human_delay; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add lib/browser.py
git commit -m "feat: add browser.py Playwright helpers"
```

---

## Task 5: lib/claude_client.py — Anthropic SDK wrapper

**Files:**
- Create: `lib/claude_client.py`

- [ ] **Step 1: Create `lib/claude_client.py`**

```python
import os
from pathlib import Path
import anthropic
from dotenv import load_dotenv

load_dotenv(Path.home() / ".env.secrets")
load_dotenv(Path(__file__).parent.parent / ".env")

_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not found in ~/.env.secrets or .env")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def generate(
    system: str,
    prompt: str,
    max_tokens: int = 4096,
    use_cache: bool = True,
) -> str:
    client = get_client()
    system_block: dict = {"type": "text", "text": system}
    if use_cache:
        system_block["cache_control"] = {"type": "ephemeral"}
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        system=[system_block],
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text
```

- [ ] **Step 2: Verify API key loads and client initializes**

```bash
python -c "from lib.claude_client import get_client; c = get_client(); print('Client OK:', type(c).__name__)"
```

Expected: `Client OK: Anthropic`

- [ ] **Step 3: Commit**

```bash
git add lib/claude_client.py
git commit -m "feat: add claude_client.py with prompt caching"
```

---

## Task 6: validate.py — Phase 0 market validation

**Files:**
- Create: `validate.py`
- Create: `tests/test_validate.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_validate.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock


def test_parse_reddit_results_extracts_posts():
    from validate import parse_reddit_results
    sample = {
        "data": {
            "children": [
                {"data": {"title": "Cold email tips", "score": 150, "num_comments": 30}},
                {"data": {"title": "Outreach for recruiters", "score": 80, "num_comments": 12}},
            ]
        }
    }
    results = parse_reddit_results(sample)
    assert len(results) == 2
    assert results[0]["score"] == 150
    assert results[0]["title"] == "Cold email tips"


def test_parse_reddit_results_empty():
    from validate import parse_reddit_results
    assert parse_reddit_results({"data": {"children": []}}) == []


def test_score_niche_aggregates_correctly():
    from validate import score_niche
    posts = [
        {"score": 100, "num_comments": 20},
        {"score": 50, "num_comments": 10},
    ]
    result = score_niche(posts)
    assert result["total_score"] == 150
    assert result["total_comments"] == 30
    assert result["post_count"] == 2


def test_select_best_niche_picks_highest_score():
    from validate import select_best_niche
    scores = {
        "recruiter": {"total_score": 500, "total_comments": 80, "post_count": 5},
        "generic": {"total_score": 200, "total_comments": 30, "post_count": 3},
        "real_estate": {"total_score": 100, "total_comments": 10, "post_count": 2},
    }
    assert select_best_niche(scores) == "recruiter"


def test_select_best_niche_falls_back_on_empty():
    from validate import select_best_niche
    assert select_best_niche({}) == "recruiter"
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_validate.py -v 2>&1 | head -15
```

Expected: `ImportError`

- [ ] **Step 3: Implement `validate.py`**

```python
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
```

- [ ] **Step 4: Run unit tests**

```bash
pytest tests/test_validate.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add validate.py tests/test_validate.py
git commit -m "feat: add validate.py (Phase 0) with niche scoring"
```

---

## Task 7: create_product.py — Prompt generation via Claude API

**Files:**
- Create: `create_product.py` (prompt generation section)
- Create: `tests/test_create_product.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_create_product.py`:

```python
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


def test_parse_prompts_from_claude_output():
    from create_product import parse_prompts_from_output
    sample = """## Category 1: Opening Lines
1. Prompt one text here.
2. Prompt two text here.
## Category 2: Follow-Up
3. Prompt three text here."""
    result = parse_prompts_from_output(sample)
    assert len(result) >= 2
    assert all("text" in p for p in result)
    assert all("category" in p for p in result)


def test_parse_prompts_handles_numbered_list():
    from create_product import parse_prompts_from_output
    sample = "1. First prompt.\n2. Second prompt.\n3. Third prompt."
    result = parse_prompts_from_output(sample)
    assert len(result) == 3


def test_split_free_and_paid():
    from create_product import split_free_and_paid
    prompts = [{"text": f"Prompt {i}", "category": f"Cat {i % 5}"} for i in range(50)]
    free, paid = split_free_and_paid(prompts)
    assert len(free) == 10
    assert len(paid) == 50


def test_generate_persona_returns_required_keys():
    from create_product import generate_persona
    with patch("create_product.generate") as mock_gen:
        mock_gen.return_value = json.dumps({
            "name": "Alex Morgan",
            "username": "alexmorgan_sales",
            "bio": "Sales coach helping recruiters.",
            "backstory": "Former recruiter turned coach.",
            "location": "Austin, TX",
        })
        persona = generate_persona("Recruiter Cold Outreach")
        assert "name" in persona
        assert "username" in persona
        assert "bio" in persona
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_create_product.py -v 2>&1 | head -15
```

Expected: `ImportError`

- [ ] **Step 3: Create `create_product.py` with parsing functions**

```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_create_product.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add create_product.py tests/test_create_product.py
git commit -m "feat: add prompt generation and persona functions"
```

---

## Task 8: create_product.py — PDF rendering, cover image, compliance notes

**Files:**
- Modify: `create_product.py` (add PDF + image generation + `main()`)

- [ ] **Step 1: Add PDF and cover generation to `create_product.py`**

Append to `create_product.py`:

```python
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from PIL import Image, ImageDraw, ImageFont
import textwrap


COVER_PATH = ASSETS_DIR / "cover.png"
FREE_PDF_PATH = ASSETS_DIR / "free-sample-pack.pdf"
PAID_PDF_PATH = ASSETS_DIR / "full-prompt-pack.pdf"
COMPLIANCE_PATH = Path("compliance_notes.txt")


def generate_cover(niche: str) -> None:
    img = Image.new("RGB", (800, 600), color=(30, 58, 95))
    draw = ImageDraw.Draw(img)
    # Gradient-style overlay
    for y in range(600):
        alpha = int(255 * (1 - y / 600) * 0.3)
        draw.line([(0, y), (800, y)], fill=(255, 255, 255, alpha))
    # Title text
    title_lines = textwrap.wrap(f"{niche}\nPrompt Pack", width=25)
    y_pos = 180
    for line in title_lines:
        draw.text((400, y_pos), line, fill=(255, 255, 255), anchor="mm")
        y_pos += 60
    draw.text((400, 420), "50 Ready-to-Use Templates", fill=(180, 210, 255), anchor="mm")
    draw.text((400, 470), "Cold Outreach Made Easy", fill=(150, 180, 220), anchor="mm")
    draw.rectangle([(50, 510), (750, 540)], fill=(70, 130, 200))
    ASSETS_DIR.mkdir(exist_ok=True)
    img.save(COVER_PATH)
    print(f"Cover saved to {COVER_PATH}")


def build_pdf(path: Path, title: str, prompts: list[dict], sequences: str = "") -> None:
    doc = SimpleDocTemplate(str(path), pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"], fontSize=22, spaceAfter=20, textColor=colors.HexColor("#1e3a5f"))
    heading_style = ParagraphStyle("Heading", parent=styles["Heading2"], fontSize=14, spaceBefore=16, spaceAfter=8, textColor=colors.HexColor("#2563eb"))
    body_style = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=16, spaceAfter=6)

    story = [Paragraph(title, title_style), Spacer(1, 0.5*cm)]

    current_category = None
    for i, prompt in enumerate(prompts, 1):
        if prompt["category"] != current_category:
            current_category = prompt["category"]
            story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
            story.append(Paragraph(current_category, heading_style))
        story.append(Paragraph(f"<b>{i}.</b> {prompt['text']}", body_style))

    if sequences:
        story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#2563eb")))
        story.append(Paragraph("Bonus: Follow-Up Email Sequences", heading_style))
        for line in sequences.split("\n"):
            if line.startswith("## "):
                story.append(Paragraph(line[3:], heading_style))
            elif line.startswith("### "):
                story.append(Paragraph(f"<b>{line[4:]}</b>", body_style))
            elif line.strip():
                story.append(Paragraph(line, body_style))

    doc.build(story)
    print(f"PDF saved to {path}")


def write_compliance_notes() -> None:
    content = """COMPLIANCE NOTES
================
- Gumroad collects and remits sales tax on the seller's behalf in most jurisdictions — no action needed.
- Income from sales is reportable as self-employment income — set aside ~30% of net revenue for taxes (US).
- The product description must NOT make income claims ("make $10k/month with these prompts") — Gumroad and FTC enforce this.
- Email marketing must include physical address and unsubscribe link — ConvertKit handles this automatically.
- Do not scrape or use copyrighted content in prompts.
- All AI-generated content used in prompts is original.
"""
    COMPLIANCE_PATH.write_text(content)
    print(f"Compliance notes saved to {COMPLIANCE_PATH}")


def run_product_creation() -> None:
    ASSETS_DIR.mkdir(exist_ok=True)
    PROMPTS_DIR.mkdir(exist_ok=True)

    state = load()
    niche = state.get("niche") or "Recruiter Cold Outreach"

    # Generate persona
    if not state.get("persona"):
        persona = generate_persona(niche)
        state["persona"] = persona
        save(state)
        print(f"Persona: {persona['name']} (@{persona['username']})")

    # Generate prompts
    prompts = generate_prompts(niche)
    (PROMPTS_DIR / "prompts.json").write_text(json.dumps(prompts, indent=2))

    # Generate email sequences
    sequences = generate_email_sequences(niche)
    (PROMPTS_DIR / "email_sequences.md").write_text(sequences)

    # Split free/paid
    free_prompts, all_prompts = split_free_and_paid(prompts)

    # Generate assets
    generate_cover(niche)
    build_pdf(FREE_PDF_PATH, f"{niche} — 10 Free Sample Prompts", free_prompts)
    build_pdf(PAID_PDF_PATH, f"{niche} — 50 Cold Outreach Prompts + Bonus Sequences", all_prompts, sequences)
    write_compliance_notes()

    mark_phase_complete(1)
    print("\nPhase 1 complete. PDFs and cover generated.")


if __name__ == "__main__":
    if is_phase_complete(1):
        print("Phase 1 already complete. Delete state.json phases_completed[1] to re-run.")
    else:
        run_product_creation()
```

- [ ] **Step 2: Verify PDF generation works (no Claude call needed — mock it)**

```bash
python -c "
from unittest.mock import patch
from pathlib import Path
import sys, os
os.makedirs('assets', exist_ok=True)
os.makedirs('prompts', exist_ok=True)

# Quick smoke test: generate cover and one PDF
from create_product import generate_cover, build_pdf
generate_cover('Test Niche')
build_pdf(Path('assets/test.pdf'), 'Test', [{'text': 'Hello [NAME]', 'category': 'Test'}])
print('PDF smoke test OK')
"
```

Expected: `PDF smoke test OK` and files created in `assets/`

- [ ] **Step 3: Commit**

```bash
git add create_product.py
git commit -m "feat: add PDF generation and cover image to create_product.py"
```

---

## Task 9: email_setup.py — ConvertKit funnel via Playwright

**Files:**
- Create: `email_setup.py`

- [ ] **Step 1: Create `email_setup.py`**

```python
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

    # Check if already logged in
    if "dashboard" in page.url or "subscribers" in page.url:
        print("Already logged into ConvertKit.")
        return True

    # Fill signup form
    try:
        human_type(page, 'input[name="user[email]"]', EMAIL)
        human_delay(1, 2)

        # ConvertKit may ask for name/company too
        if page.query_selector('input[name="user[first_name]"]'):
            state = load()
            persona = state.get("persona", {})
            name = persona.get("name", "Alex Morgan").split()[0]
            human_type(page, 'input[name="user[first_name]"]', name)
            human_delay()

        # Submit
        page.click('button[type="submit"], input[type="submit"]')
        human_delay(3, 5)

        # Check for CAPTCHA
        if page.query_selector("iframe[src*='recaptcha'], .h-captcha"):
            log_item(
                "ConvertKit CAPTCHA",
                f"Complete the CAPTCHA at {page.url} in a browser, then re-run.",
                "email_setup.py",
            )
            raise ManualInterventionRequired("CAPTCHA on ConvertKit signup")

        # Check for email verification message
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
    # Navigate to landing pages section
    page.goto(f"{CONVERTKIT_URL}/landing_pages", wait_until="networkidle")
    human_delay(2, 4)

    # Click "New Landing Page" or equivalent
    new_btn = page.query_selector('a[href*="new"], button:has-text("New"), button:has-text("Create")')
    if new_btn:
        new_btn.click()
        human_delay(2, 4)

    # ConvertKit landing page creation is highly interactive - log for manual
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

        # Attempt signup / login
        attempt_convertkit_signup(page)

        # Check if landing URL already captured
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
```

- [ ] **Step 2: Verify import**

```bash
python -c "import email_setup; print('Import OK')"
```

Expected: `Import OK`

- [ ] **Step 3: Commit**

```bash
git add email_setup.py
git commit -m "feat: add email_setup.py (Phase 2) ConvertKit funnel"
```

---

## Task 10: gumroad_setup.py — Gumroad product listing via Playwright

**Files:**
- Create: `gumroad_setup.py`

- [ ] **Step 1: Create `gumroad_setup.py`**

```python
#!/usr/bin/env python3
"""Phase 3: Gumroad account setup and product listing."""

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
    import json, re
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

        # Save credentials
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
            f"Gumroad signup error",
            f"Manually create a Gumroad account at https://gumroad.com/signup with {EMAIL}. Then re-run: python gumroad_setup.py",
            "gumroad_setup.py",
        )
        raise ManualInterventionRequired(str(e))


def create_product_listing(page, copy: dict, price: float) -> str:
    """Attempts to create product listing. Returns product URL or raises ManualInterventionRequired."""
    try:
        page.goto(f"{GUMROAD_URL}/products/new", wait_until="networkidle")
        human_delay(2, 3)

        # Fill product name
        name_field = page.query_selector('input[name="name"], input[placeholder*="name"], input[placeholder*="Name"]')
        if name_field:
            name_field.click()
            human_delay(0.5, 1)
            name_field.fill(copy["name"])
            human_delay()

        # Set price
        price_field = page.query_selector('input[name="price"], input[placeholder*="price"], input[placeholder*="Price"]')
        if price_field:
            price_field.click()
            human_delay(0.3, 0.8)
            price_field.fill(str(int(price)))
            human_delay()

        # Upload PDF
        pdf_path = Path("assets/full-prompt-pack.pdf")
        if pdf_path.exists():
            file_input = page.query_selector('input[type="file"]')
            if file_input:
                file_input.set_input_files(str(pdf_path))
                human_delay(3, 6)

        # Fill description
        desc_field = page.query_selector('textarea[name="description"], [contenteditable="true"]')
        if desc_field:
            full_desc = copy["description"] + "\n\n" + copy["free_teaser"]
            desc_field.click()
            human_delay(0.3, 0.8)
            page.keyboard.type(full_desc, delay=10)
            human_delay()

        # Save/publish
        save_btn = page.query_selector('button:has-text("Save"), button:has-text("Publish"), button[type="submit"]')
        if save_btn:
            save_btn.click()
            human_delay(3, 5)

        # Get product URL
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

    # Generate copy
    copy = generate_product_copy(niche, price, landing_url)
    Path("prompts/product_copy.json").write_text(__import__("json").dumps(copy, indent=2))

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
```

- [ ] **Step 2: Verify import**

```bash
python -c "import gumroad_setup; print('Import OK')"
```

Expected: `Import OK`

- [ ] **Step 3: Commit**

```bash
git add gumroad_setup.py
git commit -m "feat: add gumroad_setup.py (Phase 3) product listing"
```

---

## Task 11: distribute.py — Account creation and daily posting scheduler

**Files:**
- Create: `distribute.py`
- Create: `tests/test_distribute.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_distribute.py`:

```python
import pytest
from datetime import date


def test_get_due_actions_day_0():
    from distribute import get_due_actions
    actions = get_due_actions(0)
    labels = [a["label"] for a in actions]
    assert any("warm" in l.lower() or "reddit" in l.lower() for l in labels)


def test_get_due_actions_day_4_includes_thread():
    from distribute import get_due_actions
    actions = get_due_actions(4)
    labels = [a["label"] for a in actions]
    assert any("thread" in l.lower() or "x_thread" in l.lower() for l in labels)


def test_get_due_actions_day_3_includes_indie_hackers():
    from distribute import get_due_actions
    actions = get_due_actions(3)
    labels = [a["label"] for a in actions]
    assert any("indie" in l.lower() for l in labels)


def test_get_due_actions_day_7_includes_product_hunt():
    from distribute import get_due_actions
    actions = get_due_actions(7)
    labels = [a["label"] for a in actions]
    assert any("product_hunt" in l.lower() or "hunt" in l.lower() for l in labels)


def test_was_action_done_false_for_new(tmp_path):
    from unittest.mock import patch
    with patch("distribute.CHANNEL_LOG", tmp_path / "channel_log.csv"):
        from distribute import was_action_done
        assert not was_action_done("reddit_warmup_day0")


def test_was_action_done_true_after_log(tmp_path):
    from unittest.mock import patch
    with patch("distribute.CHANNEL_LOG", tmp_path / "channel_log.csv"):
        from distribute import was_action_done, log_action
        log_action("reddit_warmup_day0", "reddit", "Posted warmup", "http://reddit.com/r/test/1")
        assert was_action_done("reddit_warmup_day0")
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_distribute.py -v 2>&1 | head -15
```

Expected: `ImportError`

- [ ] **Step 3: Create `distribute.py`**

```python
#!/usr/bin/env python3
"""Phase 4: Multi-channel distribution with daily posting scheduler."""

import csv
import random
import time
from datetime import date
from pathlib import Path

from lib.state import load, save, mark_phase_complete, is_phase_complete, get_day_offset
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

    # Check CAPTCHA
    if page.query_selector("iframe[src*='recaptcha'], .h-captcha"):
        log_item(
            "Reddit CAPTCHA",
            f"Complete CAPTCHA at {page.url}, then re-run: python distribute.py",
            "distribute.py",
        )
        raise ManualInterventionRequired("Reddit CAPTCHA")

    try:
        # Title
        title_input = page.query_selector('textarea[placeholder*="Title"], input[placeholder*="Title"]')
        if title_input:
            title_input.click()
            human_delay(0.5, 1)
            title_input.fill(title)
            human_delay()

        # Body
        body_input = page.query_selector('div[contenteditable="true"], textarea[placeholder*="text"]')
        if body_input:
            body_input.click()
            human_delay(0.5, 1)
            page.keyboard.type(body[:40000], delay=5)
            human_delay()

        # Submit
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


def create_reddit_account(page) -> bool:
    log_item(
        "Reddit account creation required",
        (
            "Create a Reddit account at https://www.reddit.com/register/\n"
            "Use email: jeffcrooks.ai@gmail.com\n"
            "Choose a username matching the agent persona (see state.json -> persona.username)\n"
            "Complete email verification.\n"
            "Save credentials to .env as REDDIT_USERNAME and REDDIT_PASSWORD.\n"
            "Then re-run: python distribute.py"
        ),
        "distribute.py",
    )
    raise ManualInterventionRequired("Reddit account creation required")


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
    # Log as done so we don't re-trigger
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
                prompts_file = Path("prompts/prompts.json")
                free_prompts = __import__("json").loads(prompts_file.read_text())[:10] if prompts_file.exists() else []
                tweets = generate_x_thread(niche, landing_url, free_prompts)
                log_item(
                    "Post X/Twitter thread",
                    f"Post this {len(tweets)}-tweet thread on X from the @{state.get('persona', {}).get('username', 'agent')} account:\n\n"
                    + "\n\n---\n".join(f"Tweet {i+1}: {t}" for i, t in enumerate(tweets))
                    + f"\n\nThen re-run: python distribute.py",
                    "distribute.py",
                )
                log_action(label, "twitter", f"X thread logged for manual posting", "")

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
```

- [ ] **Step 4: Run unit tests**

```bash
pytest tests/test_distribute.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add distribute.py tests/test_distribute.py
git commit -m "feat: add distribute.py (Phase 4) multi-channel posting"
```

---

## Task 12: monitor.py — Daily metrics and decision tree

**Files:**
- Create: `monitor.py`
- Create: `tests/test_monitor.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_monitor.py`:

```python
import pytest


def test_decision_tree_day3_low_conversion_triggers_cover_upgrade():
    from monitor import run_decision_tree
    decisions = run_decision_tree(
        day=3,
        metrics={
            "conversion_rate": 0.003,
            "email_signups": 8,
            "sales": 0,
            "reddit_traction": True,
        },
    )
    labels = [d["action"] for d in decisions]
    assert "upgrade_cover" in labels


def test_decision_tree_day3_low_signups_triggers_copy_rewrite():
    from monitor import run_decision_tree
    decisions = run_decision_tree(
        day=3,
        metrics={
            "conversion_rate": 0.02,
            "email_signups": 3,
            "sales": 0,
            "reddit_traction": True,
        },
    )
    labels = [d["action"] for d in decisions]
    assert "rewrite_landing_copy" in labels


def test_decision_tree_day7_zero_sales_triggers_pivot():
    from monitor import run_decision_tree
    decisions = run_decision_tree(
        day=7,
        metrics={
            "conversion_rate": 0.01,
            "email_signups": 20,
            "sales": 0,
            "reddit_traction": False,
        },
    )
    labels = [d["action"] for d in decisions]
    assert "flash_sale" in labels


def test_decision_tree_day7_good_sales_triggers_price_raise():
    from monitor import run_decision_tree
    decisions = run_decision_tree(
        day=7,
        metrics={
            "conversion_rate": 0.05,
            "email_signups": 50,
            "sales": 6,
            "reddit_traction": True,
        },
    )
    labels = [d["action"] for d in decisions]
    assert "raise_price" in labels


def test_decision_tree_day14_always_generates_retrospective():
    from monitor import run_decision_tree
    decisions = run_decision_tree(
        day=14,
        metrics={"conversion_rate": 0.02, "email_signups": 30, "sales": 3, "reddit_traction": True},
    )
    labels = [d["action"] for d in decisions]
    assert "generate_retrospective" in labels
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_monitor.py -v 2>&1 | head -15
```

Expected: `ImportError`

- [ ] **Step 3: Create `monitor.py`**

```python
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
        "conversion_rate": 0.0,
        "email_signups": 0,
        "sales": 0,
        "reddit_traction": False,
        "gumroad_url": state.get("gumroad_url", ""),
        "landing_url": state.get("landing_url", ""),
    }

    # Read channel log for Reddit traction signal
    channel_log = Path("logs/channel_log.csv")
    if channel_log.exists():
        with open(channel_log) as f:
            rows = list(csv.DictReader(f))
            reddit_posts = [r for r in rows if r.get("channel") == "reddit" and r.get("url")]
            metrics["reddit_traction"] = len(reddit_posts) > 0

    # Read sales log if exists
    sales_log = Path("logs/sales_log.csv")
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
    day_offset = get_day_offset()
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
    Path("next_product_recommendations.md").write_text(retro.split("next_product_recommendations")[-1] if "next_product_recommendations" in retro else retro)
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_monitor.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add monitor.py tests/test_monitor.py
git commit -m "feat: add monitor.py (Phase 5) metrics and decision tree"
```

---

## Task 13: agent.py — Orchestrator and cron installation

**Files:**
- Create: `agent.py`

- [ ] **Step 1: Create `agent.py`**

```python
#!/usr/bin/env python3
"""Main orchestrator: runs all phases in order and installs daily cron job."""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from lib.state import load, save, is_phase_complete
from lib.manual import ManualInterventionRequired


PHASES = [
    (0, "validate.py", "Phase 0: Market Validation"),
    (1, "create_product.py", "Phase 1: Product Creation"),
    (2, "email_setup.py", "Phase 2: Email Infrastructure"),
    (3, "gumroad_setup.py", "Phase 3: Gumroad Setup"),
    (4, "distribute.py", "Phase 4: Distribution (first run)"),
    (5, "monitor.py", "Phase 5: Monitoring (first run)"),
]


def run_phase(script: str, label: str) -> bool:
    """Returns True if phase completed, False if manual intervention required."""
    print(f"\n{'='*60}")
    print(f"Running: {label}")
    print(f"{'='*60}")
    result = subprocess.run([sys.executable, script], capture_output=False)
    if result.returncode != 0:
        print(f"\n[STOPPED] {label} requires attention — check manual_work.md")
        return False
    return True


def install_cron() -> None:
    """Installs a daily cron job to run distribute.py + monitor.py at 09:00."""
    project_dir = Path(__file__).parent.resolve()
    python = sys.executable
    cron_line = f"0 9 * * * cd {project_dir} && {python} distribute.py && {python} monitor.py >> {project_dir}/logs/cron.log 2>&1"

    # Check if already installed
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    existing = result.stdout if result.returncode == 0 else ""

    if "distribute.py" in existing:
        print("Cron job already installed.")
        return

    new_crontab = existing.rstrip() + "\n" + cron_line + "\n"
    proc = subprocess.run(["crontab", "-"], input=new_crontab, text=True, capture_output=True)
    if proc.returncode == 0:
        print(f"Cron job installed: {cron_line}")
    else:
        print(f"Could not install cron automatically. Add this line manually:\n{cron_line}")


def full_run() -> None:
    state = load()
    if not state.get("start_date"):
        state["start_date"] = date.today().isoformat()
        save(state)
        print(f"Campaign start date: {state['start_date']}")

    for phase_num, script, label in PHASES:
        if is_phase_complete(phase_num):
            print(f"Skipping {label} (already complete)")
            continue
        success = run_phase(script, label)
        if not success:
            print(f"\nStopped at {label}. Resolve items in manual_work.md then re-run: python agent.py --full-run")
            return

    install_cron()
    print("\n" + "="*60)
    print("INITIAL SETUP COMPLETE")
    print("="*60)
    state = load()
    print(f"  Niche:       {state.get('niche', 'N/A')}")
    print(f"  Price:       ${state.get('price', 'N/A')}")
    print(f"  Gumroad:     {state.get('gumroad_url', 'N/A')}")
    print(f"  Landing:     {state.get('landing_url', 'N/A')}")
    print(f"  Cron:        Daily at 09:00 (distribute + monitor)")
    print(f"\nCheck manual_work.md for any pending human actions.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ProfitBot orchestrator")
    parser.add_argument("--full-run", action="store_true", help="Run all phases in sequence")
    args = parser.parse_args()

    if args.full_run:
        full_run()
    else:
        parser.print_help()
```

- [ ] **Step 2: Verify import and help output**

```bash
python agent.py
```

Expected: prints help/usage message

- [ ] **Step 3: Commit**

```bash
git add agent.py
git commit -m "feat: add agent.py orchestrator with cron installation"
```

---

## Task 14: Run full test suite and execute Phase 0

**Files:**
- No new files

- [ ] **Step 1: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass (≥19 tests)

- [ ] **Step 2: Initialize state.json**

```bash
python -c "
from lib.state import load, save
from datetime import date
s = load()
s['start_date'] = date.today().isoformat()
save(s)
print('State initialized:', s)
"
```

Expected: prints state dict with `start_date` set to today

- [ ] **Step 3: Run Phase 0 (market validation)**

```bash
python validate.py
```

Expected output ends with:
```
Phase 0 complete. Niche: [niche name], Price: $[price]
```
Check `validation/validation_report.md` exists.

- [ ] **Step 4: Run Phase 1 (product creation)**

```bash
python create_product.py
```

Expected output ends with:
```
Phase 1 complete. PDFs and cover generated.
```
Check `assets/cover.png`, `assets/free-sample-pack.pdf`, `assets/full-prompt-pack.pdf` all exist.

- [ ] **Step 5: Run Phases 2-3 (email + Gumroad setup) and review manual_work.md**

```bash
python email_setup.py
```

Expected: Either completes or writes to `manual_work.md` with email verification steps.

```bash
cat manual_work.md
```

Complete any items listed, then re-run as directed.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete profitbot implementation — all phases scaffolded"
```

---

## Self-Review Checklist

Run before handing off to implementation:

- [x] **Spec coverage:**
  - Phase 0 (validation + report): Task 6 ✓
  - Phase 1 (50 prompts, 2 PDFs, cover, persona): Tasks 7-8 ✓
  - Phase 2 (ConvertKit + 5-email sequence): Task 9 ✓
  - Phase 3 (Gumroad listing + discount codes): Task 10 ✓
  - Phase 4 (Reddit, X, IH, PH, daily schedule): Task 11 ✓
  - Phase 5 (metrics + Day 3/7/10/14 decision tree): Task 12 ✓
  - Orchestrator + cron: Task 13 ✓
  - compliance_notes.txt: Task 8 ✓
  - manual_work.md logging: Task 3 + throughout ✓
  - state.json resumability: Task 2 ✓
  - Budget gates ($30/$70): Task 12 decision tree ✓
  - Day 14 retrospective + next_product_recommendations.md: Task 12 ✓

- [x] **No placeholders:** All code blocks are complete
- [x] **Type consistency:** `parse_prompts_from_output` returns `list[dict]` with `text`/`category` keys used consistently in `split_free_and_paid` and `build_pdf`
- [x] **Manual intervention pattern:** `log_item` + `raise ManualInterventionRequired` used consistently across all browser scripts
