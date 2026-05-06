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
