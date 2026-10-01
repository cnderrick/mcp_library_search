import pytest

from mcp_library_search import adapters, server


def test_search_books_delegates_with_default_city(monkeypatch):
    calls = []

    def fake(city, keyword, page=1, limit=20):
        calls.append((city, keyword, page, limit))
        return {"books": []}

    monkeypatch.setattr(adapters, "search_books", fake)
    assert server.search_books("三体") == {"books": []}
    assert calls == [("shanghai", "三体", 1, 20)]


def test_search_books_wraps_errors(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("上游挂了")

    monkeypatch.setattr(adapters, "search_books", boom)
    with pytest.raises(RuntimeError, match="搜索失败"):
        server.search_books("三体")


def test_find_book_availability_delegates_and_wraps(monkeypatch):
    monkeypatch.setattr(
        adapters, "get_holdings", lambda city, rid, only_available=True: [{"library": "徐汇馆"}]
    )
    assert server.find_book_availability("r1") == [{"library": "徐汇馆"}]

    def boom(*args, **kwargs):
        raise RuntimeError("x")

    monkeypatch.setattr(adapters, "get_holdings", boom)
    with pytest.raises(RuntimeError, match="查询馆藏失败"):
        server.find_book_availability("r1")


def test_get_book_detail_delegates_and_wraps(monkeypatch):
    monkeypatch.setattr(adapters, "get_book_detail", lambda city, rid: {"book_id": "r1"})
    assert server.get_book_detail("r1") == {"book_id": "r1"}

    def boom(*args, **kwargs):
        raise RuntimeError("x")

    monkeypatch.setattr(adapters, "get_book_detail", boom)
    with pytest.raises(RuntimeError, match="查询图书详情失败"):
        server.get_book_detail("r1")


def test_unsupported_city_gets_clear_message():
    with pytest.raises(RuntimeError, match="暂未接入：beijing"):
        adapters.search_books("beijing", "三体")
