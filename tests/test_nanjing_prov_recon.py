r"""南京图书馆 ALEPH 侦察证据测试（家族兼容性的可执行留档）。

南图（opac.jslib.org.cn/F/）是 Ex Libris ALEPH `u20_1 / www_f_chi`，与天津主馆同版本
同皮肤；此前进不去是前置 openresty 的**按 IP 全局验证码墙**（与天津 401 同型，但**按 host
独立**——解南图不解天津）。2026-10-02 用户浏览器过码解封本机 IP 后全链路实网跑通。

本测试**只读 tests/fixtures/nanjing_prov/ 的实抓 fixture，不打真网**，钉住三件事：

1. 南图页面具备天津家族解析器依赖的全部标记（brief 的 publish section 注释块、
   itemtitle 锚点、item-global 的 Loan status/Due date/Sub-library/Collection/Location 注释）；
2. `aleph/parser.py` 的 ALEPH 解析函数实跑南图 fixture 全部命中——这是南图接入
   直接复用家族解析（未新写一份本地副本）的依据；
3. 家族解析器的**跨行吞值陷阱**已修并留档：字段取值正则写 `\s*` 会跨行，字段为空
   时把下一行文本吞成值（空 ISBN 吞掉 SET-NUMBER、空 IMPRINT 吞掉 CALL-NO）。
   天津 fixture 各字段全非空故从未暴露，南图的音像与古籍记录踩中。

详见 fixtures/nanjing_prov/NOTES.md。
"""
from pathlib import Path

from mcp_library_search.aleph import parser as aleph_parser

FIXTURES = Path(__file__).parent / "fixtures" / "nanjing_prov"


def _load(name):
    return (FIXTURES / name).read_text(encoding="utf-8", errors="replace")


# ---------- 1. 家族标记存在 ----------

def test_brief_pages_carry_family_markers():
    for name in ("findb_NJL01.html", "findb_CNBOK.html"):
        text = _load(name)
        # brief 条目锚点与 publish section 结构化字段（家族解析器的取数依据）
        assert "class=itemtitle" in text
        assert "DOC-NUMBER (3300)" in text
        assert "Z13-ISBN-ISSN (3100)" in text
        assert "Z05-BASE (3400)" in text
        # 单册链接形态
        assert "func=item-global&doc_library=" in text


def test_item_global_pages_carry_family_markers():
    for name in ("holdings_MCBKL.html", "holdings_MCTBY.html"):
        text = _load(name)
        for marker in ("Loan status", "Due date", "Due hour",
                       "Sub-library", "Collection", "Location"):
            assert f"<!--{marker}-->" in text, f"{name} 缺 {marker} 标记"


def test_paging_and_count_forms_match_family():
    text = _load("findb_CNBOK.html")
    assert aleph_parser.COUNT.search(text).groups() == ("1", "10", "2745")
    assert aleph_parser.JUMP.search(text), "缺 func=short-jump&jump= 翻页形态"
    # 原生翻页：jump=11 → 记录 11–20
    assert aleph_parser.COUNT.search(_load("short_jump11.html")).groups() == ("11", "20", "2745")


# ---------- 2. 天津家族解析器实跑南图 fixture ----------

def test_family_parser_handles_nanjing_search():
    r = aleph_parser.parse_find(_load("findb_CNBOK.html"), "CNBOK")
    assert r["total_results"] == 2745
    assert len(r["books"]) == 10
    first = r["books"][0]
    assert first.record_id == "CNBOK:002912577"
    assert first.title == "蔡元培论红楼梦"
    assert first.isbn == "978-7-100-24958-4"
    assert first.call_number == "I207.411/1581"
    assert first.publish_year == "2025"

    r2 = aleph_parser.parse_find(_load("findb_NJL01.html"), "NJL01")
    assert r2["total_results"] == 3192
    assert r2["books"][0].record_id == "NJL01:002159107"


def test_family_parser_handles_nanjing_detail():
    b = aleph_parser.parse_full_record(_load("detail_full.html"), "CNBOK")
    assert b is not None
    assert b.record_id == "CNBOK:002912577"
    assert b.title == "蔡元培论红楼梦"
    assert b.isbn == "978-7-100-24958-4"
    assert b.call_number == "I207.411/1581"


def test_family_parser_handles_nanjing_holdings():
    hs = aleph_parser.parse_item_global(_load("holdings_MCBKL.html"))
    assert len(hs) == 1
    assert hs[0].library == "中文图书借阅"
    assert hs[0].call_number == "I207.411/1581"
    assert "在架" in hs[0].status and hs[0].available and hs[0].due_date == ""

    # 采编部（订购加工）：无在架单册，0 条属数据边界，非解析失败
    assert aleph_parser.parse_item_global(_load("holdings_MBKDB.html")) == []


# ---------- 3. 跨行吞值陷阱（已修）：空字段必须回空串 ----------

def test_empty_isbn_returns_empty_string():
    """南图音像资料无 ISBN：`Z13-ISBN-ISSN (3100) = ` 后直接换行。
    正则写 `\\s*` 时会跨行把下一行 SET-NUMBER 吞成 ISBN（天津 fixture 无空样本，
    从未暴露）。已收紧为只吃同行空白。"""
    books = aleph_parser.parse_find(_load("findb_NJL01.html"), "NJL01")["books"]
    assert not any(b.isbn.startswith("SET-NUMBER") for b in books)
    audio = next(b for b in books if b.record_id == "NJL01:002910042")
    assert audio.isbn == ""


def test_empty_detail_fields_return_empty_string():
    """南图古籍记录 ISBN/IMPRINT 为空：不得把下一行的 TITLE/CALL-NO 当成值
    （实抓 detail_guji_empty_fields.html）。"""
    b = aleph_parser.parse_full_record(_load("detail_guji_empty_fields.html"), "NJL01")
    assert b.record_id == "NJL01:000942136"
    assert b.title == "續唐三體詩"
    assert b.author == "高士奇"
    assert b.isbn == ""
    assert b.publisher == ""
    assert b.publish_year == ""
    assert b.call_number == "GJ/806899"
