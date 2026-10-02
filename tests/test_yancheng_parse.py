"""盐城 fixture 解析测试：LibStar 家族 parser 直打盐城实抓页面。

字段侦察结论见 tests/fixtures/yancheng/NOTES.md（解析以它为准）。
盐城与无锡/徐州/淮安同款图星 LibStar Find，解析器抽在 libstar/ 家族，零 quirk。
"""
import json
from pathlib import Path

from mcp_library_search.libstar import parser

FIXTURES = Path(__file__).parent / "fixtures" / "yancheng"


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_search_p1_parses_books_with_stable_ids():
    r = parser.parse_search(_load("search_santi.json"))
    assert r["total_results"] == 857
    assert len(r["books"]) == 10
    first = r["books"][0]
    assert first["book_id"] == "671583"
    assert first["title"] == "三体 : 图像小说"
    assert first["author"] == "原著刘慈欣,吴青松"
    assert first["publisher"] == "译林出版社"
    # publishYear 带月份 2025.1 → 取四位年份
    assert first["publish_year"] == "2025"
    assert first["availability_summary"] == "纸本3，可借3"
    assert first["isbn"] == "978-7-5753-0280-7"


def test_search_empty_result():
    r = parser.parse_search(_load("search_empty.json"))
    assert r["total_results"] == 0
    assert r["books"] == []


def test_missing_groupcode_is_silent_zero_not_error():
    r = parser.parse_search(_load("search_santi_nogroup.json"))
    assert r["total_results"] == 0
    assert r["books"] == []


def test_detail_parses_bibliographic_fields():
    d = parser.parse_detail(_load("detail_santi.json"))
    assert d["title"] == "三体:图像小说"
    assert d["author"] == "原著刘慈欣 编绘吴青松, 三体宇宙"
    assert d["publisher"] == "译林出版社"
    assert d["publish_year"] == "2025"
    assert d["isbn"] == "978-7-5753-0280-7"
    assert d["call_number"] == "J228.2"
    assert d["summary"].startswith("本书改编自科幻巨著《三体》")


def test_holdings_single_library_mixed_states():
    hs = parser.parse_holdings(_load("holding_santi.json"))
    assert len(hs) == 3
    assert all(h["library"] == "盐城市图书馆" for h in hs)
    assert sum(1 for h in hs if h["available"]) == 1
    on_shelf = [h for h in hs if h["available"]]
    assert on_shelf[0]["status"] == "在架"
    assert on_shelf[0]["location"] == "社科室"
    assert on_shelf[0]["call_number"] == "J228.2/4768"
    assert on_shelf[0]["due_date"] == ""
    borrowed = [h for h in hs if not h["available"]]
    assert {h["due_date"] for h in borrowed} == {"2025-11-23", "2026-01-10"}
