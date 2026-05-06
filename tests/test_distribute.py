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
