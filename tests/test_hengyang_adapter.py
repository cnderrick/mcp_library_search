"""衡阳适配器测试：会话流程、题名检索 quirk、分页、详情/馆藏、契约缝、fixture 解析。

衡阳是 InDigLib 独立实现（照 chongqing.py 复刻），与非共享家族。mock 点为
模块级 `_open(req, timeout)`，按顺序或按 URL 返回 fixture 文本。
fixture 结论见 tests/fixtures/hengyang/NOTES.md。
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import hengyang

_FIX = Path(__file__).parent / "fixtures" / "hengyang"
_SESSION = (_FIX / "index.html").read_text(encoding="utf-8")
_SEARCH = (_FIX / "search.html").read_text(encoding="utf-8")
_SEARCH_EMPTY = (_FIX / "search_empty.html").read_text(encoding="utf-8")
_DETAIL = (_FIX / "detail.html").read_text(encoding="utf-8")
_ASSET = (_FIX / "get_asset.json").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_session_state(monkeypatch):
    """会话与节流计时是模块级状态，逐测试复位。"""
    hengyang._reset_session()


def _mock_open(monkeypatch, pages):
    """按顺序返回 pages；记录 (full_url, data)。"""
    calls = []
    seq = iter(pages)

    def spy(req, timeout=20):
        calls.append((req.full_url, req.data))
        return next(seq)

    monkeypatch.setattr(hengyang, "_open", spy)
    return calls


def _mock_open_by_url(monkeypatch, asset_response):
    """按 URL 路由：GetAsset → asset_response；SearchIndex → 会话页；其余 → 详情页。"""
    calls = []

    def spy(req, timeout=20):
        calls.append((req.full_url, req.data))
        if "GetAsset.action" in req.full_url:
            return asset_response
        if "SearchIndex" in req.full_url:
            return _SESSION
        return _DETAIL

    monkeypatch.setattr(hengyang, "_open", spy)
    return calls


# ---------- 检索 ----------


def test_search_session_then_posts_title(monkeypatch):
    calls = _mock_open(monkeypatch, [_SESSION, _SEARCH])
    page = hengyang.search_books("三体")
    # 会话入口为本城 advanced 页（旧版 simple 入口存在但不稳定）
    assert calls[0][0].endswith("SearchIndex!advanced.action")
    assert calls[0][1] is None  # 会话页是 GET
    assert "OpacMarcSearchSolr!simpleSearch.action" in calls[1][0]
    body = calls[1][1].decode()
    assert "select1=title" in body  # 本城默认题名检索 quirk
    assert "text1=" in body
    assert page["books"][0]["book_id"] == "i_sgbiblios:19673"
    assert page["books"][0]["title"] == "三体"
    assert page["total_pages"] == 6
    assert page["total_results"] is None  # 源站只给总页数，不给总条数
    assert page["has_next"] is True


def test_isbn_keyword_uses_isbn_select1(monkeypatch):
    calls = _mock_open(monkeypatch, [_SESSION, _SEARCH])
    hengyang.search_books("9787536692930")
    assert "select1=isbn" in calls[1][1].decode()


def test_page_two_uses_get_pageno(monkeypatch):
    calls = _mock_open(monkeypatch, [_SESSION, _SEARCH])
    page = hengyang.search_books("三体", page=2)
    assert "pageNo=2" in calls[1][0]
    assert calls[1][1] is None  # 翻页走 GET（结果页分页链接形态）
    assert page["has_next"] is True
    assert page["total_pages"] == 6


def test_empty_search_zero_pages(monkeypatch):
    _mock_open(monkeypatch, [_SESSION, _SEARCH_EMPTY])
    page = hengyang.search_books("zzzqqqxyz")
    assert page["total_pages"] == 0
    assert page["has_next"] is False
    assert page["books"] == []


# ---------- 详情与馆藏 ----------


def test_get_book_detail_fields(monkeypatch):
    _mock_open(monkeypatch, [_SESSION, _DETAIL])
    d = hengyang.get_book_detail("i_sgbiblios:19673")
    assert d["title"] == "三体"
    assert d["author"] == "刘慈欣著"
    assert d["isbn"] == "9787536692930"
    # 详情页不显示索书号（检索条目有、详情页无），如实返回空
    assert d["call_number"] == ""
    assert d["summary"] == ""


def test_get_holdings_per_item_from_getasset(monkeypatch):
    calls = _mock_open_by_url(monkeypatch, _ASSET)
    hs = hengyang.get_holdings("i_sgbiblios:19673", only_available=False)
    # 首请求即根路径 GetAsset（无需会话），POST 参数齐全
    assert "InDigLib/GetAsset.action" in calls[0][0]
    assert "frontV2" not in calls[0][0]
    body = calls[0][1].decode()
    assert "metatables=i_sgbiblios" in body
    assert "metaids=19673" in body and "type=map" in body
    assert len(hs) == 2
    assert all(h["library"] == "石鼓区图书馆" for h in hs)
    assert all(h["location"] == "石鼓_图书借阅室" for h in hs)
    assert all(h["call_number"] == "I247.55/14" for h in hs)
    assert {h["status"] for h in hs} == {"入藏", "普通借出"}
    # 统一保守口径：无明确「可借」状态词，「入藏」也判 False
    assert all(h["available"] is False for h in hs)
    loaned = [h for h in hs if h["status"] == "普通借出"]
    assert len(loaned) == 1 and loaned[0]["due_date"] == "2025-10-02"
    assert all(h["due_date"] == "" for h in hs if h["status"] == "入藏")


def test_get_holdings_default_only_available_is_empty(monkeypatch):
    # 统一保守口径的直接后果：only_available=True 恒为空，调用方需用 False 看全部原值
    _mock_open_by_url(monkeypatch, _ASSET)
    assert hengyang.get_holdings("i_sgbiblios:19673") == []


def test_get_holdings_blocked_getasset_falls_back_to_library_level(monkeypatch):
    # 根路径若哪天也被拦（返回登录页 HTML 而非 JSON）→ 回退详情页馆名级（旧行为）
    calls = _mock_open_by_url(monkeypatch, "<html>登录</html>")
    hs = hengyang.get_holdings("i_sgbiblios:19673", only_available=False)
    assert hs and hs[0]["library"] == "石鼓区图书馆"
    assert hs[0]["status"] == "" and hs[0]["available"] is False
    urls = [u for u, _ in calls]
    assert any("SearchIndex" in u for u in urls)
    assert any("BookDetail.action" in u for u in urls)


def test_bad_book_id_raises(monkeypatch):
    with pytest.raises(RuntimeError, match="book_id"):
        hengyang.get_book_detail("19673")


# ---------- 契约缝自断言（镜像 tests/test_adapter_contract.py 的注入形态） ----------


def test_contract_seam(monkeypatch):
    client = Mock()
    client.search.return_value = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": None, "page": 1, "total_pages": 6, "has_next": True},
        books=[SimpleNamespace(record_id="i_sgbiblios:19673", title="三体",
                               author="刘慈欣著", publisher="", publish_year="",
                               availability_summary="", isbn="9787536692930",
                               call_number="", summary="")]
    )
    client.get_holdings.return_value = [
        SimpleNamespace(library="石鼓区图书馆", location="石鼓_图书借阅室",
                        call_number="I247.55/14", status="普通借出",
                        is_available=lambda: False, item_id="", due_date="2025-10-02"),
    ]
    client.get_book_detail.return_value = SimpleNamespace(
        record_id="i_sgbiblios:19673", title="三体", author="刘慈欣著",
        publisher="", publish_year="", isbn="9787536692930",
        call_number="", summary="")
    monkeypatch.setattr(hengyang, "_client", client)
    page = hengyang.search_books("三体")
    assert page["books"][0]["book_id"] == "i_sgbiblios:19673"
    base.validate_search_page(page)
    hs = hengyang.get_holdings("i_sgbiblios:19673", only_available=False)
    assert hs[0]["due_date"] == "2025-10-02"
    base.validate_holdings(hs)
    base.validate_book_detail(hengyang.get_book_detail("i_sgbiblios:19673"))


# ---------- fixture 解析 ----------


def test_fixtures_parse():
    search = hengyang._parse_search(_SEARCH)
    assert search["total_pages"] == 6
    assert search["books"][0].record_id == "i_sgbiblios:19673"
    assert search["books"][0].title == "三体"
    assert search["books"][0].author == "刘慈欣著"
    assert hengyang._parse_search(_SEARCH_EMPTY)["total_pages"] == 0
    p2 = hengyang._parse_search((_FIX / "search_p2.html").read_text(encoding="utf-8"))
    assert p2["total_pages"] == 6
    assert p2["books"][0].record_id != search["books"][0].record_id
    detail = hengyang._parse_detail(_DETAIL)
    assert detail["title"] == "三体"
    assert detail["author"] == "刘慈欣著"
    assert detail["isbn"] == "9787536692930"
    assets = hengyang._parse_assets(_ASSET)
    assert len(assets) == 2
    assert assets[0].library == "石鼓区图书馆"
    assert all(a.available is False for a in assets)


def test_select1_routing():
    assert hengyang._select1("三体") == "title"
    assert hengyang._select1("9787536692930") == "isbn"
    assert hengyang._select1("978-7-5366-9293-0") == "isbn"
