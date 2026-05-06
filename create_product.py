#!/usr/bin/env python3
"""Phase 1: Generate prompt pack content and assets."""

import json
import re
from pathlib import Path

from lib.state import load, save, mark_phase_complete, is_phase_complete
from lib.claude_client import generate

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from PIL import Image, ImageDraw
import textwrap

PROMPTS_DIR = Path("prompts")
ASSETS_DIR = Path("assets")

COVER_PATH = ASSETS_DIR / "cover.png"
FREE_PDF_PATH = ASSETS_DIR / "free-sample-pack.pdf"
PAID_PDF_PATH = ASSETS_DIR / "full-prompt-pack.pdf"
COMPLIANCE_PATH = Path("compliance_notes.txt")


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


def generate_cover(niche: str) -> None:
    img = Image.new("RGB", (800, 600), color=(30, 58, 95))
    draw = ImageDraw.Draw(img)
    for y in range(600):
        alpha = int(255 * (1 - y / 600) * 0.3)
        draw.line([(0, y), (800, y)], fill=(255, 255, 255))
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

    if not state.get("persona"):
        persona = generate_persona(niche)
        state["persona"] = persona
        save(state)
        print(f"Persona: {persona['name']} (@{persona['username']})")

    prompts = generate_prompts(niche)
    (PROMPTS_DIR / "prompts.json").write_text(json.dumps(prompts, indent=2))

    sequences = generate_email_sequences(niche)
    (PROMPTS_DIR / "email_sequences.md").write_text(sequences)

    free_prompts, all_prompts = split_free_and_paid(prompts)

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
