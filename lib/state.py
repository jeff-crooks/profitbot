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
