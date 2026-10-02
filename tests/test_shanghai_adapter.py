from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from mcp_library_search.adapters.cn import shanghai


@pytest.fixture
def client(monkeypatch):
    c = Mock()
    monkeypatch.setattr(shanghai, "_client", c)
    return c


def _book(**kw):
    defaults = dict(
        record_id="r1",
        title="三体",
        author="刘慈欣",
        publisher="重庆出版社",
        publish_year="2022",
        call_number="I247.55/L62",
        availability_summary="多家分馆有馆藏",
        isbn="9787536692930",
        summary="文化大革命期间一次绝密工程……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def _search_result(books, **stats):
    return SimpleNamespace(
        success=True,
        error="",
        statistics={"total_results": len(books), "page": 1, "total_pages": 1,
                    "has_next": False, **stats},
        books=books,
    )


def test_search_books_maps_to_unified_model(client):
    client.search.return_value = _search_result(
        [_book(), _book(record_id="r2", title="三体Ⅱ 黑暗森林", availability_summary="")],
        total_results=347,
    )

    page = shanghai.search_books("三体")

    assert page["total_results"] == 347
    assert page["has_next"] is False
    assert page["books"][0] == {
        "book_id": "r1",
        "title": "三体",
        "author": "刘慈欣",
        "publisher": "重庆出版社",
        "publish_year": "2022",
        "availability_summary": "多家分馆有馆藏",
    }


def test_search_books_zero_total_with_results_means_unknown(client):
    """站点不再输出总条数时解析结果为 0：有结果应视为未知（null），而不是真 0。"""
    client.search.return_value = _search_result([_book()], total_results=0)

    page = shanghai.search_books("三体")

    assert page["total_results"] is None
    assert len(page["books"]) == 1


def test_search_books_zero_total_no_results_is_really_zero(client):
    client.search.return_value = _search_result([], total_results=0)

    page = shanghai.search_books("不存在的书名xyz")

    assert page["total_results"] == 0
    assert page["books"] == []


def test_search_books_failure_raises(client):
    client.search.return_value = SimpleNamespace(
        success=False, error="timeout", statistics={}, books=[]
    )
    with pytest.raises(RuntimeError, match="上海图书馆搜索失败"):
        shanghai.search_books("三体")


def test_get_holdings_defaults_to_available_only_and_sorts(client):
    client.get_holdings.return_value = [
        SimpleNamespace(library="闵行馆", location="3楼", call_number="I247.55", status="已借出", is_available=lambda: False, item_id="i1"),
        SimpleNamespace(library="徐汇馆", location="2楼", call_number="I247.55", status="可借", is_available=lambda: True, item_id=""),
        SimpleNamespace(library="静安馆", location="1楼", call_number="I247.55", status="在馆", is_available=lambda: True, item_id=""),
    ]

    out = shanghai.get_holdings("r1")

    assert [h["library"] for h in out] == ["徐汇馆", "静安馆"]  # 可借在前，同按馆名排序；已借出被过滤
    assert all(h["available"] for h in out)
    assert all(h["due_date"] == "" for h in out)
    assert out[0]["call_number"] == "I247.55"
    # 已借出的条目被过滤后不查归还时间，不发多余请求
    client.get_return_date.assert_not_called()


def test_get_holdings_fetches_due_date_for_borrowed_copies(client):
    client.get_holdings.return_value = [
        SimpleNamespace(library="闵行馆", location="3楼", call_number="I247.55", status="已借出", is_available=lambda: False, item_id="i1"),
        SimpleNamespace(library="徐汇馆", location="2楼", call_number="I247.55", status="已借出", is_available=lambda: False, item_id="i2"),
        SimpleNamespace(library="静安馆", location="1楼", call_number="I247.55", status="可借", is_available=lambda: True, item_id=""),
    ]
    client.get_return_date.side_effect = ["2026-11-05", ""]

    out = shanghai.get_holdings("r1", only_available=False)

    assert client.get_return_date.call_args_list == [call("i1"), call("i2")]
    by_library = {h["library"]: h for h in out}
    assert by_library["闵行馆"]["due_date"] == "2026-11-05"
    assert by_library["徐汇馆"]["due_date"] == ""  # 接口失败/无数据时留空串
    assert by_library["静安馆"]["due_date"] == ""  # 可借馆藏不查


def test_get_holdings_include_all_sorts_available_first(client):
    client.get_holdings.return_value = [
        SimpleNamespace(library="B馆", location="", call_number="", status="已借出", is_available=lambda: False, item_id=""),
        SimpleNamespace(library="A馆", location="", call_number="", status="可借", is_available=lambda: True, item_id=""),
    ]

    out = shanghai.get_holdings("r1", only_available=False)

    assert [h["library"] for h in out] == ["A馆", "B馆"]
    assert [h["available"] for h in out] == [True, False]
    client.get_return_date.assert_not_called()  # 已借出但无 item_id 时不查


def test_get_book_detail_maps_all_fields(client):
    client.get_book_detail.return_value = _book()

    detail = shanghai.get_book_detail("r1")

    assert detail == {
        "book_id": "r1",
        "title": "三体",
        "author": "刘慈欣",
        "publisher": "重庆出版社",
        "publish_year": "2022",
        "isbn": "9787536692930",
        "call_number": "I247.55/L62",
        "summary": "文化大革命期间一次绝密工程……",
    }


def test_get_book_detail_not_found_raises(client):
    client.get_book_detail.return_value = None
    with pytest.raises(RuntimeError, match="未找到该书的详情"):
        shanghai.get_book_detail("r-not-exist")
