# Project Spec v2: Autonomous Digital Product Launch Agent

## Mission
Build, validate, launch, and scale a profitable digital product within 14 days with zero human input after initial setup. Target: >$100 net revenue in 14 days, with a durable email-list asset that continues generating revenue beyond Day 14.

## Budget Allocation ($100 total)
- **$0** — Core infrastructure (Gumroad, Reddit, ConvertKit free tier, X/Twitter, Product Hunt, Indie Hackers all free)
- **$30** — Cover art / Canva Pro one-month if conversion data shows the cover is the bottleneck (Day 4+ decision)
- **$70** — Held as ad-test reserve. Only deployed AFTER organic conversion is proven, as a promoted Reddit post or X Ads test on the winning content

## Success Criteria
- Validated product launched on Gumroad
- Email list with 25+ subscribers by Day 14
- Distribution active on minimum 4 channels (Reddit, X, Product Hunt or Indie Hackers, plus email)
- At least 1 sale within 14 days, net revenue > $100
- A repeatable system that keeps producing post-Day-14

---

## Phase 0: Validation (NEW — Day 1, before building)

**This phase did not exist in v1. Skipping it is the single biggest mistake an agent could make.**

### Step 0.1 — Market scan
Use web scraping (Playwright + requests) to gather data:

1. **Gumroad bestsellers in "Business & Money" and "Self Improvement":**
   - Scrape https://gumroad.com/discover?query=prompts and https://gumroad.com/discover?query=cold+email
   - Capture: product title, price, sales count (if visible), thumbnail style
   - Save to `validation/gumroad_competitors.csv`

2. **Reddit demand signals:**
   - Search r/Entrepreneur, r/sales, r/freelance, r/recruiting, r/realestate for posts in last 90 days containing "cold email," "outreach," "follow up," "prompts"
   - Capture upvote counts and comment counts
   - Save to `validation/reddit_demand.csv`

3. **Niche refinement:**
   - Compare engagement across niches: generic sales / recruiter outreach / real estate / B2B SaaS / agency outbound / freelancer pitching
   - Identify the niche with HIGHEST demand and LOWEST competition

### Step 0.2 — Validation decision
Generate a `validation_report.md` recommending:
- Specific niche (e.g., "Recruiter Cold Outreach Prompts" if data favors it over generic)
- Optimal price point ($7, $9, $15, $19, $29 — based on competitor median)
- Top 3 angles for messaging

**The agent must use this report to update product naming, copy, and target subreddits before proceeding.**

---

## Phase 1: Product Creation

### Step 1.1 — Generate the prompt pack content
Use Claude API to write 50 prompts in the validated niche. Structure unchanged from v1 (5 categories, 10 prompts each), but content is tuned to the validated niche.

### Step 1.2 — Create TWO products

**Product A (Free Lead Magnet):**
- 10 sample prompts (1-2 from each category)
- PDF + clean landing page
- Filename: `free-sample-pack.pdf`
- Used to capture email addresses

**Product B (Paid Product):**
- Full 50 prompts
- PDF + plain text + (NEW) bonus: 5 follow-up email sequences as separate file
- Filename: `full-prompt-pack.pdf`
- Price determined by Phase 0

### Step 1.3 — Cover image
Generate cover with Pillow (matches v1 spec). After Day 3, if conversion is below 1%, the agent may use the $30 budget to:
- Subscribe to Canva Pro for one month
- Generate higher-quality cover via Canva templates
- A/B test against original

---

## Phase 2: Email Infrastructure (NEW)

### Step 2.1 — ConvertKit account
- Navigate to https://convertkit.com/pricing (free tier supports up to 1,000 subscribers)
- Create account with anonymous email
- Store credentials in `.env`

