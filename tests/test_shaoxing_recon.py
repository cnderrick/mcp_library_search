"""绍兴 OPAC 侦察证据测试（该城降级「待调研」，本文件是结论的可执行留档）。

绍兴（opac.sxlib.com）确属图创 Interlib，但跑的是 pro2018 模板代：搜索结果页与
详情页的 HTML 结构与家族 parser（interlib/parser.py，以广州为基准）依赖的标记全部
对不上。本测试**只读 tests/fixtures/shaoxing/ 的实抓 fixture，不打真网**，钉住三件事：

1. pro2018 模板标记存在（libBookUl/libBookDetNm/bkTxtTit/numFound=/totalPage: 等）；
2. 家族基准标记缺失（bookmeta 容器、title-link 结果锚点、bookInfoTable、leftTD/rightTD、h2）；
3. 家族 parser 实跑绍兴 fixture 的结果——搜索 0 条、详情全空（不兼容的硬证据），
   而 holding JSON 顶层键与广州一致（结构兼容）。

若将来家族 parser 被扩展以覆盖 pro2018 模板，本文件的「不兼容」断言会变红——
那是正确信号：说明降级前提已变，应重新评估接入。详见 fixtures/shaoxing/NOTES.md。
"""
import json
import re
from pathlib import Path

from mcp_library_search.interlib import parser

FIXTURES = Path(__file__).parent / "fixtures" / "shaoxing"

SEARCH = (FIXTURES / "search_p1.html").read_text(encoding="utf-8")
DETAIL = (FIXTURES / "detail.html").read_text(encoding="utf-8")
HOLDING = json.loads((FIXTURES / "holding.json").read_text(encoding="utf-8"))


# ---------- 1. pro2018 模板标记存在 ----------

def test_search_uses_pro2018_template_markers():
    # 结果列表容器是 libBookUl/libBookLi，题名锚点 class 是 libBookDetNm
    assert "libBookUl" in SEARCH
    assert 'class="libBookDetNm"' in SEARCH or "libBookDetNm" in SEARCH
    # 书目 ID 从 bookDetail(数字 调用里取（散落在内层元素，不在条目容器上）
    assert re.search(r"bookDetail\(\d+", SEARCH)
    # 责任者/出版信息靠中文标签 + layerTip class，不是 author-link/publisher-link
    assert "责任者" in SEARCH
    assert "出版信息" in SEARCH


def test_search_total_and_pages_are_js_vars():
    # 总数/总页数走 JS 变量，不是广州的「检索到: N 条结果」「共 N 页」可见文案
    assert re.search(r"numFound=\d+", SEARCH)
    assert re.search(r"totalPage:\s*\d+", SEARCH)
    assert "检索到" not in SEARCH


def test_detail_uses_pro2018_template_markers():
    # 题名用 <a class="bkTxtTit">，字段是 <li>标签：<span>值</span></li>
    assert "bkTxtTit" in DETAIL
    assert "ISBN：" in DETAIL
    assert "出版发行：" in DETAIL
    assert "中图分类法：" in DETAIL


# ---------- 2. 家族基准标记缺失 ----------

def test_search_lacks_family_bookmeta_anchors():
    # 家族 _SearchParser 的入口容器与字段锚点在绍兴结果里都不存在
    assert '<div class="bookmeta"' not in SEARCH
    assert not re.search(r'<a[^>]*class="[^"]*title-link', SEARCH)
    assert not re.search(r'<a[^>]*class="[^"]*author-link', SEARCH)
    assert not re.search(r'<a[^>]*class="[^"]*publisher-link', SEARCH)


def test_detail_lacks_family_bookinfo_anchors():
    # 家族 _DetailParser 依赖的 bookInfoTable/leftTD/rightTD/h2/主要责任者/内容提要 全缺
    assert "bookInfoTable" not in DETAIL
    assert "leftTD" not in DETAIL
    assert "rightTD" not in DETAIL
    assert "<h2" not in DETAIL
    assert "主要责任者" not in DETAIL
    assert "内容提要" not in DETAIL


# ---------- 3. 家族 parser 实跑结果（不兼容硬证据 + holding 结构兼容） ----------

def test_family_parse_search_returns_no_books():
    # 硬证据：家族搜索 parser 跑绍兴搜索页得 0 条书、总数 None、页数回退 1
    r = parser.parse_search(SEARCH)
    assert r["books"] == []
    assert r["total_results"] is None
    assert r["total_pages"] == 1


def test_family_parse_detail_returns_empty_fields():
    # 硬证据：家族详情 parser 跑绍兴详情页所有字段全空
    d = parser.parse_detail(DETAIL)
    assert d["title"] == ""
    assert d["author"] == ""
    assert d["isbn"] == ""
    assert d["publisher"] == ""
    assert d["call_number"] == ""
    assert d["summary"] == ""


def test_holding_json_structure_is_family_compatible():
    # holding JSON 顶层键与广州一致 → parse_holdings 结构兼容（本书 holdingList 恰为空）
    for key in ("holdingList", "libcodeMap", "localMap", "holdStateMap", "loanWorkMap"):
        assert key in HOLDING
    # holdStateMap 形状一致：{状态码: {stateType, stateName}}
    sample = next(iter(HOLDING["holdStateMap"].values()))
    assert "stateName" in sample and "stateType" in sample
    # 本书单册数组为空（联合目录取数条件待查，照实记录不猜语义）
    assert parser.parse_holdings(HOLDING) == []
