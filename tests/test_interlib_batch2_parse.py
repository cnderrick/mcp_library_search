"""陕西之外第二批 Interlib 城市解析测试（2026-10-03 批量接入）。

字段侦察结论见各 tests/fixtures/<city>/NOTES.md（解析以它为准）。
两族：`html`（HTML 检索页直连，default 模板）与 `solr`（检索页被滑动验证码
拦截，改走内嵌 Solr `api/search`）。两族详情都走 `/api/book/{recno}` JSON。
"""
import json
from pathlib import Path

import pytest

from mcp_library_search.interlib import parser

FIXTURES = Path(__file__).parent / "fixtures"

HTML_CASES = [
    ("haikou", "html", 18, "900003134", "三体"),
    ("zhuzhou", "html", 222, "904226979", "三体：．，"),
    ("xiaogan", "html", 96, "4002967799", "三体"),
    ("jingmen", "html", 87, "900365539", "三体"),
    ("hunan_prov", "html", 176, "1100505", "三体Ⅱ"),
    ("fujian_prov", "html", 127, "904575263", "《三体》秘密"),
    ("yangjiang", "html", 98, "691023", "三体"),
    ("zibo", "html", 61, "900259657", "《三体》导读"),
    ("dezhou", "html", 30, "227331", "三体"),
    ("zhoukou", "html", 20, "1012204", "三体世界"),
    ("quanzhou", "html", 103, "900838527", "三体"),
    ("tongliao", "html", 11, "900041746", "三体"),
    ("heyuan", "html", 111, "5838380", "三体"),
]

SOLR_CASES = [
    ("heilongjiang", "solr", 70, "902828415", "三体．上"),
    ("changchun", "solr", 171, "2002259739", "三体：图文版"),
    ("tangshan", "solr", 101, "901232074", "三体"),
    ("baotou", "solr", 40, "2000263925", "三体：新版"),
    ("wuhai", "solr", 75, "258910", "三体"),
    ("huhehaote", "solr", 122, "2161823", "三体：新版"),
    ("chaozhou", "solr", 90, "900273066", "三体"),
]


@pytest.mark.parametrize("city,mode,total,bid,title", HTML_CASES)
def test_html_search_parses(city, mode, total, bid, title):
    html = (FIXTURES / city / "search_p1.html").read_text(encoding="utf-8")
    r = parser.parse_search(html)
    assert r["total_results"] == total
    assert r["books"], city
    first = r["books"][0]
    assert first["book_id"] == bid
    assert first["title"] == title
    empty = (FIXTURES / city / "search_empty.html").read_text(encoding="utf-8")
    e = parser.parse_search(empty)
    assert e["total_results"] == 0
    assert e["books"] == []


@pytest.mark.parametrize("city,mode,total,bid,title", SOLR_CASES)
def test_solr_search_parses(city, mode, total, bid, title):
    payload = json.loads((FIXTURES / city / "search_solr.json").read_text(encoding="utf-8"))
    r = parser.parse_solr(payload)
    assert r["total_results"] == total
    assert r["books"], city
    first = r["books"][0]
    assert first["book_id"] == bid
    assert first["title"] == title
    empty = json.loads((FIXTURES / city / "search_solr_empty.json").read_text(encoding="utf-8"))
    e = parser.parse_solr(empty)
    assert e["total_results"] == 0
    assert e["books"] == []


ALL_CASES = [(c,) for c, *_ in HTML_CASES] + [(c,) for c, *_ in SOLR_CASES]


@pytest.mark.parametrize("city", [c for (c,) in ALL_CASES])
def test_detail_api_and_holdings(city):
    d = parser.parse_detail_api(json.loads(
        (FIXTURES / city / "detail_api.json").read_text(encoding="utf-8")))
    assert d["title"], city
    assert d["isbn"] or city in ("quanzhou",), city   # quanzhou 源站 ISBN 原值异常
    hs = parser.parse_holdings(json.loads(
        (FIXTURES / city / "holding.json").read_text(encoding="utf-8")))
    for h in hs:
        assert set(h) == {"library", "location", "call_number", "status", "due_date"}
