import json
import pytest
from unittest.mock import patch, MagicMock


def test_parse_reddit_results_extracts_posts():
    from validate import parse_reddit_results
    sample = {
        "data": {
            "children": [
                {"data": {"title": "Cold email tips", "score": 150, "num_comments": 30}},
                {"data": {"title": "Outreach for recruiters", "score": 80, "num_comments": 12}},
            ]
        }
    }
    results = parse_reddit_results(sample)
    assert len(results) == 2
    assert results[0]["score"] == 150
    assert results[0]["title"] == "Cold email tips"


def test_parse_reddit_results_empty():
    from validate import parse_reddit_results
    assert parse_reddit_results({"data": {"children": []}}) == []


def test_score_niche_aggregates_correctly():
    from validate import score_niche
    posts = [
        {"score": 100, "num_comments": 20},
        {"score": 50, "num_comments": 10},
    ]
    result = score_niche(posts)
    assert result["total_score"] == 150
    assert result["total_comments"] == 30
    assert result["post_count"] == 2


def test_select_best_niche_picks_highest_score():
    from validate import select_best_niche
    scores = {
        "recruiter": {"total_score": 500, "total_comments": 80, "post_count": 5},
        "generic": {"total_score": 200, "total_comments": 30, "post_count": 3},
        "real_estate": {"total_score": 100, "total_comments": 10, "post_count": 2},
    }
    assert select_best_niche(scores) == "recruiter"


def test_select_best_niche_falls_back_on_empty():
    from validate import select_best_niche
    assert select_best_niche({}) == "recruiter"
