"""台州适配器测试:config 正确、经模块级 _client 委托、契约缝与 base.py 结构自断言。

适配器暂不注册进 _ADAPTERS(契约测试盖不到),输出结构用 base.validate_* 自断言。
单测全部 monkeypatch interlib.client.get / interlib.get_holdings 打 fixture,不打真网。
"""
import pytest

from mcp_library_search.adapters import taizhou
from mcp_library_search.adapters.base import (
    validate_book_detail, validate_holdings, validate_search_page,
)
from mcp_library_search.interlib import InterlibConfig
from mcp_library_search.interlib import client as _family_client

SEARCH_P1 = open("tests/fixtures/taizhou/search_p1.html", encoding="utf-8").read()
SEARCH_EMPTY = open("tests/fixtures/taizhou/search_empty.html", encoding="utf-8").read()
DETAIL = open("tests/fixtures/taizhou/detail_default.html", encoding="utf-8").read()
HOLDING = open("tests/fixtures/taizhou/holding.json", encoding="utf-8").read()


def test_module_client_shape():
    # 契约测试的硬契约形态:模块级 _client,方法 search/get_holdings/get_book_detail
    assert hasattr(taizhou, "_client")
    for meth in ("search", "get_holdings", "get_book_detail"):
        assert callable(getattr(taizhou._client, meth))


def test_config_and_search_delegation(monkeypatch):
    seen = {}

    def fake_get(cfg, path, params=None):
        seen["cfg"] = cfg
        seen["path"] = path
        seen["params"] = params
        return SEARCH_P1

    monkeypatch.setattr(_family_client, "get", fake_get)
    page = taizhou.search_books("三体", page=2, limit=5)
    assert seen["cfg"] == InterlibConfig(
        city="taizhou", name_cn="台州市图书馆", base_url="https://opac.tzlib.cn:8182",
        pro2018=True,
    )
    assert seen["path"] == "/opac/search"
    # 检索参数与家族 _search_once 同款(台州实测该参数集可用)
    assert seen["params"] == {
        "q": "三体", "searchType": "standard", "searchWay0": "marc",
        "logical0": "AND", "rows": 5, "sortWay": "score",
        "sortOrder": "desc", "page": 2,
    }
    validate_search_page(page)
    assert page["total_results"] == 163
    assert page["total_pages"] == 17
    assert page["has_next"] is True
    assert page["page"] == 2
    # 家族 book_id → 契约 record_id 的映射在 _Client.search 内完成(真网冒烟曾抓到此回归),
    # 必须覆盖「非空 books」的转换
    assert len(page["books"]) == 10
    assert page["books"][0]["book_id"] == "1185362"
    assert page["books"][0]["title"] == "三体：新版"
    assert page["books"][0]["author"] == "刘慈欣著"
    assert page["books"][0]["publisher"] == "重庆出版社"
    assert page["books"][0]["publish_year"] == "2022"
    assert page["books"][0]["availability_summary"] == ""
    # 契约形态不带 isbn(内部字段不进 BookSummary)
    assert "isbn" not in page["books"][0]


def test_search_empty_page(monkeypatch):
    monkeypatch.setattr(_family_client, "get", lambda cfg, path, params=None: SEARCH_EMPTY)
    page = taizhou.search_books("azbycxq不存在xyz")
    validate_search_page(page)
    assert page["books"] == []
    assert page["total_results"] == 0
    assert page["has_next"] is False


def test_search_retries_isbn_without_hyphens(monkeypatch):
    # 镜像家族 search_raw 语义:首搜为空且关键词含连字符时去连字符重试一次
    calls = []

    def spy(cfg, path, params=None):
        calls.append(params["q"])
        return SEARCH_EMPTY if len(calls) == 1 else SEARCH_P1

    monkeypatch.setattr(_family_client, "get", spy)
    page = taizhou.search_books("978-7-229-16692-2")
    assert calls == ["978-7-229-16692-2", "9787229166922"]
    assert page["books"]


def test_holdings_go_through_family(monkeypatch):
    # 馆藏 JSON 与广州同构:走家族 get_holdings(client.get 打台州 fixture)
    seen = {}

    def fake_get(cfg, path, params=None):
        seen["path"] = path
        seen["params"] = params
        return HOLDING

    monkeypatch.setattr(_family_client, "get", fake_get)
    hs = taizhou.get_holdings("1185362", only_available=False)
    assert seen["path"] == "/opac/api/holding/1185362"
    assert seen["params"] == {"limitLibcodes": "", "isCluster": ""}
    validate_holdings(hs)
    assert len(hs) == 5
    # 样例 5 册全部借出:available False、状态原值照登、due_date 来自 loanWorkMap
    assert all(h["available"] is False for h in hs)
    assert all(h["status"] == "借出" for h in hs)
    assert all(h["library"] == "台州市图书馆" for h in hs)
    assert all(h["due_date"] for h in hs)
    # only_available=True 时全借出样例返回空列表(数据边界,不是故障)
    assert taizhou.get_holdings("1185362", only_available=True) == []


def test_holdings_sorts_available_first(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "台州市图书馆", "location": "市馆普文", "call_number": "I247.55/L597",
             "status": "借出", "available": False, "due_date": "2026-10-05"},
            {"library": "城东分馆", "location": "", "call_number": "I247.55/L597",
             "status": "在馆", "available": True, "due_date": ""},
        ],
    )
    hs = taizhou.get_holdings("1185362", only_available=False)
    validate_holdings(hs)
    assert [h["available"] for h in hs] == [True, False]  # 可借在前
    assert hs[1]["due_date"] == "2026-10-05"


def test_book_detail_parses_default_view(monkeypatch):
    seen = {}

    def fake_get(cfg, path, params=None):
        seen["path"] = path
        seen["params"] = params
        return DETAIL

    monkeypatch.setattr(_family_client, "get", fake_get)
    d = taizhou.get_book_detail("1185362")
    # 默认视图即完整标题来源,不带 view 参数(simple 视图丢副题名,见 NOTES.md)
    assert seen["path"] == "/opac/book/1185362"
    assert seen["params"] is None
    validate_book_detail(d)
    assert d["book_id"] == "1185362"
    assert d["title"] == "三体：新版"
    assert d["author"] == "刘慈欣"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2022"
    assert d["isbn"] == "978-7-229-16692-2"
    assert d["call_number"] == "I247.55"
    assert d["summary"] == ""


def test_book_detail_not_found(monkeypatch):
    monkeypatch.setattr(_family_client, "get",
                        lambda cfg, path, params=None: "<html><body></body></html>")
    with pytest.raises(RuntimeError, match="未找到"):
        taizhou.get_book_detail("9999999999")


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, path, params=None):
        raise RuntimeError("台州市图书馆请求失败：reset")

    monkeypatch.setattr(_family_client, "get", boom)
    with pytest.raises(RuntimeError, match="台州市图书馆"):
        taizhou.search_books("三体")
    with pytest.raises(RuntimeError, match="台州市图书馆"):
        taizhou.get_book_detail("1185362")
