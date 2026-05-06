import json
import pytest
from unittest.mock import patch, MagicMock


def test_parse_prompts_from_claude_output():
    from create_product import parse_prompts_from_output
    sample = """## Category 1: Opening Lines
1. Prompt one text here.
2. Prompt two text here.
## Category 2: Follow-Up
3. Prompt three text here."""
    result = parse_prompts_from_output(sample)
    assert len(result) >= 2
    assert all("text" in p for p in result)
    assert all("category" in p for p in result)


def test_parse_prompts_handles_numbered_list():
    from create_product import parse_prompts_from_output
    sample = "1. First prompt.\n2. Second prompt.\n3. Third prompt."
    result = parse_prompts_from_output(sample)
    assert len(result) == 3


def test_split_free_and_paid():
    from create_product import split_free_and_paid
    prompts = [{"text": f"Prompt {i}", "category": f"Cat {i % 5}"} for i in range(50)]
    free, paid = split_free_and_paid(prompts)
    assert len(free) == 10
    assert len(paid) == 50


def test_generate_persona_returns_required_keys():
    from create_product import generate_persona
    with patch("create_product.generate") as mock_gen:
        mock_gen.return_value = json.dumps({
            "name": "Alex Morgan",
            "username": "alexmorgan_sales",
            "bio": "Sales coach helping recruiters.",
            "backstory": "Former recruiter turned coach.",
            "location": "Austin, TX",
        })
        persona = generate_persona("Recruiter Cold Outreach")
        assert "name" in persona
        assert "username" in persona
        assert "bio" in persona
