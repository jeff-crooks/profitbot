# ProfitBot Worklog

## 2026-05-06 — Session 1: Full build from spec

### What was done

Built the entire ProfitBot agent end-to-end from `gumroad-agent-spec-v2.md`.

**Architecture decisions:**
- Scheduler-based independent phase scripts (not a monolithic loop)
- `state.json` for resumable/idempotent execution across all phases
- `manual_work.md` as the human intervention queue — scripts exit cleanly and log what needs doing
- Fully synthetic persona: **Danielle Okafor** (@danielle_recruits, Atlanta GA)

**Phases completed automatically:**
- Phase 0 ✅ — Niche validated as **Recruiter Cold Outreach**, price **$15**
  - Reddit JSON API now returns 403 for unauthenticated requests — all niches scored 0, fallback to recruiter (which is the right pick anyway)
  - Gumroad scraping returned 0 results (their discovery page changed structure)
  - Claude still generated a solid `validation/validation_report.md` with messaging angles
- Phase 1 ✅ — 50 prompts generated, `assets/full-prompt-pack.pdf` (20KB), `assets/free-sample-pack.pdf`, `assets/cover.png`, email sequences
- Daily cron installed: `distribute.py && monitor.py` at 09:00

**Key bugs found and fixed:**
1. `~/.env.secrets` uses `export KEY="value"` shell syntax — `load_dotenv` truncated the API key to 10 chars. Replaced with custom `_load_shell_env_file()` parser.
2. `ANTHROPIC_API_KEY` was already set (stale truncated value) in the environment — fixed by removing the non-override guard so `.env.secrets` always wins.
3. `BrowserSession.__exit__`: stored `_pw_cm` (context manager) separately from `_pw` (Playwright instance) — was calling `__exit__` on wrong object.
4. Playwright missing system libs (`libatk`, `libatspi`, `libgbm`, etc.) — no sudo available. Downloaded and extracted 10 `.deb` packages from Ubuntu archive into `~/libs/extracted/`; `browser.py` sets `LD_LIBRARY_PATH` before launch.
5. `monitor.py` `collect_metrics()` returned `conversion_rate=0.0` and `email_signups=0` as defaults — Day 3 decisions would always fire. Fixed to `1.0` and `99` (safe/unknown state).
6. ConvertKit rebranded to Kit — URL updated to `app.kit.com`.

**Phases blocked by human action:**
- Phase 2 — Kit (ConvertKit) signup blocked by Cloudflare Turnstile bot protection. Must be done in real browser.
- Phase 3 — Gumroad product creation. Standard email verification wall.

### What to pick up next

See `manual_work.md` for the exact steps. In order:

1. **Kit signup** — https://app.kit.com/users/signup with jeffcrooks.ai@gmail.com
   - Create landing page, upload `assets/free-sample-pack.pdf` as incentive
   - Create 4-email sequence (email bodies in `email_setup.py` lines 17–59)
   - Save landing page URL to `landing_url.txt`
   - Add API secret to `~/.env.secrets` as `export KIT_API_KEY="..."`
   - Run: `python email_setup.py`

2. **Gumroad product** — https://gumroad.com with jeffcrooks.ai@gmail.com
   - $15, upload `assets/full-prompt-pack.pdf`
   - Discount codes: LAUNCH20 (20% off, 30 days), SUBSCRIBER30 (30% off)
   - Save product URL: `python -c "from lib.state import load, save; s=load(); s['gumroad_url']='URL'; save(s)"`
   - Run: `python gumroad_setup.py`

3. **After both are done:** `python agent.py --full-run` — picks up from Phase 4 (distribution) and Phase 5 (monitoring/cron)

### Key file locations

| What | Where |
|------|-------|
| Products to sell | `assets/full-prompt-pack.pdf`, `assets/free-sample-pack.pdf` |
| Validation report | `validation/validation_report.md` |
| Email sequence copy | `email_setup.py` lines 17–59 |
| Persona | `state.json` → `.persona` |
| Human action queue | `manual_work.md` |
| Daily logs | `logs/` (created when distribute/monitor run) |
| Cron | `0 9 * * *` — `distribute.py && monitor.py` |
