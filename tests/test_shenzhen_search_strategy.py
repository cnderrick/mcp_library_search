"""深圳 search_books 的检索策略：ISBN 走专门索引，其余走任意词。"""
import json
from pathlib import Path

from mcp_library_search.adapters import shenzhen

_FIXTURES = Path(__file__).parent / "fixtures" / "shenzhen"
_SEARCH = json.loads((_FIXTURES / "search.json").read_text(encoding="utf-8"))


def test_isbn_keyword_uses_isbn_index(monkeypatch):
    calls = []

    def spy(path, params):
        calls.append(params)
        return _SEARCH

    monkeypatch.setattr(shenzhen, "_get", spy)
    shenzhen.search_books("978-7-5086-6831-4")
    assert len(calls) == 1
    assert calls[0]["v_index"] == "isbn"
    assert calls[0]["v_value"] == "978-7-5086-6831-4"
    assert calls[0]["library"] == "all"
    assert "v_tablearray" in calls[0]


def test_isbn_keyword_without_hyphens_also_uses_isbn_index(monkeypatch):
    calls = []

    def spy(path, params):
        calls.append(params)
        return _SEARCH

    monkeypatch.setattr(shenzhen, "_get", spy)
    shenzhen.search_books("9787508686314")
    assert calls[0]["v_index"] == "isbn"


def test_plain_keyword_uses_all_index(monkeypatch):
    calls = []

    def spy(path, params):
        calls.append(params)
        return _SEARCH

    monkeypatch.setattr(shenzhen, "_get", spy)
    shenzhen.search_books("活着")
    assert calls[0]["v_index"] == "all"
    assert "v_tablearray" not in calls[0]
