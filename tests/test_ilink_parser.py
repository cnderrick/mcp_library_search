"""iLink 家族解析测试（离线，不打真网）：用甘肃三站实抓 fixture 钉页面解析。

覆盖：结果页总数/空结果、命中条目字段与 record_id、翻页区间与 catkey 定位、
详情页简要字段、馆藏表（**无 `id="display_holdings_table"` 的甘肃变体**）按分馆分组
与复本索书号召回、copy_info 可借判定、题名候选梯度与短语包装。大连接口同构但独立
实现，不在本测试范围。
"""
from pathlib import Path

from mcp_library_search.ilink import parser

_FIX = Path(__file__).parent / "fixtures"
_GS = (_FIX / "gansu_prov")
_ENTRY = (_GS / "entry_raw.html").read_text(encoding="utf-8")
_SEARCH = (_GS / "search_prov.html").read_text(encoding="utf-8")
_P2 = (_GS / "search_p2.html").read_text(encoding="utf-8")
_EMPTY = (_GS / "search_empty.html").read_text(encoding="utf-8")


def test_result_page_markers_and_total():
    assert parser.is_result_page(_SEARCH)
    assert parser.parse_total(_SEARCH) == 101
    assert parser.parse_total(_P2) == 101
    # 空结果页：title 仍是「目录检索结果」、summary 为 &nbsp; → total 0、无命中块
    assert parser.is_result_page(_EMPTY)
    assert parser.parse_total(_EMPTY) == 0
    assert parser.parse_hits(_EMPTY) == []


def test_parse_hits_fields_and_record_id():
    books = parser.parse_hits(_SEARCH)
    assert len(books) == 20
    b0 = books[0]
    assert b0["catkey"] == "1644695"
    assert b0["record_id"] == "1644695:2016文化观察选粹 专著 金浪主编"
    assert b0["title"] == "2016文化观察选粹 专著 金浪主编"
    assert b0["author"] == "金浪 (文学) 主编"
    assert b0["publish_year"] == "2017"
    assert b0["availability_summary"] == "1 馆藏于 甘肃省馆 在 社科闭架"


def test_hitlist_action_range_and_ckey_position():
    assert parser.hitlist_action(_SEARCH) == "/uhtbin/cgisirsi/?ps=GfuKPnbHFB/甘肃馆/182790315/9"
    assert parser.hitlist_range(_SEARCH, 20) == (1, 20)
    assert parser.hitlist_range(_P2, 20) == (21, 40)
    assert parser.find_ckey_position(_SEARCH, "1644695") == 1
    assert parser.find_ckey_position(_SEARCH, "999999999") is None


def test_entry_markers_and_actions():
    assert parser.is_entry_page(_ENTRY)
    assert parser.searchform_action(_ENTRY) == (
        "/uhtbin/cgisirsi/?ps=5FQqk48A3u/甘肃馆/5530661/123")
    assert parser.sort_by_value(_ENTRY) == "TI"


def test_detail_fields_gansu():
    t = (_GS / "detail_prov.html").read_text(encoding="utf-8")
    assert parser.is_detail_page(t)
    assert parser.detail_field(t, "题名") == "2016文化观察选粹 专著 金浪主编"
    assert parser.detail_field(t, "著者") == "金浪 (文学) 主编"
    assert parser.detail_field(t, "出版者") == "北岳文艺出版社"
    assert parser.detail_field(t, "出版日期") == "2017"
    assert parser.detail_field(t, "ISBN") == "9787537850797"
    assert parser.year(parser.detail_field(t, "出版日期")) == "2017"


def test_holdings_rows_gansu_table_without_id_and_copy_fill_down():
    t = (_GS / "detail_prov.html").read_text(encoding="utf-8")
    rows = parser.holdings_rows(t)
    assert len(rows) == 3  # 三个复本；后续复本索书号格为 &nbsp;，需沿用首行
    assert all(r["library"] == "甘肃馆" for r in rows)
    assert [r["call_number"] for r in rows] == ["G122-53/25/:2016"] * 3
    assert [r["copies"] for r in rows] == ["1", "2", "3"]
    assert rows[0]["location"] == "到期: 2027/7/31"
    assert rows[2]["location"] == "社科闭架"


def test_availability_conservative_wording():
    # 明确在架词才判可借；「馆藏于」等仅表位置，保守 False 且状态原值照登
    assert parser.availability_from_copy_info("3 件馆藏在架上 陇南图书馆.") == ("在架上", True)
    assert parser.availability_from_copy_info("1 馆藏于 甘肃省馆.") == ("馆藏于", False)
    assert parser.availability_from_copy_info("") == ("", False)


def test_copy_info_and_longnan_onshelf():
    t = (_FIX / "longnan" / "detail.html").read_text(encoding="utf-8")
    assert parser.copy_info(t) == "3 件馆藏在架上 陇南图书馆."
    assert parser.availability_from_copy_info(parser.copy_info(t)) == ("在架上", True)
    assert parser.holdings_rows(t)[0]["library"] == "陇南馆"


def test_gannan_holdings_library_header():
    t = (_FIX / "gannan" / "detail.html").read_text(encoding="utf-8")
    assert parser.copy_info(t) == "1 馆藏于 甘南图书馆."
    rows = parser.holdings_rows(t)
    assert len(rows) == 2
    assert all(r["library"] == "甘南馆" for r in rows)


def test_phrase_and_title_variants():
    assert parser.phrase("三体") == '"三体"'
    assert parser.phrase('"三体"') == '"三体"'  # 已带引号不二次包裹
    variants = parser.title_variants("三体 2 黑暗森林 专著 刘慈欣著")
    assert variants[0] == '"三体 2 黑暗森林"'
    assert variants[1] == "三体 2 黑暗森林"
