"""第三批 Interlib 城市解析测试（2026-10-03 批量接入）。

字段侦察结论见各 tests/fixtures/<city>/NOTES.md（解析以它为准）。
两族：`html`（HTML 检索页直连，default 模板）与 `solr`（检索页被验证码/500
拦截，改走内嵌 Solr `api/search`）。两族详情都走 `/api/book/{recno}` JSON。
"""
import json
from pathlib import Path

import pytest

from mcp_library_search.interlib import parser

FIXTURES = Path(__file__).parent / "fixtures"

HTML_CASES = [
    ("huangshi", 54, "900230756", "三体："),
    ("zunyi", 43, "55946", "三体问题"),
    ("qiandongnan", 77, "900072785", "三体"),
    ("qiannan", 20, "2000001103", "三体：典藏版"),
    ("qujing", 138, "900734735", "三体"),
    ("lincang", 31, "94243", "三体"),
    ("chuxiong", 76, "808489239", "三体"),
    ("honghe", 33, "900153170", "三体"),
    ("dehong", 52, "306603", "三体：新版"),
    ("nujiang", 9, "900089099", "三体：新版．黑暗森林"),
]

SOLR_CASES = [
    ("deqing", 55, "61754", "三体"),
    ("xishuangbanna", 18, "102821", "三体"),
]

# 源站 ISBN 原值为 null/空的记录（非适配器缺陷，数据边界）
_ISBN_EMPTY_OK = {"huangshi", "zunyi"}


@pytest.mark.parametrize("city,total,bid,title", HTML_CASES)
def test_html_search_parses(city, total, bid, title):
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


@pytest.mark.parametrize("city,total,bid,title", SOLR_CASES)
def test_solr_search_parses(city, total, bid, title):
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


@pytest.mark.parametrize("city", [c for c, *_ in HTML_CASES] + [c for c, *_ in SOLR_CASES])
def test_detail_api_and_holdings(city):
    d = parser.parse_detail_api(json.loads(
        (FIXTURES / city / "detail_api.json").read_text(encoding="utf-8")))
    assert d["title"], city
    assert d["isbn"] or city in _ISBN_EMPTY_OK, city
    hs = parser.parse_holdings(json.loads(
        (FIXTURES / city / "holding.json").read_text(encoding="utf-8")))
    for h in hs:
        assert set(h) == {"library", "location", "call_number", "status", "due_date"}


def test_solr_null_fields_are_empty_strings():
    # 德清实抓含 isbn_meta/pubdate_meta 为 null 的文档，解析须按空串处理不崩
    payload = {
        "response": {
            "numFound": 2,
            "docs": [
                {"id": "1", "title_meta": "三体", "author_meta": None,
                 "publisher_meta": None, "pubdate_meta": None, "isbn_meta": None},
                {"id": "2", "title_meta": "三体Ⅱ", "author_meta": "刘慈欣",
                 "publisher_meta": "重庆出版社", "pubdate_meta": "2008", "isbn_meta": "978-7-5366-9293-0"},
            ],
        }
    }
    r = parser.parse_solr(payload)
    assert r["total_results"] == 2
    assert r["books"][0] == {"book_id": "1", "title": "三体", "author": "",
                             "publisher": "", "publish_year": "",
                             "availability_summary": "", "isbn": ""}
