"""uopac 家族解析层测试：金陵（uopac.jllib.cn）与扬州（ytlmopac.cn）两站 fixture 同跑。

本文件的存在本身就是家族化的验收证据——同一套解析函数在两地实抓页面上都必须
逐字段命中；任何一站页面结构漂移，这里立刻红。
字段结论见 tests/fixtures/nanjing/NOTES.md 与 tests/fixtures/yangzhou/NOTES.md。
"""
from pathlib import Path

import pytest

from mcp_library_search.uopac import check_id, isbn_wildcard, looks_like_isbn, parser

_NJ = Path(__file__).parent / "fixtures" / "nanjing"
_YZ = Path(__file__).parent / "fixtures" / "yangzhou"


def _nj(name):
    return (_NJ / name).read_text(encoding="utf-8")


def _yz(name):
    return (_YZ / name).read_text(encoding="utf-8")


# ---------- ISBN 形态与通配（两站同一策略） ----------

def test_isbn_helpers():
    assert looks_like_isbn("9787229100605")
    assert looks_like_isbn("978-7-229-10060-5")
    assert looks_like_isbn("7536692930")
    assert not looks_like_isbn("三体")
    assert not looks_like_isbn("12345")
    assert isbn_wildcard("978-7-229-10060-5") == "9*7*8*7*2*2*9*1*0*0*6*0*5"


def test_norm_isbn_drops_dirty_values():
    assert parser.norm_isbn("978-7-5366-9293-0") == "9787536692930"
    assert parser.norm_isbn("") == ""
    assert parser.norm_isbn("无") == ""


def test_check_id_rejects_non_digits():
    from mcp_library_search.uopac import UopacConfig
    cfg = UopacConfig(name_cn="测试馆", base_url="http://example.invalid")
    assert check_id(cfg, "780232") == "780232"
    with pytest.raises(RuntimeError, match="book_id"):
        check_id(cfg, "abc")


# ---------- 检索结果页 ----------

def test_parse_search_jinling():
    r = parser.parse_search(_nj("uopac_result_santi.html"), "JL:")
    assert r["total_results"] == 59
    assert r["total_pages"] == 3
    assert len(r["books"]) == 20
    b0 = r["books"][0]
    assert b0.record_id == "JL:4386216"
    assert b0.title == "三体问题"
    assert b0.author == "汪家訸编著"
    assert b0.publisher == "科学出版社"
    assert b0.publish_year == "1961"
    assert b0.availability_summary == "所在馆：金陵图书馆"


def test_parse_search_yangzhou():
    r = parser.parse_search(_yz("uopac_result_santi.html"))
    assert r["total_results"] == 73
    assert r["total_pages"] == 4
    assert len(r["books"]) == 20
    b0 = r["books"][0]
    # 单源城市：无前缀，book_id 即源站 uopac 数字 id
    assert b0.record_id == "780232"
    assert b0.title == "三体漫画 起源 地球大危机"
    assert b0.author == "刘慈欣原著"
    assert b0.publisher == "浙江文艺出版社"
    assert b0.publish_year == "2024"
    assert b0.isbn == "9787533974022"
    assert b0.availability_summary == "所在馆：扬州市图书馆"
    # 多馆持有的条目：联盟成员馆以「、」连接（源站是空白分隔）
    b1 = r["books"][1]
    assert b1.availability_summary == "所在馆：扬州市图书馆、扬州市邗江区图书馆"


def test_parse_search_yangzhou_page_two_and_empty():
    p2 = parser.parse_search(_yz("uopac_result_santi_p2.html"))
    assert p2["total_results"] == 73
    assert p2["total_pages"] == 4
    assert p2["books"][0].title == "唐宋词三体钢笔字帖"

    empty = parser.parse_search(_yz("uopac_result_empty.html"))
    assert empty["total_results"] == 0
    assert empty["books"] == []
    # 空结果页无 num 分页区 → 按固定每页 20 条回退
    assert empty["total_pages"] == 0


def test_parse_search_isbn_wildcard_result_yangzhou():
    r = parser.parse_search(_yz("uopac_result_isbn_wild.html"))
    assert r["total_results"] == 1
    assert r["books"][0].record_id == "780232"


@pytest.mark.parametrize("reader", [_nj, _yz], ids=["jinling", "yangzhou"])
def test_result_mark_present_in_both(reader):
    # 家族用 RESULT_MARK 判断「是不是结果页」——两站都必须有
    assert parser.RESULT_MARK in reader("uopac_result_santi.html")


# ---------- 详情页 ----------

