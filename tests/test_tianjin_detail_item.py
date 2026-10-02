"""天津 ALEPH 详情与单册解析。

fixture 语义（NOTES.md）：单册行「单册状态」列是流通类型（阅览/中文图书借阅/网借图书借阅），
「应还日期」列才是可借性原值（在架上 / 借出时为日期）。可借判定只看应还日期列。
"""
from pathlib import Path

from mcp_library_search.aleph import parser as aleph_parser

_FIX = Path(__file__).parent / "fixtures" / "tianjin"


def open_fix(name):
    return (_FIX / name).read_text(encoding="utf-8")


def test_parse_full_record_detail():
    d = aleph_parser.parse_full_record(open_fix("detail_tjl01.html"), "TJL01")
    assert d.record_id == "TJL01:002892667"
    assert d.isbn == "978-7-5730-2384-1"
    assert "宇宙是巧合吗" in d.title
    assert d.author == "艾格纳"
    assert d.publisher == "海南出版社"
    assert d.call_number == "P159/88"


def test_parse_item_rows_raw_values():
    hs = aleph_parser.parse_item_global(open_fix("item_tjl01.html"))
    assert len(hs) == 3
    assert [h.library for h in hs] == ["文化中心中图基藏", "复康路中文图书借阅", "津图驿借"]
    h0 = hs[0]
    # 状态原值 = 流通类型 + 应还日期列文本，两值都保留
    assert "阅览" in h0.status and "在架上" in h0.status
    assert h0.call_number == "P159/88"
    assert h0.due_date == ""


def test_parse_item_availability_from_due_column():
    hs = aleph_parser.parse_item_global(open_fix("item_tjl01.html"))
    # 三册应还日期列均为「在架上」→ 可借；「阅览」是流通类型不参与判定
    assert all(h.is_available() for h in hs)


def test_parse_item_borrowed_row_synthetic():
    # 借出行无真网样本（本书三册全在架），按 NOTES 推定结构合成：
    # 应还日期列变为日期 → 不可借，status 只留流通类型，due_date 归一化
    row = (
        "<tr><td class=td1>x</td>"
        "<!--Description--><td class=td1><br></td>"
        "<!--Loan status--><td class=td1>中文图书借阅</td>"
        "<!--Due date--><td class=td1>20261015</td>"
        "<!--Sub-library--><td class=td1 nowrap>复康路中文图书借阅</td>"
        "<!--Collection--><td class=td1 nowrap><br></td>"
        "<!--Location--><td class=td1>P159/88</td></tr>"
    )
    hs = aleph_parser.parse_item_global(row)
    assert len(hs) == 1
    assert hs[0].is_available() is False
    assert hs[0].due_date == "2026-10-15"
    assert hs[0].status == "中文图书借阅"


def test_parse_item_unknown_due_word_conservative():
    # 应还日期列出现词表外文本 → 保守不可借，原值进 status
    row = (
        "<tr><!--Loan status--><td class=td1>外借</td>"
        "<!--Due date--><td class=td1>整理中</td>"
        "<!--Sub-library--><td class=td1>某分馆</td>"
        "<!--Location--><td class=td1>X1/1</td></tr>"
    )
    hs = aleph_parser.parse_item_global(row)
    assert len(hs) == 1
    assert hs[0].is_available() is False
    assert "整理中" in hs[0].status


def test_parse_item_same_value_columns_deduped():
    # 真网实测：两列同值（分配中/编目中/物流中）→ status 只留一份，保守不可借
    row = (
        "<tr><!--Loan status--><td class=td1>分配中</td>"
        "<!--Due date--><td class=td1>分配中</td>"
        "<!--Sub-library--><td class=td1>宁河区图书馆图书借阅</td>"
        "<!--Location--><td class=td1>I247.55 19</td></tr>"
    )
    hs = aleph_parser.parse_item_global(row)
    assert hs[0].status == "分配中"
    assert hs[0].is_available() is False
    assert hs[0].due_date == ""
