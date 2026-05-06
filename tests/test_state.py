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
