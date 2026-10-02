"""汉中 fixture 解析测试：LibStar 家族 parser 直打汉中实抓页面。

字段侦察结论见 tests/fixtures/hanzhong/NOTES.md（解析以它为准）。
汉中与无锡/徐州/淮安/盐城同款图星 LibStar Find，groupCode=100121。
"""
import json
from pathlib import Path

from mcp_library_search.libstar import parser

FIXTURES = Path(__file__).parent / "fixtures" / "hanzhong"


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_search_p1_parses_books_with_stable_ids():
    r = parser.parse_search(_load("search_santi.json"))
    assert r["total_results"] == 930
    assert len(r["books"]) == 10
    first = r["books"][0]
    assert first["book_id"] == "187591"
    assert first["title"] == "三体"
    assert first["author"] == "刘慈欣 著"
    assert first["publisher"] == "重庆出版社"
    assert first["publish_year"] == "2010"
    assert first["availability_summary"] == "纸本1，可借1"
    assert first["isbn"] == "978-7-229-03093-3"


def test_empty_search_and_missing_groupcode_are_silent_zero():
    for name in ("search_empty.json", "search_santi_nogroup.json"):
        r = parser.parse_search(_load(name))
        assert r["total_results"] == 0
        assert r["books"] == []


def test_detail_parses_bibliographic_fields():
    d = parser.parse_detail(_load("detail_santi.json"))
    assert d["title"] == "三体"
    assert d["author"] == "刘慈欣 著"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2010"
    assert d["isbn"] == "978-7-229-03093-3"
    assert d["call_number"] == "I247.5"


def test_holdings_parse():
    hs = parser.parse_holdings(_load("holding_santi.json"))
    assert len(hs) == 1
    assert hs[0]["library"] == "洋县图书馆"
    assert hs[0]["location"] == "洋县图书馆-24小时书房"
    assert hs[0]["call_number"] == "I247.5/27"
    assert hs[0]["status"] == "在架" and hs[0]["available"] is True
