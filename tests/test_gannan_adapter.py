"""甘南州图书馆适配器测试（离线）：Config 正确性、经模块级 _client 的委托、
错误包装、馆藏过滤排序、_client 契约缝，以及馆别过滤（借甘肃省图 iLink 实例）。
"""
import urllib.parse
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_library_search.adapters.base import (
    validate_book_detail, validate_holdings, validate_search_page)
from mcp_library_search.adapters.cn import gannan
from mcp_library_search.ilink import client as ilink_client

_FIX = Path(__file__).parent / "fixtures"
_ENTRY = (_FIX / "gansu_prov" / "entry_raw.html").read_text(encoding="utf-8")
_SEARCH = (_FIX / "gannan" / "search.html").read_text(encoding="utf-8")


def test_config():
    c = gannan._CONFIG
    assert c.city == "gannan"
    assert c.name_cn == "甘南州图书馆"
    assert c.base_url == "http://search.gslib.com.cn"   # 借甘肃省图 iLink 实例
    assert c.library_code == "甘南馆"
    assert c.throttle >= 4.0


def test_module_level_client_seam():
    assert isinstance(gannan._client, gannan._Client)


def test_search_delegates_through_client(monkeypatch):
    stub = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 3, "page": 1, "total_pages": 1, "has_next": False},
        books=[SimpleNamespace(record_id="1551269:三体 刘慈欣著",
                               title="三体 刘慈欣著", author="刘慈欣 著",
                               publisher="", publish_year="",
                               availability_summary="1 馆藏于 甘南图书馆 在 甘南文学")],
    )
    monkeypatch.setattr(gannan, "_client", SimpleNamespace(search=lambda **kw: stub))
    page = gannan.search_books("三体")
    assert page["books"][0]["book_id"] == "1551269:三体 刘慈欣著"
    validate_search_page(page)


def test_search_error_wrapped(monkeypatch):
    stub = SimpleNamespace(success=False, error="会话失效")
    monkeypatch.setattr(gannan, "_client", SimpleNamespace(search=lambda **kw: stub))
    with pytest.raises(RuntimeError, match="甘南州图书馆"):
        gannan.search_books("三体")


def test_holdings_delegation_filter_and_sort(monkeypatch):
    hs = [
        gannan._Holding(library="甘南馆", call_number="A", status="馆藏于", available=False),
        gannan._Holding(library="甘南馆", call_number="B", status="在架上", available=True),
    ]
    monkeypatch.setattr(gannan, "_client", SimpleNamespace(get_holdings=lambda book_id: hs))
    all_h = gannan.get_holdings("1551269:t", only_available=False)
    assert [h["available"] for h in all_h] == [True, False]
    validate_holdings(all_h)
    assert len(gannan.get_holdings("1551269:t", only_available=True)) == 1


def test_detail_delegates(monkeypatch):
    b = SimpleNamespace(title="三体 刘慈欣著", author="刘慈欣 著", publisher="重庆出版社",
                        publish_year="2010", isbn="9787536692930",
                        call_number="(GNT)I247.5/3084.1", summary="")
    monkeypatch.setattr(gannan, "_client", SimpleNamespace(get_book_detail=lambda book_id: b))
    d = gannan.get_book_detail("1551269:t")
    assert d["isbn"] == "9787536692930"
    validate_book_detail(d)


def test_offline_library_code_and_token_flow(monkeypatch):
    calls = []

    def spy(cfg, req, timeout=25):
        calls.append((req.full_url, req.data))
        return _ENTRY if req.data is None else _SEARCH

    monkeypatch.setattr(ilink_client, "_open", spy)
    page = gannan.search_books("三体")
    q = [urllib.parse.parse_qs(c[1].decode()) for c in calls if c[1] is not None][0]
    assert q["library"] == ["甘南馆"]
    assert page["total_results"] == 3
