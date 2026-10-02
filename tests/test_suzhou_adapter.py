"""苏州双源适配器测试：模块级 _client 契约缝 + 双源归并/容错/路由。

覆盖：两源配置、ISBN 复合 book_id、源级容错、馆藏成员路由、详情优先级成员。
fixture 结论见 tests/fixtures/suzhou/NOTES.md。
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import suzhou
from mcp_library_search.interlib import client as il_client

_FIX = Path(__file__).parent / "fixtures" / "suzhou"
_SZ_SEARCH = (_FIX / "sz" / "search_p1.html").read_text(encoding="utf-8")
_SZ_DETAIL = (_FIX / "sz" / "detail.html").read_text(encoding="utf-8")
_SZ_HOLDING = (_FIX / "sz" / "holding.json").read_text(encoding="utf-8")
_SIP_SEARCH = (_FIX / "sip" / "search_p1.html").read_text(encoding="utf-8")
_SIP_DETAIL = (_FIX / "sip" / "detail.html").read_text(encoding="utf-8")
_SIP_HOLDING = (_FIX / "sip" / "holding.json").read_text(encoding="utf-8")


# ---------- 双源配置 ----------


def test_source_configs():
    assert suzhou._SOURCE_PRIORITY == ("SZ", "SIP")
    assert suzhou._SOURCES["SZ"].cfg == suzhou.InterlibConfig(
        city="sz", name_cn="苏州图书馆", base_url="https://reader.szlib.com")
    assert suzhou._SOURCES["SIP"].cfg == suzhou.InterlibConfig(
        city="sip", name_cn="苏州工业园区图书馆", base_url="http://opac.sdll.cn:8088")


# ---------- ISBN 归并与复合 book_id ----------


def _b(prefix, rid, isbn="", title="三体"):
    return suzhou._Book(record_id=f"{prefix}:{rid}", title=title, author="刘慈欣",
                        publisher="重庆出版社", publish_year="2008",
                        availability_summary="", isbn=isbn)


def test_merge_same_isbn_composite_id():
    merged = suzhou._merge_books(
        {"SZ": [_b("SZ", "100", "978-7-5366-9293-0")],
         "SIP": [_b("SIP", "200", "9787536692930")]})
    assert len(merged) == 1
    assert merged[0].record_id == "SZ:100+SIP:200"
    assert merged[0].title == "三体"


def test_merge_no_isbn_stays_single():
    merged = suzhou._merge_books(
        {"SZ": [_b("SZ", "A", ""), _b("SZ", "C", "9787536692930")],
         "SIP": [_b("SIP", "D", "123")]})
    assert {m.record_id for m in merged} == {"SZ:A", "SZ:C", "SIP:D"}


def test_split_book_id():
    assert suzhou._split_book_id("SIP:2+SZ:1") == [("SZ", "1"), ("SIP", "2")]
    assert suzhou._split_book_id("SZ:1") == [("SZ", "1")]
    with pytest.raises(RuntimeError, match="book_id"):
        suzhou._split_book_id("100100")
    with pytest.raises(RuntimeError, match="book_id"):
        suzhou._split_book_id("AH:1")


# ---------- _Client.search：双源合并、total、容错 ----------


def _dispatch(mapping):
    calls = []

    def fake_get(cfg, path, params=None, timeout=20):
        calls.append((cfg.city, path, params))
        return mapping[(cfg.city, path)]

    return fake_get, calls


def test_search_merges_two_sources(monkeypatch):
    fake, calls = _dispatch({("sz", "/opac/search"): _SZ_SEARCH,
                             ("sip", "/opac/search"): _SIP_SEARCH})
    monkeypatch.setattr(il_client, "get", fake)
    r = suzhou._Client().search("三体")
    assert r.success is True
    assert r.statistics["total_results"] == 232 + 98
    assert r.statistics["total_pages"] == 24       # 各源最大值
    assert r.statistics["has_next"] is True
    ids = {b.record_id for b in r.books}
    assert all(i.startswith(("SZ:", "SIP:")) for i in ids)
    assert {c[0] for c in calls} == {"sz", "sip"}


def test_search_survives_one_source_failure(monkeypatch):
    def fake_get(cfg, path, params=None, timeout=20):
        if cfg.city == "sip":
            raise RuntimeError("苏州工业园区图书馆请求失败：timed out")
        return _SZ_SEARCH

    monkeypatch.setattr(il_client, "get", fake_get)
    r = suzhou._Client().search("三体")
    assert r.success is True
    assert r.statistics["total_results"] == 232
    assert r.books and all(b.record_id.startswith("SZ:") for b in r.books)


def test_search_both_fail_raises(monkeypatch):
    def fake_get(cfg, path, params=None, timeout=20):
        raise RuntimeError(f"{cfg.name_cn}请求失败：connection reset")

    monkeypatch.setattr(il_client, "get", fake_get)
    with pytest.raises(RuntimeError) as ei:
        suzhou._Client().search("三体")
    assert "苏州" in str(ei.value)
    assert "苏州图书馆" in str(ei.value) and "苏州工业园区图书馆" in str(ei.value)


# ---------- _Client.get_holdings：成员路由 ----------


def test_holdings_composite_aggregates_and_routes(monkeypatch):
    # 用真实馆藏 JSON，但 book_id 用 SZ/SIP 前缀路由
    fake, calls = _dispatch({
        ("sz", "/opac/api/holding/1006489923"): _SZ_HOLDING,
        ("sip", "/opac/api/holding/872372"): _SIP_HOLDING,
    })
    monkeypatch.setattr(il_client, "get", fake)
    hs = suzhou._Client().get_holdings("SZ:1006489923+SIP:872372")
    assert len(hs) == 8 + 4
    flags = [h.available for h in hs]
    assert flags == sorted(flags, reverse=True)     # 可借在前
    assert {c[0] for c in calls} == {"sz", "sip"}


def test_holdings_attached_source_failure_skipped(monkeypatch):
    def fake_get(cfg, path, params=None, timeout=20):
        if cfg.city == "sip":
            raise RuntimeError("苏州工业园区图书馆请求失败：reset")
        return _SZ_HOLDING

    monkeypatch.setattr(il_client, "get", fake_get)
    hs = suzhou._Client().get_holdings("SZ:1006489923+SIP:872372")
    assert len(hs) == 8


def test_holdings_primary_source_failure_raises(monkeypatch):
    def fake_get(cfg, path, params=None, timeout=20):
        if cfg.city == "sz":
            raise RuntimeError("苏州图书馆请求失败：reset")
        return _SIP_HOLDING

    monkeypatch.setattr(il_client, "get", fake_get)
    with pytest.raises(RuntimeError, match="苏州图书馆"):
        suzhou._Client().get_holdings("SZ:1006489923+SIP:872372")


# ---------- _Client.get_book_detail：优先级成员 ----------


def test_detail_uses_priority_member(monkeypatch):
    fake, calls = _dispatch({
        ("sz", "/opac/book/1006489923"): _SZ_DETAIL,
        ("sip", "/opac/book/872372"): _SIP_DETAIL,
    })
    monkeypatch.setattr(il_client, "get", fake)
    b = suzhou._Client().get_book_detail("SZ:1006489923+SIP:872372")
    assert [c[1] for c in calls] == ["/opac/book/1006489923"]
    assert b.record_id == "SZ:1006489923+SIP:872372"
    assert b.title == "三体：图像小说"
    assert b.isbn == "978-7-5753-0280-7"


# ---------- 契约缝合约（镜像 test_adapter_contract.py 的注入形态） ----------


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(suzhou, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="SZ:1006429505", title="三体：典藏版", author="刘慈欣著",
        publisher="重庆出版社", publish_year="2016", availability_summary="有馆藏",
        isbn="978-7-229-10060-5", call_number="I247.55/1121", summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_search_books_contract(monkeypatch):
    result = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="SIP:872372", title="一说《三体》")],
    )
    _patch_client(monkeypatch, search=result)
    page = suzhou.search_books("三体")
    assert page["books"][0]["book_id"] == "SZ:1006429505"
    assert page["books"][1]["book_id"] == "SIP:872372"
    base.validate_search_page(page)


def test_get_holdings_contract(monkeypatch):
    holdings = [
        SimpleNamespace(library="苏图", location="北馆书库", call_number="I247.55/1121",
                        status="在馆", is_available=lambda: True, item_id="", due_date=""),
        SimpleNamespace(library="工业园区图书馆", location="网借书库（联创产业园）",
                        call_number="N49/681", status="借出", is_available=lambda: False,
                        item_id="item-1", due_date="2026-10-21"),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-10-21")
    hs = suzhou.get_holdings("SZ:1+SIP:2", only_available=False)
    base.validate_holdings(hs)
    assert [h["available"] for h in hs] == [True, False]
    client.get_return_date.assert_called_once_with("item-1")
    assert hs[1]["due_date"] == "2026-10-21"


def test_get_book_detail_contract(monkeypatch):
    _patch_client(monkeypatch, get_book_detail=_book())
    d = suzhou.get_book_detail("SZ:1006429505")
    base.validate_book_detail(d)
    assert d["book_id"] == "SZ:1006429505"
    assert d["title"] == "三体：典藏版"
