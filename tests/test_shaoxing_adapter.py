"""绍兴适配器测试:config 正确、经模块级 _client 委托、pro2018 本地解析、
引文块责任者兜底、联合层书目空馆藏边界、契约缝与 base.py 结构自断言。

单测全部 monkeypatch interlib.client.get / interlib.get_holdings 打 fixture,
不打真网。fixture 结论以 tests/fixtures/shaoxing/NOTES.md 为准;
家族 parser 不兼容 pro2018 的硬证据另见 tests/test_shaoxing_recon.py。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters.cn import shaoxing
from mcp_library_search.adapters.base import (
    validate_book_detail, validate_holdings, validate_search_page,
)
from mcp_library_search.interlib import InterlibConfig
from mcp_library_search.interlib import client as _family_client

_FIXTURES = Path(__file__).parent / "fixtures" / "shaoxing"
SEARCH_P1 = (_FIXTURES / "search_p1.html").read_text(encoding="utf-8")
SEARCH_LUXUN = (_FIXTURES / "search_luxun_p1.html").read_text(encoding="utf-8")
SEARCH_EMPTY = (_FIXTURES / "search_empty.html").read_text(encoding="utf-8")
DETAIL = (_FIXTURES / "detail.html").read_text(encoding="utf-8")
DETAIL_879551 = (_FIXTURES / "detail_879551.html").read_text(encoding="utf-8")
HOLDING = (_FIXTURES / "holding_879551.json").read_text(encoding="utf-8")
HOLDING_EMPTY = (_FIXTURES / "holding.json").read_text(encoding="utf-8")


def test_module_client_shape():
    # 契约测试的硬契约形态:模块级 _client,方法 search/get_holdings/get_book_detail
    assert hasattr(shaoxing, "_client")
    for meth in ("search", "get_holdings", "get_book_detail"):
        assert callable(getattr(shaoxing._client, meth))


def test_config_and_search_delegation(monkeypatch):
    seen = {}

    def fake_get(cfg, path, params=None):
        seen["cfg"] = cfg
        seen["path"] = path
        seen["params"] = params
        return SEARCH_P1

    monkeypatch.setattr(_family_client, "get", fake_get)
    page = shaoxing.search_books("三体", page=2, limit=5)
    assert seen["cfg"] == InterlibConfig(
        city="shaoxing", name_cn="绍兴图书馆", base_url="https://opac.sxlib.com",
        pro2018=True, pro2018_cite_author=True,
    )
    assert seen["path"] == "/opac/search"
    # 检索参数与家族 _search_once 同款(绍兴侦察实抓即用此参数集)
    assert seen["params"] == {
        "q": "三体", "searchType": "standard", "searchWay0": "marc",
        "logical0": "AND", "rows": 5, "sortWay": "score",
        "sortOrder": "desc", "page": 2,
    }
    validate_search_page(page)
    # 总数在 schResNumIn、分页在 JS 配置(totalPage: 21)
    assert page["total_results"] == 203
    assert page["total_pages"] == 21
    assert page["has_next"] is True
    assert page["page"] == 2
    assert len(page["books"]) == 10
    b0 = page["books"][0]
    assert b0["book_id"] == "1227282"
    assert b0["title"] == "三体"
    assert b0["author"] == "刘慈欣著"
    assert b0["publisher"] == "重庆出版社"
    assert b0["publish_year"] == "2010"  # 「,2010.11」裸文本取 4 位年
    assert b0["availability_summary"] == ""
    # 契约形态不带 isbn(内部字段不进 BookSummary)
    assert "isbn" not in b0


def test_search_luxun_page(monkeypatch):
    # 第二份检索 fixture(鲁迅,numFound 8523):解析器对不同结果集稳定
    monkeypatch.setattr(_family_client, "get", lambda cfg, path, params=None: SEARCH_LUXUN)
    page = shaoxing.search_books("鲁迅")
    validate_search_page(page)
    assert page["total_results"] == 8523
    assert len(page["books"]) == 10
    assert page["books"][0]["book_id"] == "60599"
    assert page["books"][0]["title"] == "鲁迅．下"  # 原生句点照登


def test_search_empty_page(monkeypatch):
    monkeypatch.setattr(_family_client, "get", lambda cfg, path, params=None: SEARCH_EMPTY)
    page = shaoxing.search_books("azbycxq不存在xyz")
    validate_search_page(page)
    assert page["books"] == []
    assert page["total_results"] == 0  # notFindFt 空结果锚点,源站明说没有
    assert page["has_next"] is False


def test_search_retries_isbn_without_hyphens(monkeypatch):
    # 镜像家族 search_raw 语义:首搜为空且关键词含连字符时去连字符重试一次
    calls = []

    def spy(cfg, path, params=None):
        calls.append(params["q"])
        return SEARCH_EMPTY if len(calls) == 1 else SEARCH_P1

    monkeypatch.setattr(_family_client, "get", spy)
    page = shaoxing.search_books("978-7-229-03093-3")
    assert calls == ["978-7-229-03093-3", "9787229030933"]
    assert page["books"]


def test_holdings_go_through_family(monkeypatch):
    # 馆藏 JSON 与广州同构、家族参数形态实测可用:走家族 get_holdings
    seen = {}

    def fake_get(cfg, path, params=None):
        seen["path"] = path
        seen["params"] = params
        return HOLDING

    monkeypatch.setattr(_family_client, "get", fake_get)
    hs = shaoxing.get_holdings("879551", only_available=False)
    assert seen["path"] == "/opac/api/holding/879551"
    assert seen["params"] == {"limitLibcodes": "", "isCluster": ""}
    validate_holdings(hs)
    assert len(hs) == 3
    # 3 册全部在馆(上虞图书馆,localMap 翻译:储藏外借×2、资料×1)
    assert all(h["available"] and h["status"] == "在馆" for h in hs)
    assert all(h["library"] == "上虞图书馆" for h in hs)
    assert {h["location"] for h in hs} == {"储藏外借", "资料"}
    assert all(h["call_number"] == "K825.6/102" for h in hs)
    assert all(h["due_date"] == "" for h in hs)


def test_holdings_union_level_entry_empty(monkeypatch):
    # 联合层书目(《三体》1227282)无本地单册:holdingList 空 → 空列表,
    # 数据边界照实返回,不是故障(NOTES.md「holding 取数条件」实证)
    monkeypatch.setattr(_family_client, "get", lambda cfg, path, params=None: HOLDING_EMPTY)
    assert shaoxing.get_holdings("1227282", only_available=False) == []
    assert shaoxing.get_holdings("1227282", only_available=True) == []


def test_holdings_sorts_available_first(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "绍兴图书馆", "location": "外借", "call_number": "I247.5/L59",
             "status": "借出", "available": False, "due_date": "2026-10-05"},
            {"library": "上虞图书馆", "location": "储藏外借", "call_number": "I247.5/L59",
             "status": "在馆", "available": True, "due_date": ""},
        ],
    )
    hs = shaoxing.get_holdings("879551", only_available=False)
    validate_holdings(hs)
    assert [h["available"] for h in hs] == [True, False]  # 可借在前
    assert hs[1]["due_date"] == "2026-10-05"


def test_book_detail_citation_author_fallback(monkeypatch):
    # 绍兴详情页无「主要责任者」标签行 → 责任者取引文块首段(原值照登含「著」)
    seen = {}

    def fake_get(cfg, path, params=None):
        seen["path"] = path
        seen["params"] = params
        return DETAIL

    monkeypatch.setattr(_family_client, "get", fake_get)
    d = shaoxing.get_book_detail("1227282")
    assert seen["path"] == "/opac/book/1227282"
    assert seen["params"] is None
    validate_book_detail(d)
    assert d["book_id"] == "1227282"
    assert d["title"] == "三体"
    assert d["author"] == "刘慈欣著"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2010"
    assert d["isbn"] == "978-7-229-03093-3"
    assert d["call_number"] == ""  # 该记录中图分类法值空(只有「版次：」),照实
    assert d["summary"] == ""      # 无「内容提要」标签行(数据边界)


def test_book_detail_second_record(monkeypatch):
    # 第二份详情 fixture(《鲁迅：1881--1936》):引文兜底「编」字样、有分类号
    monkeypatch.setattr(_family_client, "get", lambda cfg, path, params=None: DETAIL_879551)
    d = shaoxing.get_book_detail("879551")
    validate_book_detail(d)
    assert d["title"] == "鲁迅：1881--1936"
    assert d["author"] == "北京鲁迅博物馆编"
    assert d["publisher"] == "文物出版社"
    assert d["publish_year"] == "1977"
    assert d["isbn"] == ""  # 该记录无 ISBN 值,照实
    assert d["call_number"] == "K825.6"
    assert d["summary"] == ""


def test_book_detail_not_found(monkeypatch):
    monkeypatch.setattr(_family_client, "get",
                        lambda cfg, path, params=None: "<html><body></body></html>")
    with pytest.raises(RuntimeError, match="未找到"):
        shaoxing.get_book_detail("9999999999")


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, path, params=None):
        raise RuntimeError("绍兴图书馆请求失败：reset")

    monkeypatch.setattr(_family_client, "get", boom)
    with pytest.raises(RuntimeError, match="绍兴图书馆"):
        shaoxing.search_books("三体")
    with pytest.raises(RuntimeError, match="绍兴图书馆"):
        shaoxing.get_book_detail("1227282")
