"""广州适配器测试：config 正确、委托 interlib 家族、契约缝生效。"""
import pytest

from mcp_library_search.adapters import guangzhou


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.interlib import InterlibConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 0, "page": 1, "total_pages": 1,
                "has_next": False, "books": []}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake)
    assert guangzhou.search_books("活着", page=2, limit=5) == {
        "total_results": 0, "page": 1, "total_pages": 1, "has_next": False, "books": [],
    }
    assert seen["cfg"] == InterlibConfig(
        city="guangzhou", name_cn="广州图书馆", base_url="https://opac.gzlib.org.cn"
    )
    assert seen["args"] == ("活着", 2, 5)


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "广州图书馆", "location": "", "call_number": "I313.4/5376",
             "status": "在馆", "available": True, "due_date": ""},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "无论如何都要活著",
                              "author": "朝井辽", "publisher": "采实文化",
                              "publish_year": "2021", "isbn": "978-986-507-471-5",
                              "call_number": "I313.45", "summary": "…"},
    )
    hs = guangzhou.get_holdings("3004742677", only_available=False)
    assert hs[0]["library"] == "广州图书馆"
    assert hs[0]["available"] is True
    d = guangzhou.get_book_detail("3004742677")
    assert d["title"] == "无论如何都要活著"
    assert d["book_id"] == "3004742677"


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("广州图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.interlib.search_books", boom)
    with pytest.raises(RuntimeError, match="广州图书馆"):
        guangzhou.search_books("活着")
