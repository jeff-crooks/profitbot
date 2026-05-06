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