### Step 2.2 — Build the funnel
1. Create a ConvertKit landing page with form: "Get 10 free [niche] outreach prompts"
2. Set up automated welcome email delivering the free PDF
3. Set up a 5-email sequence over 7 days that:
   - Email 1 (immediate): Free PDF + warm welcome
   - Email 2 (Day 1): Tip + soft mention of paid pack
   - Email 3 (Day 3): Case study / story + product link
   - Email 4 (Day 5): Direct pitch with discount code (`LAUNCH20` for 20% off)
   - Email 5 (Day 7): Final reminder + social proof if any
4. Capture landing page URL: `landing_url.txt`

### Step 2.3 — Discount code on Gumroad
Set up offer code `LAUNCH20` in Gumroad admin for 20% off, valid for 30 days.

---

## Phase 3: Gumroad Setup
*(Same as v1 spec, but the description copy is generated dynamically based on Phase 0 validation niche.)*

Add to product description: a line about the free sample to drive email signups for visitors who hesitate to buy:

> Not ready yet? Grab 10 free sample prompts here: [landing_url]

---

## Phase 4: Multi-Channel Distribution (EXPANDED)

### Channel 1: Reddit (per v1 spec)
Same warm-up + posting cadence. Critical: posts now drive to the **email landing page**, not directly to Gumroad. The email funnel does the selling.

### Channel 2: X/Twitter (NEW)
- Create anonymous X account
- Warm up with 3 days of genuine engagement in the niche (reply to outreach/sales accounts, share tips)
- Post a Twitter thread (10 tweets) on Day 4 sharing 5-7 of the free prompts as a value drop
- End the thread with: "Want all 50? Grab the free 10-prompt sample here: [landing_url]"
- Repost with variations every 3-4 days
- Engage with replies via Claude API

### Channel 3: Indie Hackers (NEW)
- Create account
- Post a "launch story" post on Day 3 in the Launches section
- Title format: "Launching: [Product Name] — solving [specific niche pain]"
- Body: founder story (use a synthetic but plausible persona), the problem, the solution, ask for feedback
- Include both Gumroad link and free sample link

### Channel 4: Product Hunt (NEW — Day 7)
- Create account
- Schedule launch for the highest-traffic day (Tuesday or Wednesday)
- Prepare: gallery images, tagline, first comment from "maker"
- Coordinate launch with a fresh email blast to the list asking for upvotes
- DO NOT launch on PH on Day 1 — needs the email list and social proof from earlier channels first

### Channel 5: Hacker News (Day 5-10, only if angle works)
- Submit as "Show HN" only if there's a genuinely interesting technical or process angle
- If the validated niche has a "I built X to solve Y" story, write a substantive post
- HN is high-risk, high-reward — one good post can drive 1000+ visitors

### Channel 6: Email list (the asset)
- As list grows, send the 5-email automated sequence to every new signup
- Day 10: Send a "subscriber-only" 30% off code (`SUBSCRIBER30`) to whole list
- Day 14: Send a "case study" email with any wins from buyers (real or synthesized from product feedback)

---

## Phase 5: Monitoring & Adaptation (Enhanced)

### Daily check (every 24 hours, run autonomously):

```
metrics = {
  gumroad: { visitors, sales, revenue, conversion_rate },
  email: { signups, open_rate, click_rate, signup_to_buy_rate },
  reddit: { posts_live, total_upvotes, total_comments, top_post },
  twitter: { followers, top_tweet_impressions, replies },
  indie_hackers: { upvotes, comments },
}
```

### Decision tree:

**Day 3:**
- If conversion rate < 0.5% → upgrade cover art (deploy $30 Canva budget)
- If email signups < 5 → rewrite landing page copy and headline
- If no Reddit posts gaining traction → expand to 2 new subreddits

**Day 7:**
- If sales ≥ 5: Raise price by 30%, create second related product
- If sales 1-4: Hold strategy, double down on best channel
- If sales = 0: Pivot — drop price 40%, run 24h flash sale email, deploy $70 ad budget on best Reddit post

**Day 10:**
- Run subscriber-only 30% off campaign to email list
- Submit to Product Hunt if not yet launched

**Day 14:**
- Generate full retrospective report
- Calculate net profit
- Generate v3 plan for next 14 days based on what worked

