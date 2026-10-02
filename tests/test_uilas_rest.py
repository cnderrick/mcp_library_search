"""新版 UILAS（ILAS REST 平台）家族测试：陕西省图书馆、榆林市图书馆。

fixture 结论见 tests/fixtures/{shaanxi,yulin}/NOTES.md。解析器在 uilas_rest/
家族；两城仅 Referer 与 base_url 不同。
"""
import json
from pathlib import Path

from mcp_library_search.uilas_rest import parser

FIXTURES = Path(__file__).parent / "fixtures"


def _load(city, name):
    return json.loads((FIXTURES / city / name).read_text(encoding="utf-8"))


def test_search_shaanxi():
    r = parser.parse_search(_load("shaanxi", "search_santi.json"))
    assert r["total_results"] == 50
    assert len(r["books"]) == 10
    first = r["books"][0]
    assert set(first) == {"book_id", "title", "author", "publisher",
                          "publish_year", "isbn", "call_number", "summary",
                          "availability_summary"}
    assert first["book_id"] == "8099896"
    assert first["title"] == "三体漫画．Ⅱ，黑暗森林．7"
    assert first["publisher"] == "浙江文艺出版社"
    assert first["publish_year"] == "2025"
    assert first["isbn"] == "978-7-5339-8072-6"
    assert first["availability_summary"] == "纸本3，可借3"


def test_search_yulin():
    r = parser.parse_search(_load("yulin", "search_santi.json"))
    assert r["total_results"] == 16
    first = r["books"][0]
    assert first["book_id"] == "65654"
    assert first["title"] == "三体．Ⅱ，黑暗森林"
    assert first["publisher"] == "重庆出版社"
    assert first["publish_year"] == "2008"
    assert first["isbn"] == "978-7-5366-9396-8"
    assert first["availability_summary"] == "纸本4，可借4"


def test_empty_search():
    for city in ("shaanxi", "yulin"):
        r = parser.parse_search(_load(city, "search_empty.json"))
        assert r["total_results"] == 0
        assert r["books"] == []


def test_detail_and_holdings_shaanxi():
    r = parser.parse_detail(_load("shaanxi", "detail_santi.json"))
    book = r["book"]
    assert book["title"] == "三体漫画．Ⅱ．7：黑暗森林"
    assert book["author"] == "刘慈欣原著；蔡劲，戈闻頔，薄暮改编；草祭九日东绘；"
    assert book["isbn"] == "978-7-5339-8072-6"
    assert book["call_number"] == "J228.2"
    hs = r["holdings"]
    assert len(hs) == 3
    assert all(h["library"] == "陕西省图书馆" for h in hs)
    assert all(h["status"] == "在馆" and h["available"] is True for h in hs)
    assert hs[0]["location"] == "保存本室"


def test_detail_and_holdings_yulin():
    r = parser.parse_detail(_load("yulin", "detail_santi.json"))
    book = r["book"]
    assert book["title"] == "三体．Ⅱ：黑暗森林"
    assert book["isbn"] == "978-7-5366-9396-8"
    assert book["call_number"] == "I247.55"
    hs = r["holdings"]
    assert len(hs) == 4
    assert all(h["library"] == "榆阅空间" for h in hs)
    assert all(h["available"] is True for h in hs)


def test_status_code_mapping_is_conservative():
    assert parser.STATUS_NAMES == {"a": "采编", "b": "在馆", "c": "借出",
                                   "d": "租出", "e": "预约"}
    assert parser.AVAILABLE_CODES == {"b"}
    # 借出册不可借
    payload = {"data": {"bookDetail": {"id": "1", "name": "x"}, "inList": [
        {"status": "c", "curlib": "馆", "curlocal": "室", "callno": "C", "retudate": "2026-01-01"}]}}
    h = parser.parse_detail(payload)["holdings"][0]
    assert h["status"] == "借出" and h["available"] is False and h["due_date"] == "2026-01-01"
