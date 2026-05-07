
## [2026-05-07] Kit landing page required — Phase 2 (final step)
**Status:** PENDING
**What's already done via API:** Sequence "Recruiter Outreach Nurture" (ID 2748684) created with all 4 emails (Days 1/3/5/7).
**Action required:** The Kit API does not support creating landing pages — must be done in the UI (5 min):
1. Go to https://app.kit.com/landing_pages/new
2. Choose any template
3. Set headline: "Get 10 Free Recruiter Cold Outreach Prompts"
4. Set subheadline: "Boost your reply rate with these ready-to-use templates"
5. Under Incentive/Download, upload: assets/free-sample-pack.pdf
6. Connect sequence: "Recruiter Outreach Nurture"
7. Publish and copy the page URL
8. Run: `echo 'YOUR_URL' > landing_url.txt`
9. Re-run: python email_setup.py
**Re-run:** `python email_setup.py`

## [2026-05-07] Gumroad product listing — Phase 3
**Status:** PENDING
**Action required:**
1. Sign up / log in at https://gumroad.com with jeffcrooks.ai@gmail.com
2. Create a product:
   - Name: "Recruiter Cold Outreach Prompt Pack — 50 Templates + Sequences"
   - Price: $15
   - Upload: assets/full-prompt-pack.pdf
   - Description: See validation/validation_report.md for messaging angles
   - Add a line: "Get 10 free samples at [paste your Kit landing page URL]"
3. Create discount codes:
   - LAUNCH20: 20% off, expires in 30 days
   - SUBSCRIBER30: 30% off (for email subscribers)
4. After publishing, copy your product URL and run:
   `python -c "from lib.state import load, save; s=load(); s['gumroad_url']='PASTE_URL_HERE'; save(s)"`
5. Re-run: python gumroad_setup.py
**Re-run:** `python gumroad_setup.py`

## [2026-05-07 01:19] Gumroad signup error
**Action required:** Manually create a Gumroad account at https://gumroad.com/signup with jeffcrooks.ai@gmail.com. Then re-run: python gumroad_setup.py
**Re-run:** `python gumroad_setup.py`
**Status:** PENDING

## [2026-05-07 01:21] Gumroad signup error
**Action required:** Manually create a Gumroad account at https://gumroad.com/signup with jeffcrooks.ai@gmail.com. Then re-run: python gumroad_setup.py
**Re-run:** `python gumroad_setup.py`
**Status:** PENDING

## [2026-05-07 01:33] Reddit warmup post — r/humanresources
**Action required:** Post the following to https://www.reddit.com/r/humanresources/submit (no links, pure value):

Title: Honest question: what recruiter cold outreach have you actually responded to, and why?

Body:
Been thinking a lot about cold outreach lately after cleaning out my LinkedIn inbox. It's genuinely wild how much of it feels like a copy-paste job with my name swapped in.

But it also got me curious — because I HAVE responded to a handful over the years. And when I thought about why, it usually came down to a few things:

- They clearly read something specific about my background (not just my title)
- The message was short and respected my time
- They led with what was interesting about the role, not just "exciting opportunity!"
- No pressure, no fake urgency

For those of you on the TA/recruiting side — what's actually working for you right now when reaching out to passive candidates? And for HR generalists and leaders who get recruited regularly, what makes you delete something immediately vs. actually reply?

I feel like there's a real craft to cold outreach that gets buried under volume-based strategies. Curious if anyone has genuinely cracked it or if it's just a numbers game at this point.

Would love to hear real examples if you're willing to share — good and bad. No judgment here, just trying to understand what's actually moving the needle for people.

After posting, paste the post URL back and run: python3 distribute.py
**Re-run:** `python distribute.py`
**Status:** PENDING

## [2026-05-07 01:33] Reddit warmup post — r/humanresources
**Action required:** Post the following to https://www.reddit.com/r/humanresources/submit (no links, pure value):

Title: Honest question: What recruiter cold outreach actually made you stop and respond?

Body:
Been thinking a lot about recruiter cold outreach lately and how most of it lands with a thud.

We all know the formula: 'Hi [First Name], I came across your profile and think you'd be a GREAT fit for an EXCITING opportunity...' Delete.

But occasionally something cuts through. I'm curious what's actually worked - either as the sender or the receiver.

One thing I've seen make a real difference: specificity over flattery. Instead of saying someone has an 'impressive background,' calling out ONE specific thing you actually read - a project they led, a company transition they navigated, a skill that's genuinely rare. It signals you're a human, not a mail merge.

Another underrated move: being upfront about why YOU specifically reached out to THEM instead of the 50 other people with similar titles. Candidates can smell a broadcast message instantly.

For those of you on the TA side - what's one small tweak to your outreach that noticeably improved your response rates?

And for the broader HR folks here - when you've been on the receiving end of recruiter outreach (internal moves, vendor pitches, whatever), what made someone stand out in a good way?

Genuinely curious what's working out there right now.

After posting, paste the post URL back and run: python3 distribute.py
**Re-run:** `python distribute.py`
**Status:** PENDING
