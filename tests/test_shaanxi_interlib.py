"""陕西四市（Interlib 家族）fixture 解析测试：西安/咸阳/宝鸡/安康。

字段侦察结论见 tests/fixtures/{xian,xianyang,baoji,ankang}/NOTES.md（解析以它为准）。
西安与安康是 pro2018 模板；四城详情都走 `/api/book/{recno}` JSON（`api_detail=True`，
安康 HTML 详情页被源站截断）。西安应用上下文是 `/opac3`。
"""
import json
from pathlib import Path

import pytest

from mcp_library_search.interlib import parser

FIXTURES = Path(__file__).parent / "fixtures"

# (city, pro2018, first_id, first_title, first_publisher, first_year)
CASES = [
    ("xian", True, "902511096", "三体．上", "中国盲文出版社", "2017"),
    ("xianyang", False, "730219", "三体：新版", "重庆出版社", "2022"),
    ("baoji", False, "900858229", "三体：新版", "重庆出版社", "2022"),
    ("ankang", True, "1983176", "三体：新版", "重庆出版社", "2022"),
]


def _load(city, name):
    p = FIXTURES / city / name
    if name.endswith(".json"):
        return json.loads(p.read_text(encoding="utf-8"))
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("city,pro2018,bid,title,publisher,year", CASES)
def test_search_parses_with_family_parser(city, pro2018, bid, title, publisher, year):
    parse = parser.parse_search_pro2018 if pro2018 else parser.parse_search
    r = parse(_load(city, "search_p1.html"))
    assert len(r["books"]) == 10
    assert r["total_results"] > 0
    first = r["books"][0]
    assert first["book_id"] == bid
    assert first["title"] == title
    assert first["publisher"] == publisher
    assert first["publish_year"] == year
    # 首批全部有稳定数字 id
    assert all(b["book_id"].isdigit() for b in r["books"])


@pytest.mark.parametrize("city,pro2018,bid,title,publisher,year", CASES)
def test_empty_search(city, pro2018, bid, title, publisher, year):
    parse = parser.parse_search_pro2018 if pro2018 else parser.parse_search
    r = parse(_load(city, "search_empty.html"))
    assert r["books"] == []
    assert r["total_results"] == 0
    assert r["total_pages"] == 1


@pytest.mark.parametrize("city,pro2018,bid,title,publisher,year", CASES)
def test_detail_via_api(city, pro2018, bid, title, publisher, year):
    """四城详情走 `/api/book/{recno}` JSON（安康 HTML 详情页被源站截断）。"""
    d = parser.parse_detail_api(_load(city, "detail_api.json"))
    assert d["title"]
    assert d["isbn"]
    assert d["call_number"]
    assert set(d) == {"title", "author", "publisher", "publish_year",
                      "isbn", "call_number", "summary"}


def test_holdings_parse_maps_codes():
    for city, *_ in CASES:
        hs = parser.parse_holdings(_load(city, "holding.json"))
        assert hs, city
        for h in hs:
            assert set(h) == {"library", "location", "call_number", "status", "due_date"}
            assert h["library"]


def test_ankang_borrowed_has_due_date_and_is_unavailable():
    hs = parser.parse_holdings(_load("ankang", "holding.json"))
    borrowed = [h for h in hs if h["status"] == "借出"]
    assert borrowed and borrowed[0]["due_date"] == "2026-10-07"
    assert not parser.is_available_status("借出")
