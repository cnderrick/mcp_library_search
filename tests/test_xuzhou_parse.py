"""徐州 fixture 解析测试：LibStar 家族 parser 直打徐州实抓页面。

字段侦察结论见 tests/fixtures/xuzhou/NOTES.md（解析以它为准）。
徐州与无锡新吴同款图星 LibStar Find，解析器抽在 libstar/ 家族，零 quirk。
"""
import json
from pathlib import Path

from mcp_library_search.libstar import parser

FIXTURES = Path(__file__).parent / "fixtures" / "xuzhou"


def _load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_search_p1_parses_books_with_stable_ids():
    r = parser.parse_search(_load("search_santi.json"))
    assert r["total_results"] == 407
    assert len(r["books"]) == 10
    first = r["books"][0]
    assert set(first) == {"book_id", "title", "author", "publisher",
                          "publish_year", "availability_summary", "isbn"}
    assert first["book_id"] == "439114"
    assert first["title"] == "三体. Ⅲ. Ⅲ, 死神永生, Dead end"
    assert first["author"] == "刘慈欣著"
    assert first["publisher"] == "重庆出版社"
    # publishYear 带月份 2010.11 → 取四位年份
    assert first["publish_year"] == "2010"
    # 可借概况由 physicalCount/onShelfCountI 拼装
    assert first["availability_summary"] == "纸本1，可借1"
    assert first["isbn"] == "978-7-229-03093-3"


def test_search_empty_result():
    r = parser.parse_search(_load("search_empty.json"))
    assert r["total_results"] == 0
    assert r["books"] == []


def test_missing_groupcode_is_silent_zero_not_error():
    """对照证据：同一「三体」请求去掉 groupcode 头即静默 0 结果（success:true）。

    这正是家族 client 必须统一注入 groupcode 的原因——响应里无法分辨它是
    「真 0 命中」还是「漏带头」，只能靠调用点保证带上。
    """
    r = parser.parse_search(_load("search_santi_nogroup.json"))
    assert r["total_results"] == 0
    assert r["books"] == []


def test_detail_parses_bibliographic_fields():
    d = parser.parse_detail(_load("detail_santi3.json"))
    assert d["title"] == "三体.Ⅲ.死神永生"
    assert d["author"] == "刘慈欣著"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2010"
    assert d["isbn"] == "978-7-229-03093-3"
    # 详情页无独立索书号字段，call_number 取「中图法分类号」cnb67
    assert d["call_number"] == "I247.55"
    assert d["summary"].startswith("与三体文明的战争使人类第一次看到了宇宙黑暗的真相")


def test_holdings_multi_branch_and_empty_main_group():
    """馆藏 sortedList 含多分馆分组；主馆分组可无单册（439114 即如此）。"""
    hs = parser.parse_holdings(_load("holding_santi3.json"))
    assert len(hs) == 1
    assert hs[0]["library"] == "鼓楼图书馆黄楼分馆"
    assert hs[0]["location"] == "黄楼分馆综合外借"
    assert hs[0]["call_number"] == "I247.55/4:3"
    assert hs[0]["status"] == "在架"
    assert hs[0]["available"] is True
    assert hs[0]["due_date"] == ""


def test_holdings_maps_status_and_due_dates():
    hs = parser.parse_holdings(_load("holding_huozhe.json"))
    assert len(hs) == 20
    # 9 册在架（可借）；其余 10 册借出 + 1 册「正在上架」不可借
    assert sum(1 for h in hs if h["available"]) == 9
    borrowed = [h for h in hs if h["status"].startswith("借出-应还日期:")]
    assert len(borrowed) == 10
    # 应还日期从状态串内嵌解析，原值照登（含已过期的 2021/2023）
    assert "2021-05-17" in {h["due_date"] for h in borrowed}
    assert all(h["due_date"] for h in borrowed)
    # 多分馆：主馆（徐州图书馆）与鼓楼区馆都在同一个 sortedList 里
    libs = {h["library"] for h in hs}
    assert {"徐州图书馆", "徐州鼓楼区"} <= libs


def test_holdings_returning_to_shelf_is_conservatively_unavailable():
    """`本馆归还: 正在上架` 是词表外观测值：保守判不可借，原值照登（同重庆口径）。"""
    hs = parser.parse_holdings(_load("holding_huozhe.json"))
    shelving = [h for h in hs if h["status"] == "本馆归还: 正在上架"]
    assert len(shelving) == 1
    assert all(h["available"] is False and h["due_date"] == "" for h in shelving)
