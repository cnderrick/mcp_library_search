"""苏州工业园区图书馆 fixture 解析测试：家族 parser 直打实抓页面。

字段侦察结论见 tests/fixtures/suzhou_sip/NOTES.md（解析以它为准）。
苏州工业园区图书馆与广州/苏州同款 Interlib 默认（非 pro2018）模板，零 quirk。
"""
import json
import re
from pathlib import Path

from mcp_library_search.interlib.parser import (
    is_available_status,
    parse_detail,
    parse_holdings,
    parse_search,
)

FIXTURES = Path(__file__).parent / "fixtures" / "suzhou_sip"

INDEX = (FIXTURES / "index.html").read_text(encoding="utf-8")
SEARCH_P1 = (FIXTURES / "search_p1.html").read_text(encoding="utf-8")
SEARCH_EMPTY = (FIXTURES / "search_empty.html").read_text(encoding="utf-8")
DETAIL = (FIXTURES / "detail.html").read_text(encoding="utf-8")
HOLDING = json.loads((FIXTURES / "holding.json").read_text(encoding="utf-8"))


def test_interlib_fingerprint():
    assert "interlib" in INDEX.lower()
    assert "图创" in INDEX
    assert "苏州工业园区图书馆" in INDEX
    assert "<title>检索系统</title>" in INDEX


def test_search_p1_parses_books_with_stable_ids():
    r = parse_search(SEARCH_P1)
    assert len(r["books"]) == 10
    for b in r["books"]:
        assert set(b) == {"book_id", "title", "author", "publisher",
                          "publish_year", "availability_summary", "isbn"}
        assert b["book_id"].isdigit()
        assert b["title"]
    first = r["books"][0]
    assert first["book_id"] == "872372"
    assert first["title"] == "一说《三体》：《三体》中的前沿科学漫谈"
    assert first["author"] == "王一"
    assert first["publisher"] == "人民邮电出版社"
    assert first["publish_year"] == "2023"
    assert first["isbn"] == "978-7-115-60591-7"


def test_search_pagination_semantics():
    r = parse_search(SEARCH_P1)
    assert r["total_results"] == 98
    assert r["total_pages"] == 10
    assert r["has_next"] is True


def test_empty_search_yields_nothing():
    r = parse_search(SEARCH_EMPTY)
    assert r["books"] == []
    assert r["total_results"] == 0
    assert r["has_next"] is False
    assert r["total_pages"] == 1
    assert "检索到: 0 条结果" in SEARCH_EMPTY
    assert not re.search(r"bookDetail\(\d+", SEARCH_EMPTY)


def test_detail_parses_bibliographic_fields():
    d = parse_detail(DETAIL)
    assert d["title"] == "一说《三体》：《三体》中的前沿科学漫谈"
    assert d["author"] == "王一"
    assert d["publisher"] == "人民邮电出版社"
    assert d["publish_year"] == "2023"
    assert d["isbn"] == "978-7-115-60591-7"
    assert d["call_number"] == "I207.425"
    assert d["summary"].startswith("本书围绕科幻小说《三体》世界观展开")


def test_holdings_parse_maps_codes_and_due_dates():
    hs = parse_holdings(HOLDING)
    assert len(hs) == 4
    for h in hs:
        assert set(h) == {"library", "location", "call_number", "status", "due_date"}
    assert all(h["library"] == "工业园区图书馆" for h in hs)
    assert all(h["call_number"] == "N49/681" for h in hs)
    avail = [h for h in hs if is_available_status(h["status"])]
    assert len(avail) == 1
    loaned = [h for h in hs if h["status"] == "借出"]
    assert len(loaned) == 3
    assert {h["due_date"] for h in loaned} == {"2026-10-21", "2025-06-28", "2026-10-05"}
    assert "东部市民中心分馆" in {h["location"] for h in hs}


def test_availability_conservative():
    assert is_available_status("在馆") is True
    for s in ("借出", "编目", "丢失", "剔除", "交换", "赠送", "装订", "锁定",
              "预借", "清点", "闭架", "修补", "查找中", "重复锁定", "运回中",
              "已签收", "已通还", "报废", "丢失赔书", "已装订", "流通还回上架中"):
        assert is_available_status(s) is False
