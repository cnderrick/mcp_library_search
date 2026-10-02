"""成都 OPAC 解析测试：libBookLi 搜索模板 + bkTxt 详情模板 + 家族馆藏 JSON。

fixture 为 2026-10-02 实抓（见 tests/fixtures/chengdu/NOTES.md），钉死值以实抓为准。
搜索/详情解析在 adapters/chengdu.py 本地（pro2018 模板代，台州同款路径），
馆藏直接走家族解析器（holding JSON 与广州基准同构，state=2→在馆/3→借出）。
"""
import json

from mcp_library_search.adapters.chengdu import _parse_detail, _parse_search
from mcp_library_search.interlib import parser as family_parser

P1 = open("tests/fixtures/chengdu/search_p1.html", encoding="utf-8").read()
P2 = open("tests/fixtures/chengdu/search_p2.html", encoding="utf-8").read()
EMPTY = open("tests/fixtures/chengdu/search_empty.html", encoding="utf-8").read()
DETAIL = open("tests/fixtures/chengdu/detail.html", encoding="utf-8").read()
HOLDING = json.load(open("tests/fixtures/chengdu/holding.json", encoding="utf-8"))


# ---------- 搜索页（libBookLi 模板，pro2018 皮肤） ----------


def test_search_p1_parses_books_with_stable_ids():
    r = _parse_search(P1)
    assert len(r["books"]) == 10
    for b in r["books"]:
        assert set(b) == {"book_id", "title", "author", "publisher",
                          "publish_year", "availability_summary", "isbn"}
        assert b["book_id"].isdigit()
        assert b["title"]
        assert b["availability_summary"] == ""
    # 钉死第一条（值以实抓 fixture 为准；bookrecno 10 位，联合目录形态）
    first = r["books"][0]
    assert first["book_id"] == "1004752340"
    assert first["title"] == "三体"
    assert first["author"] == "刘慈欣著"          # 含 MARC 责任方式，同家族口径
    assert first["publisher"] == "重庆出版社"
    assert first["publish_year"] == "2008"
    assert first["isbn"] == "978-7-5366-9293-0"   # 内部字段，不进 BookSummary 契约


def test_search_p1_pagination_semantics():
    # 成都总数/分页与台州同源：schResNumIn 元素 + JS pagination 配置
    r = _parse_search(P1)
    assert r["total_results"] == 1826
    assert r["total_pages"] == 183
    assert r["has_next"] is True


def test_search_p2_is_different_page():
    r1, r2 = _parse_search(P1), _parse_search(P2)
    ids1 = [b["book_id"] for b in r1["books"]]
    ids2 = [b["book_id"] for b in r2["books"]]
    assert len(ids2) == 10
    assert set(ids1).isdisjoint(ids2)
    assert r2["books"][0]["book_id"] == "1004758425"
    assert r2["books"][0]["isbn"] == "978-7-229-16692-2"
    # 第 2 页（共 183 页）仍有下一页
    assert r2["total_pages"] == 183
    assert r2["has_next"] is True


def test_search_empty_yields_zero():
    r = _parse_search(EMPTY)
    assert r["books"] == []
    # 空结果页不渲染总数区，但有 notFindFt 明确提示锚点 → 判 0（源站明说）
    assert r["total_results"] == 0
    assert r["total_pages"] == 1
    assert r["has_next"] is False


# ---------- 详情页（bkTxt 模板，左右两列 li 标签） ----------


def test_detail_parses_all_fields():
    d = _parse_detail(DETAIL)
    assert set(d) == {"title", "author", "publisher", "publish_year",
                      "isbn", "call_number", "summary"}
    assert d["title"] == "三体"                # bkTxtTit 锚点
    assert d["author"] == "刘慈欣"             # 主要责任者首个 a 文本
    assert d["publisher"] == "重庆出版社"      # 出版发行首个 a 文本，尾逗号已去
    assert d["publish_year"] == "2008"
    assert d["isbn"] == "978-7-5366-9293-0"
    assert d["call_number"] == "I247.55"       # 中图分类法「版次」之前
    assert d["summary"] == ""                  # 实抓样例无「内容提要」标签行


def test_detail_json_marc_is_optional_enhancement():
    # ?return_fmt=json 带完整 MARC（可选增强，适配器未采用；fixture 存档作证）
    dj = json.load(open("tests/fixtures/chengdu/detail.json", encoding="utf-8"))
    marc = ((dj.get("book") or {}).get("biblios") or {}).get("marcContent") or ""
    assert marc.startswith("00819nam")         # ISO 2709 记录头
    assert "\u001e" in marc                    # 字段分隔符


# ---------- 馆藏 JSON（家族解析器零改动兼容；state 语义以 holdStateMap 原值为准） ----------


def test_family_holdings_parser_compat():
    hs = family_parser.parse_holdings(HOLDING)
    assert len(hs) == 98
    # 调研初判「2=非外借、3=在架可借」与实抓相反：holdStateMap 原值 2→在馆、3→借出
    state_map = HOLDING["holdStateMap"]
    assert state_map["2"]["stateName"] == "在馆"
    assert state_map["3"]["stateName"] == "借出"
    assert {h["status"] for h in hs} == {"在馆", "借出"}
    # 家族词表判定：在馆 84 条可借、借出 14 条不可借，无需新词表
    avail = [h for h in hs if family_parser.is_available_status(h["status"])]
    assert len(avail) == 84
    # 馆名经 libcodeMap 翻译（联合目录跨市域：成都辖区+德阳/眉山/资阳等）
    assert {h["library"] for h in hs} >= {"郫都区图书馆", "德阳市图书馆", "什邡市图书馆"}
    # 应还日期来自 loanWorkMap.returnDate（epoch 毫秒，UTC+8）；借出 14 条中 8 条带日期，
    # 其余空串照登；日期含远期（2035-02-10）与远逾期（2019-02-26）原值，不判断
    dues = sorted(h["due_date"] for h in hs if h["due_date"])
    assert len(dues) == 8
    assert dues[0] == "2019-02-26"
    assert dues[-1] == "2035-02-10"
