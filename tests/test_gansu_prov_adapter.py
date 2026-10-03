"""甘肃省图书馆适配器测试（离线）：Config 正确性、经模块级 _client 的委托、
错误包装、馆藏过滤排序、_client 契约缝，以及走真实家族 client 的馆别/会话流。
"""
import urllib.parse
from pathlib import Path
from types import SimpleNamespace

import pytest

from mcp_library_search.adapters.base import (
    validate_book_detail, validate_holdings, validate_search_page)
from mcp_library_search.adapters.cn import gansu_prov
from mcp_library_search.ilink import client as ilink_client

_FIX = Path(__file__).parent / "fixtures" / "gansu_prov"
_ENTRY = (_FIX / "entry_raw.html").read_text(encoding="utf-8")
_SEARCH = (_FIX / "search_prov.html").read_text(encoding="utf-8")


def test_config():
    c = gansu_prov._CONFIG
    assert c.city == "gansu_prov"
    assert c.name_cn == "甘肃省图书馆"
    assert c.base_url == "http://search.gslib.com.cn"
    assert c.library_code == "甘肃馆"                 # 仅查省馆馆别
    assert c.entry_path == "/uhtbin/cgisirsi/x/x/0/49/"
    assert c.page_size == 20
    assert c.throttle >= 4.0                          # 会话敏感，≥4 秒/host


def test_module_level_client_seam():
    assert isinstance(gansu_prov._client, gansu_prov._Client)


def test_search_delegates_through_client(monkeypatch):
    stub = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 1, "page": 1, "total_pages": 1, "has_next": False},
        books=[SimpleNamespace(record_id="1644695:2016文化观察选粹 专著 金浪主编",
                               title="2016文化观察选粹 专著 金浪主编",
                               author="金浪 (文学) 主编", publisher="", publish_year="2017",
                               availability_summary="1 馆藏于 甘肃省馆 在 社科闭架")],
    )
    monkeypatch.setattr(gansu_prov, "_client", SimpleNamespace(search=lambda **kw: stub))
    page = gansu_prov.search_books("三体")
    assert page["books"][0]["book_id"] == "1644695:2016文化观察选粹 专著 金浪主编"
    assert page["total_results"] == 1
    validate_search_page(page)


def test_search_error_wrapped(monkeypatch):
    stub = SimpleNamespace(success=False, error="会话失效")
    monkeypatch.setattr(gansu_prov, "_client", SimpleNamespace(search=lambda **kw: stub))
    with pytest.raises(RuntimeError, match="甘肃省图书馆"):
        gansu_prov.search_books("三体")


def test_holdings_delegation_filter_and_sort(monkeypatch):
    hs = [
        gansu_prov._Holding(library="甘肃省馆", call_number="A", status="馆藏于", available=False),
        gansu_prov._Holding(library="甘肃省馆", call_number="B", status="在架上", available=True),
    ]
    monkeypatch.setattr(gansu_prov, "_client", SimpleNamespace(get_holdings=lambda book_id: hs))
    all_h = gansu_prov.get_holdings("1644695:t", only_available=False)
    assert [h["available"] for h in all_h] == [True, False]   # 可借的排前
    validate_holdings(all_h)
    only = gansu_prov.get_holdings("1644695:t", only_available=True)
    assert len(only) == 1 and only[0]["available"] is True


def test_detail_delegates(monkeypatch):
    b = SimpleNamespace(title="t", author="a", publisher="p", publish_year="2017",
                        isbn="9787537850797", call_number="G122-53/25/:2016", summary="")
    monkeypatch.setattr(gansu_prov, "_client", SimpleNamespace(get_book_detail=lambda book_id: b))
    d = gansu_prov.get_book_detail("1644695:t")
    assert d["book_id"] == "1644695:t" and d["isbn"] == "9787537850797"
    validate_book_detail(d)


def test_offline_library_code_and_token_flow(monkeypatch):
    calls = []

    def spy(cfg, req, timeout=25):
        calls.append((req.full_url, req.data))
        return _ENTRY if req.data is None else _SEARCH

    monkeypatch.setattr(ilink_client, "_open", spy)
    page = gansu_prov.search_books("三体")
    q = [urllib.parse.parse_qs(c[1].decode()) for c in calls if c[1] is not None][0]
    assert q["library"] == ["甘肃馆"]
    assert page["total_results"] == 101
