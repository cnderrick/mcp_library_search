import json
from pathlib import Path

from mcp_library_search.adapters import shenzhen

_FIXTURES = Path(__file__).parent / "fixtures" / "shenzhen"
_SEARCH = json.loads((_FIXTURES / "search.json").read_text(encoding="utf-8"))
_EMPTY = json.loads((_FIXTURES / "search_empty.json").read_text(encoding="utf-8"))


def test_search_maps_books(monkeypatch):
    monkeypatch.setattr(shenzhen, "_get", lambda path, params: _SEARCH)
    page = shenzhen.search_books("三体", page=1, limit=10)
    assert set(page) == {"total_results", "page", "total_pages", "has_next", "books"}
    assert page["total_results"] == _SEARCH["data"]["numFound"]  # 深圳有真实总数
    assert page["page"] == 1
    assert page["books"]
    b0 = page["books"][0]
    assert set(b0) == {"book_id", "title", "author", "publisher",
                       "publish_year", "availability_summary"}
    d0 = _SEARCH["data"]["docs"][0]
    assert b0["book_id"] == f"{d0['tablename']}:{d0['recordid']}"
    assert b0["availability_summary"] == ""


def test_search_empty(monkeypatch):
    monkeypatch.setattr(shenzhen, "_get", lambda path, params: _EMPTY)
    page = shenzhen.search_books("不存在xyz", page=1, limit=10)
    assert page["books"] == []
    assert page["total_results"] == 0
    assert page["has_next"] is False
