"""台州 OPAC 解析测试:libBookLi 搜索模板 + bkTxt 详情模板 + 家族馆藏 JSON。

fixture 为 2026-10-02 实抓(见 tests/fixtures/taizhou/NOTES.md),钉死值以实抓为准。
搜索/详情解析函数暂在 adapters/taizhou.py(家族化建议见交付报告),馆藏直接走家族解析器。
"""
import json

from mcp_library_search.interlib.parser import (
    parse_detail_pro2018 as _parse_detail,
    parse_search_pro2018 as _parse_search,
)
from mcp_library_search.interlib import parser as family_parser

P1 = open("tests/fixtures/taizhou/search_p1.html", encoding="utf-8").read()
P2 = open("tests/fixtures/taizhou/search_p2.html", encoding="utf-8").read()
EMPTY = open("tests/fixtures/taizhou/search_empty.html", encoding="utf-8").read()
DETAIL = open("tests/fixtures/taizhou/detail_default.html", encoding="utf-8").read()
HOLDING = json.load(open("tests/fixtures/taizhou/holding.json", encoding="utf-8"))


# ---------- 搜索页(libBookLi 模板) ----------


def test_search_p1_parses_books_with_stable_ids():
    r = _parse_search(P1)
    assert len(r["books"]) == 10
    for b in r["books"]:
        assert set(b) == {"book_id", "title", "author", "publisher",
                          "publish_year", "availability_summary", "isbn"}
        assert b["book_id"].isdigit()
        assert b["title"]
        assert b["availability_summary"] == ""
    # 钉死第一条(值以实抓 fixture 为准)
    first = r["books"][0]
    assert first["book_id"] == "1185362"
    assert first["title"] == "三体：新版"
    assert first["author"] == "刘慈欣著"          # 含 MARC 责任方式,同广州口径
    assert first["publisher"] == "重庆出版社"
    assert first["publish_year"] == "2022"
    assert first["isbn"] == "978-7-229-16692-2"   # 内部字段,不进 BookSummary 契约


def test_search_p1_pagination_semantics():
    # 台州总数/分页与广州不同源:schResNumIn 元素 + JS pagination 配置
    r = _parse_search(P1)
    assert r["total_results"] == 163
    assert r["total_pages"] == 17
    assert r["has_next"] is True


def test_search_p2_is_different_page():
    r1, r2 = _parse_search(P1), _parse_search(P2)
    ids1 = [b["book_id"] for b in r1["books"]]
    ids2 = [b["book_id"] for b in r2["books"]]
    assert len(ids2) == 10
    assert set(ids1).isdisjoint(ids2)
    assert r2["books"][0]["book_id"] == "1187304"
    assert r2["books"][0]["title"] == "三体漫画．7"
    # 第 2 页(共 17 页)仍有下一页
    assert r2["total_pages"] == 17
    assert r2["has_next"] is True


def test_search_empty_yields_zero():
    r = _parse_search(EMPTY)
    assert r["books"] == []
    # 空结果页不渲染总数区,但有明确「暂时没有相关书目」提示锚点 → 判 0(源站明说)
    assert r["total_results"] == 0
    assert r["total_pages"] == 1
    assert r["has_next"] is False


# ---------- 详情页(bkTxt 模板,左右两列 li 标签) ----------


def test_detail_parses_all_fields():
    d = _parse_detail(DETAIL)
    assert set(d) == {"title", "author", "publisher", "publish_year",
                      "isbn", "call_number", "summary"}
    assert d["title"] == "三体：新版"        # bkTxtTit 是完整标题(含副题名)
    assert d["author"] == "刘慈欣"
    assert d["publisher"] == "重庆出版社"    # 首个 a 文本,尾逗号已去
    assert d["publish_year"] == "2022"
    assert d["isbn"] == "978-7-229-16692-2"
    assert d["call_number"] == "I247.55"     # 「版次」之前,同广州口径
    # 简介由第三方 API 异步注入,服务端 HTML 无「内容提要」行 → 空串(NOTES.md)
    assert d["summary"] == ""


def test_detail_stub_yields_no_title():
    # 未找到详情的判定依据:标题为空(与家族 get_book_detail 语义一致)
    assert _parse_detail("<html><body></body></html>")["title"] == ""


# ---------- 馆藏 JSON(与广州同构,家族解析器原样可用) ----------


def test_holding_json_parses_with_family_parser():
    hs = family_parser.parse_holdings(HOLDING)
    assert len(hs) == 5
    # 样例 5 册全部借出(实抓日 2026-10-02),状态原值照登
    assert all(h["status"] == "借出" for h in hs)
    assert all(family_parser.is_available_status(h["status"]) is False for h in hs)
    assert all(h["library"] == "台州市图书馆" for h in hs)
    assert all(h["call_number"] == "I247.55/L597" for h in hs)
    # 应还日期来自 loanWorkMap[barcode].returnDate(epoch 毫秒,UTC+8)
    assert sorted(h["due_date"] for h in hs) == [
        "2026-08-18", "2026-09-22", "2026-10-05", "2026-10-17", "2026-10-28",
    ]
    # 馆藏地点含地铁线与信阅柜等自助网点(localMap 翻译,原值照登)
    assert "S1线南屏站" in [h["location"] for h in hs]
