"""Smoke tests for the shared LLM client JSON extraction helper."""

import pytest

from app.services.llm_client import _extract_json_object


def test_extract_json_object_plain():
    data = _extract_json_object('{"key": "value", "count": 1}')
    assert data == {"key": "value", "count": 1}


def test_extract_json_object_from_markdown_fence():
    raw = 'Here is the result:\n```json\n{"sentiment_lean": "positive"}\n```'
    data = _extract_json_object(raw)
    assert data["sentiment_lean"] == "positive"


def test_extract_json_object_rejects_non_object():
    with pytest.raises(ValueError):
        _extract_json_object("[1, 2, 3]")
