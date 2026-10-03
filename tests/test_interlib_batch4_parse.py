"""第四批 Interlib 城市解析测试（2026-10-03 批量接入）。

字段侦察结论见各 tests/fixtures/<city>/NOTES.md（解析以它为准）。
`html`（HTML 检索页直连）与 `solr`（检索页被验证码拦，改走内嵌 Solr）两族
详情都走 `/api/book/{recno}` JSON；乐山另有验证码墙（见 test_leshan_captcha.py）。
"""
import json
from pathlib import Path

import pytest

from mcp_library_search.interlib import parser

FIXTURES = Path(__file__).parent / "fixtures"

HTML_CASES = [
    ("wuhan", 263, 14, "1900722937", "三体"),
    ("daqing", 29, 2, "273681", "《三体》中的物理学"),
]

SOLR_CASES = [
    ("taiyuan", 179, "2002435398", "三体"),
]

DETAIL_CITIES = ["wuhan", "daqing", "taiyuan", "leshan"]


@pytest.mark.parametrize("city,total,pages,bid,title", HTML_CASES)
def test_html_search_parses(city, total, pages, bid, title):
    html = (FIXTURES / city / "search_p1.html").read_text(encoding="utf-8")
    r = parser.parse_search(html)
    assert r["total_results"] == total
    assert r["total_pages"] == pages
    assert r["books"], city
    first = r["books"][0]
    assert first["book_id"] == bid
    assert first["title"] == title
    empty = (FIXTURES / city / "search_empty.html").read_text(encoding="utf-8")
    e = parser.parse_search(empty)
    assert e["total_results"] == 0
    assert e["books"] == []


@pytest.mark.parametrize("city,total,bid,title", SOLR_CASES)
def test_solr_search_parses(city, total, bid, title):
    payload = json.loads((FIXTURES / city / "search_solr.json").read_text(encoding="utf-8"))
    r = parser.parse_solr(payload)
    assert r["total_results"] == total
    assert r["books"][0]["book_id"] == bid
    assert r["books"][0]["title"] == title
    empty = json.loads((FIXTURES / city / "search_solr_empty.json").read_text(encoding="utf-8"))
    e = parser.parse_solr(empty)
    assert e["total_results"] == 0
    assert e["books"] == []


@pytest.mark.parametrize("city", DETAIL_CITIES)
def test_detail_api_and_holdings(city):
    d = parser.parse_detail_api(json.loads(
        (FIXTURES / city / "detail_api.json").read_text(encoding="utf-8")))
    assert d["title"], city
    hs = parser.parse_holdings(json.loads(
        (FIXTURES / city / "holding.json").read_text(encoding="utf-8")))
    for h in hs:
        assert set(h) == {"library", "location", "call_number", "status", "due_date"}
