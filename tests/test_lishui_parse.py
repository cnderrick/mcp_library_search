"""丽水 fixture 解析测试：家族 parser 直打丽水实抓页面，钉死 pro2018 结构兼容。

字段侦察结论见 tests/fixtures/lishui/NOTES.md（解析以它为准）。
丽水与台州/成都/绍兴同为 Interlib pro2018 模板代，家族 parser 零 quirk。
"""
import json
from pathlib import Path

from mcp_library_search.interlib.parser import (
    is_available_status,
    parse_detail_pro2018,
    parse_holdings,
    parse_search_pro2018,
)

FIXTURES = Path(__file__).parent / "fixtures" / "lishui"

INDEX = (FIXTURES / "index.html").read_text(encoding="utf-8")
SEARCH_P1 = (FIXTURES / "search_p1.html").read_text(encoding="utf-8")
SEARCH_EMPTY = (FIXTURES / "search_empty.html").read_text(encoding="utf-8")
DETAIL = (FIXTURES / "detail.html").read_text(encoding="utf-8")
HOLDING = json.loads((FIXTURES / "holding.json").read_text(encoding="utf-8"))


def test_interlib_fingerprint():
    assert "interlib" in INDEX.lower()
    assert "图创" in INDEX
    assert "丽水市公共图书馆" in INDEX
    assert "<title>检索系统</title>" in INDEX


def test_search_p1_parses_books_with_stable_ids():
    r = parse_search_pro2018(SEARCH_P1)
    assert len(r["books"]) == 10
    for b in r["books"]:
        assert set(b) == {"book_id", "title", "author", "publisher",
                          "publish_year", "availability_summary", "isbn"}
        assert b["book_id"].isdigit()
        assert b["title"]
    first = r["books"][0]
    assert first["book_id"] == "181917"
    assert first["title"] == "三体X"
    assert first["author"] == "宝树著"
    assert first["publisher"] == "重庆出版社"
    assert first["publish_year"] == "2015"
    assert first["isbn"] == "978-7-229-10063-6"


def test_search_pagination_semantics():
    r = parse_search_pro2018(SEARCH_P1)
    assert r["total_results"] == 535
    assert r["total_pages"] == 54
    assert r["has_next"] is True


def test_empty_search_yields_nothing():
    r = parse_search_pro2018(SEARCH_EMPTY)
    assert r["books"] == []
    assert r["total_results"] == 0
    assert r["has_next"] is False
    assert r["total_pages"] == 1


def test_detail_parses_bibliographic_fields():
    d = parse_detail_pro2018(DETAIL)
    assert d["title"] == "三体：新版"
    assert d["author"] == "刘慈欣"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2022"
    assert d["isbn"] == "978-7-229-16692-2"
    # 详情页无独立索书号字段，call_number 取「中图分类法」值
    assert d["call_number"] == "I247.55"
    # 该记录无内容提要 → 空串（数据边界）
    assert d["summary"] == ""


def test_holdings_parse_maps_codes_and_due_dates():
    hs = parse_holdings(HOLDING)
    assert len(hs) == 4
    for h in hs:
        assert set(h) == {"library", "location", "call_number", "status", "due_date"}
    avail = [h for h in hs if is_available_status(h["status"])]
    assert len(avail) == 3
    loaned = [h for h in hs if h["status"] == "借出"]
    assert len(loaned) == 1
    assert loaned[0]["due_date"] == "2026-08-07"
    # 馆名经 libcodeMap 翻译成中文，含县级馆与乡镇阅读驿站
    assert "庆元县图书馆" in {h["library"] for h in hs}
    assert all(h["library"] and h["location"] and h["call_number"] for h in hs)


def test_availability_conservative_for_lishui_states():
    assert is_available_status("在馆") is True
    for s in ("借出", "编目", "丢失", "剔除", "交换", "赠送", "装订", "锁定",
              "预借", "清点", "闭架", "修补", "查找中", "重复锁定", "运回中",
              "已签收", "已通还", "报废", "丢失赔书", "已装订",
              "流通还回上架中"):
        assert is_available_status(s) is False
