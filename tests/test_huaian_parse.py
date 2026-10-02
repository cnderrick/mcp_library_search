"""淮安 fixture 解析测试：LibStar 家族 parser 直打淮安实抓页面。

字段侦察结论见 tests/fixtures/huaian/NOTES.md（解析以它为准）。
淮安与无锡/徐州同款图星 LibStar Find，解析器抽在 libstar/ 家族，零 quirk。
"""
import json
from pathlib import Path

from mcp_library_search.libstar import parser

FIXTURES = Path(__file__).parent / "fixtures" / "huaian"


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_search_p1_parses_books_with_stable_ids():
    r = parser.parse_search(_load("search_santi.json"))
    assert r["total_results"] == 3110
    assert len(r["books"]) == 10
    first = r["books"][0]
    assert first["book_id"] == "733596"
    assert first["title"] == "三体 : 图像小说"
    assert first["author"] == "原著刘慈欣"
    assert first["publisher"] == "译林出版社"
    # publishYear 带月份 2025.01 → 取四位年份
    assert first["publish_year"] == "2025"
    assert first["availability_summary"] == "纸本2，可借2"
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
    assert d["call_number"] == "I247.5"
    assert d["summary"].startswith("本书改编自科幻文学《三体》")


def test_holdings_borrowed_and_empty_main_group():
    hs = parser.parse_holdings(_load("holding_santi.json"))
    assert len(hs) == 2
    assert all(h["library"] == "淮安市清江浦区图书馆" for h in hs)
    assert all(h["status"].startswith("借出-应还日期:") for h in hs)
    assert all(h["available"] is False for h in hs)
    assert {h["due_date"] for h in hs} == {"2026-09-28", "2026-11-07"}
    assert hs[0]["call_number"] == "I247.5/7744"


def test_holdings_mixed_states_and_due_dates():
    hs = parser.parse_holdings(_load("holding_weicheng.json"))
    assert len(hs) == 8
    assert sum(1 for h in hs if h["available"]) == 6
    borrowed = [h for h in hs if not h["available"]]
    assert {h["due_date"] for h in borrowed} == {"2025-12-25", "2027-01-17"}
    assert all(h["status"] == "在架" or h["status"].startswith("借出-应还日期:")
               for h in hs)
