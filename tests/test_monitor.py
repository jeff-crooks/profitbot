import pytest


def test_decision_tree_day3_low_conversion_triggers_cover_upgrade():
    from monitor import run_decision_tree
    decisions = run_decision_tree(
        day=3,
        metrics={
            "conversion_rate": 0.003,
            "email_signups": 8,
            "sales": 0,
            "reddit_traction": True,
        },
    )
    labels = [d["action"] for d in decisions]
    assert "upgrade_cover" in labels


def test_decision_tree_day3_low_signups_triggers_copy_rewrite():
    from monitor import run_decision_tree
    decisions = run_decision_tree(
        day=3,
        metrics={
            "conversion_rate": 0.02,
            "email_signups": 3,
            "sales": 0,
            "reddit_traction": True,
        },
    )
    labels = [d["action"] for d in decisions]
    assert "rewrite_landing_copy" in labels


def test_decision_tree_day7_zero_sales_triggers_pivot():
    from monitor import run_decision_tree
    decisions = run_decision_tree(
        day=7,
        metrics={
            "conversion_rate": 0.01,
            "email_signups": 20,
            "sales": 0,
            "reddit_traction": False,
        },
    )
    labels = [d["action"] for d in decisions]
    assert "flash_sale" in labels


def test_decision_tree_day7_good_sales_triggers_price_raise():
    from monitor import run_decision_tree
    decisions = run_decision_tree(
        day=7,
        metrics={
            "conversion_rate": 0.05,
            "email_signups": 50,
            "sales": 6,
            "reddit_traction": True,
        },
    )
    labels = [d["action"] for d in decisions]
    assert "raise_price" in labels


def test_decision_tree_day14_always_generates_retrospective():
    from monitor import run_decision_tree
    decisions = run_decision_tree(
        day=14,
        metrics={"conversion_rate": 0.02, "email_signups": 30, "sales": 3, "reddit_traction": True},
    )
    labels = [d["action"] for d in decisions]
    assert "generate_retrospective" in labels
