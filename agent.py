#!/usr/bin/env python3
"""Main orchestrator: runs all phases in order and installs daily cron job."""

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

from lib.state import load, save, is_phase_complete


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