def test_parse_detail_jinling():
    d = parser.parse_detail(_nj("uopac_detail_jl.html"))
    assert d["title"] == "三体:典藏版"
    assert d["author"] == "刘慈欣著"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2016"
    assert d["isbn"] == "978-7-229-10060-5"
    # 详情页无索书号字段：中图法分类号不冒充，恒空串
    assert d["call_number"] == ""
    assert d["summary"].startswith("国内科学界发生巨大变故")


def test_parse_detail_yangzhou():
    d = parser.parse_detail(_yz("uopac_detail_single.html"))
    assert d["title"] == "三体漫画:起源.地球大危机"
    assert d["author"] == "刘慈欣原著 蔡劲, 戈同頔, 薄暮改编"
    assert d["publisher"] == "浙江文艺出版社"
    assert d["publish_year"] == "2024"
    assert d["isbn"] == "978-7-5339-7402-2"
    assert d["call_number"] == ""          # 同金陵：无索书号字段
    assert d["summary"].startswith("汪淼是一位普通的物理学家")


# ---------- 馆藏 tab ----------

def test_parse_tabs_jinling():
    tabs = parser.parse_tabs(_nj("uopac_detail_jl.html"), "http://uopac.jllib.cn")
    assert tabs[0][0] == "金陵图书馆"
    assert all(u.startswith("http://uopac.jllib.cn/uopac/s/ajax_holding.action") for _, u in tabs)


def test_parse_tabs_yangzhou_multi_member():
    tabs = parser.parse_tabs(_yz("uopac_detail_multi.html"), "http://ytlmopac.cn:8080")
    assert [name for name, _ in tabs] == ["扬州市图书馆", "扬州市邗江区图书馆"]
    assert all(u.startswith("http://ytlmopac.cn:8080/uopac/s/ajax_holding.action")
               for _, u in tabs)
    # 代理目标落在成员馆自站（libCode 由源站拼好）
    assert "libCode%3DYZLIB" in tabs[0][1] or "libCode=YZLIB" in tabs[0][1]


# ---------- 馆藏表 ----------

def test_parse_holding_rows_yangzhou():
    hs = parser.parse_holding_rows(_yz("uopac_holding_yzlib.html"), "扬州市图书馆")
    assert len(hs) == 4
    assert all(h.library == "扬州市图书馆" for h in hs)
    assert all(h.call_number == "J228.2/482" for h in hs)
    assert {h.location for h in hs} == {"委托借阅 网约书", "总馆 少儿外借室"}
    avail = [h for h in hs if h.available]
    assert len(avail) == 3
    assert all(h.status == "可借" and h.due_date == "" for h in avail)
    loaned = [h for h in hs if not h.available]
    # 扬州站不给应还日期：裸「借出」原值照登，due_date 不猜
    assert [h.status for h in loaned] == ["借出"]
    assert [h.due_date for h in loaned] == [""]


def test_parse_holding_rows_jinling_keeps_due_date():
    # 同一条解析路径在金陵侧照常取出「借出-应还日期：X」里的日期
    hs = parser.parse_holding_rows(_nj("uopac_holding_jl.html"), "金陵图书馆")
    assert len(hs) == 13
    loaned = [h for h in hs if not h.available]
    assert loaned and all(h.status.startswith("借出-应还日期：") for h in loaned)
    assert all(len(h.due_date) == 10 for h in loaned)
    assert {h.due_date for h in loaned} >= {"2026-10-10", "2025-01-30", "2027-09-30"}


def test_parse_holding_rows_yangzhou_member():
    hs = parser.parse_holding_rows(_yz("uopac_holding_hjq.html"), "扬州市邗江区图书馆")
    assert len(hs) == 1
    assert hs[0].library == "扬州市邗江区图书馆"
    assert hs[0].call_number == "J228.2/118"
    assert hs[0].location == "总馆 少儿书库"
    assert hs[0].available is True


def test_holding_conservative_on_unknown_status():
    # 词表外状态与坏日期形态：一律 False，原值照登，due_date 不猜
    table = ('<table><tr align="center" bgcolor="#FFFFFF">'
             '<td>I2/1</td><td>001</td><td></td><td>总馆</td><td>借阅室</td>'
             '<td>借出-应还日期：待定</td></tr>'
             '<tr align="center" bgcolor="#FFFFFF">'
             '<td>I2/2</td><td>002</td><td></td><td></td><td>阅览室</td>'
             '<td>阅览室内</td></tr></table>')
    hs = parser.parse_holding_rows(table, "某馆")
    assert [(h.status, h.available, h.due_date) for h in hs] == [
        ("借出-应还日期：待定", False, ""), ("阅览室内", False, "")]
    assert hs[1].location == "阅览室"
