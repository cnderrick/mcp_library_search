"""丽江 fixture 解析测试：Interlib 家族 parser 直打丽江实抓页面。

字段侦察结论见 tests/fixtures/lijiang/NOTES.md（解析以它为准）。
丽江与广州同款默认（非 pro2018）模板，详情走 /api/book JSON（api_detail）。
"""
import json
from pathlib import Path

from mcp_library_search.interlib.parser import (
    is_available_status, parse_detail_api, parse_holdings, parse_search,
)

FIXTURES = Path(__file__).parent / "fixtures" / "lijiang"

INDEX = (FIXTURES / "index.html").read_text(encoding="utf-8")
SEARCH_P1 = (FIXTURES / "search_p1.html").read_text(encoding="utf-8")
SEARCH_EMPTY = (FIXTURES / "search_empty.html").read_text(encoding="utf-8")
DETAIL = json.loads((FIXTURES / "detail_api.json").read_text(encoding="utf-8"))
HOLDING = json.loads((FIXTURES / "holding.json").read_text(encoding="utf-8"))


def test_interlib_fingerprint():
    assert "interlib" in INDEX.lower()
    assert "图创" in INDEX
    assert "丽江市图书馆" in INDEX
    assert "<title>检索系统</title>" in INDEX


def test_search_parses():
    r = parse_search(SEARCH_P1)
    assert r["total_results"] == 80
    assert r["total_pages"] == 8
    assert r["has_next"] is True
    assert len(r["books"]) == 10
    first = r["books"][0]
    assert first["book_id"] == "257370"
    assert first["title"] == "三体：典藏版"
    assert first["publisher"] == "重庆出版社"
    assert first["isbn"] == "978-7-229-10060-5"


def test_empty_search():
    r = parse_search(SEARCH_EMPTY)
    assert r["books"] == []
    assert r["total_results"] == 0


def test_detail_api():
    d = parse_detail_api(DETAIL)
    assert d["title"] == "三体：典藏版"
    assert d["author"] == "刘慈欣著"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2016"
    assert d["isbn"] == "978-7-229-10060-5"
    assert d["call_number"] == "I247.55"


def test_holdings():
    hs = parse_holdings(HOLDING)
    assert len(hs) == 1
    h = hs[0]
    assert h["library"] == "古城区图书馆"
    assert h["location"] == "古城区外借室"
    assert h["call_number"] == "I247.5/0287"
    assert h["status"] == "在馆" and is_available_status(h["status"]) is True
    assert h["due_date"] == ""