---

## Phase 6: Legal & Tax Notes (NEW)

The agent must generate a `compliance_notes.txt` with:

```
- Gumroad collects and remits sales tax on the seller's behalf in most jurisdictions — no action needed
- Income from sales is reportable as self-employment income — set aside ~30% of net revenue for taxes (US)
- The product description must NOT make income claims ("make $10k/month with these prompts") — Gumroad and FTC enforce this
- Email marketing must include physical address and unsubscribe link — ConvertKit handles this automatically
- Do not scrape or use copyrighted content in prompts
- All AI-generated content used in prompts must be original
```

---

## File Structure

```
/project
  agent.py                  # Main orchestrator
  validate.py               # Phase 0: market validation
  create_product.py         # Phase 1: PDF + assets
  email_setup.py            # Phase 2: ConvertKit funnel
  gumroad_setup.py          # Phase 3: Gumroad listing
  distribute.py             # Phase 4: multi-channel posting
  monitor.py                # Phase 5: monitoring + adaptation
  validation/
    gumroad_competitors.csv
    reddit_demand.csv
    validation_report.md
  prompts/
    [generated based on validated niche]
  assets/
    cover.png
    free-sample-pack.pdf
    full-prompt-pack.pdf
  logs/
    sales_log.csv
    channel_log.csv          # all channels in one log
    daily_report_*.txt
    decisions_log.txt        # every adaptation decision logged
  compliance_notes.txt
  .env                       # gitignored
  state.json                 # resumable state
```

---

## Dependencies

```bash
pip install playwright reportlab fpdf2 pillow anthropic python-dotenv requests pandas beautifulsoup4
playwright install chromium
```

---

## How to Run

```bash
# Full autonomous run:
python agent.py --full-run

# Or step-by-step:
python validate.py            # Phase 0 — must complete first
python create_product.py
python email_setup.py
python gumroad_setup.py
python distribute.py --start  # Begins continuous posting + monitoring
```

---

## Critical Rules for Claude Code

1. **PHASE 0 BLOCKS EVERYTHING ELSE.** Do not proceed to product creation until validation_report.md exists and recommends a niche. If validation data is inconclusive, default to "Recruiter Cold Outreach" — it has consistent demand and clear buyer intent.

2. **Every channel drives to the email landing page first**, not directly to Gumroad. The email list is the durable asset. Only the email sequence sells the product.

3. **No fake reviews. No fake testimonials. No income claims.** These will get the Gumroad account banned and may create FTC liability.

4. **Resumable execution.** state.json tracks what's complete. If the script crashes, re-running it picks up where it left off.

5. **Rate limit + human-like timing** on all browser automation: `random.uniform(2, 6)` seconds between actions, longer between posts.

6. **CAPTCHA = pause and log.** Do not retry indefinitely. Write to `manual_intervention_needed.txt` if a human is required.

7. **Budget gates:** The $30 cover budget and $70 ad budget can ONLY be spent if the decision tree explicitly authorizes them. Log every dollar spent to `spend_log.csv`.

8. **Adapt based on data, not assumptions.** The decision tree on Day 3, 7, 10 is non-negotiable — run it and act on it.

9. **Email list is the win condition.** Even if sales are low, 100+ email subscribers = a working asset for a relaunch. The agent should optimize for both sales AND list growth, not sales alone.

10. **Generate the final retrospective on Day 14.** Include: total spend, total revenue, net profit, list size, top channel, lessons, recommended next product.

---

## What "Success" Looks Like Beyond Day 14

If the system works:
- Email list of 100-500 engaged subscribers
- 1 proven product with conversion data
- Validated niche with documented competitor landscape
- Distribution playbook with channel performance data

That asset is worth far more than $100. It's a repeatable launch system. The agent should generate `next_product_recommendations.md` on Day 14 with three specific follow-up products to launch using the same playbook.

---

*Spec v2.0 — hand this entire document to Claude Code and say: "Execute this spec end to end, starting with Phase 0."*
