"""苏州双源 fixture 解析测试：家族 parser 直打 SZ/SIP 实抓页面。

字段侦察结论见 tests/fixtures/suzhou/NOTES.md（解析以它为准）。
两源均为 Interlib 默认（非 pro2018）模板，家族 parser 零改动。
"""
import json
from pathlib import Path

from mcp_library_search.interlib.parser import (
    is_available_status,
    parse_detail,
    parse_holdings,
    parse_search,
)

FIXTURES = Path(__file__).parent / "fixtures" / "suzhou"


def _load(source, name):
    p = FIXTURES / source / name
    if name.endswith(".json"):
        return json.loads(p.read_text(encoding="utf-8"))
    return p.read_text(encoding="utf-8")


def test_sz_fingerprint_and_search():
    index = _load("sz", "index.html")
    assert "interlib" in index.lower()
    assert "图创" in index
    assert "苏州图书馆" in index
    r = parse_search(_load("sz", "search_p1.html"))
    assert r["total_results"] == 232
    assert r["total_pages"] == 24
    assert r["has_next"] is True
    first = r["books"][0]
    assert first["book_id"] == "1006429505"
    assert first["title"] == "三体：典藏版"
    assert first["publisher"] == "重庆出版社"
    assert first["isbn"] == "978-7-229-10060-5"
    assert _load("sz", "search_p1.html").count('class="bookmeta"') == 10


def test_sz_detail_and_holdings():
    d = parse_detail(_load("sz", "detail.html"))
    assert d["title"] == "三体：图像小说"
    assert d["author"] == "刘慈欣"
    assert d["isbn"] == "978-7-5753-0280-7"
    assert d["call_number"] == "I247.55"
    hs = parse_holdings(_load("sz", "holding.json"))
    assert len(hs) == 8
    assert {h["library"] for h in hs} == {"苏图"}
    avail = [h for h in hs if is_available_status(h["status"])]
    assert len(avail) == 2
    assert any(h["location"] == "渭塘分馆" for h in hs)


def test_sip_fingerprint_and_search():
    index = _load("sip", "index.html")
    assert "interlib" in index.lower()
    assert "苏州工业园区图书馆" in index
    r = parse_search(_load("sip", "search_p1.html"))
    assert r["total_results"] == 98
    assert r["total_pages"] == 10
    first = r["books"][0]
    assert first["book_id"] == "872372"
    assert first["title"] == "一说《三体》：《三体》中的前沿科学漫谈"
    assert first["author"] == "王一"
    assert first["publisher"] == "人民邮电出版社"
    assert first["isbn"] == "978-7-115-60591-7"


def test_sip_detail_and_holdings():
    d = parse_detail(_load("sip", "detail.html"))
    assert d["title"] == "一说《三体》：《三体》中的前沿科学漫谈"
    assert d["author"] == "王一"
    assert d["isbn"] == "978-7-115-60591-7"
    assert d["call_number"] == "I207.425"
    hs = parse_holdings(_load("sip", "holding.json"))
    assert len(hs) == 4
    assert {h["library"] for h in hs} == {"工业园区图书馆"}
    loaned = [h for h in hs if h["status"] == "借出"]
    assert len(loaned) == 3
    assert {h["due_date"] for h in loaned} == {"2026-10-21", "2025-06-28", "2026-10-05"}


def test_empty_search_both_sources():
    for source in ("sz", "sip"):
        r = parse_search(_load(source, "search_empty.html"))
        assert r["books"] == []
        assert r["total_results"] == 0
        assert r["has_next"] is False
        assert r["total_pages"] == 1
