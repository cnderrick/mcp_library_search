"""苏州 fixture 解析测试：家族 parser 直打苏州实抓页面，钉死结构兼容与差异。

字段侦察结论见 tests/fixtures/suzhou/NOTES.md（解析以它为准）。
苏州与广州同模板（默认非 pro2018）：bookmeta/bookrecno 容器、class 锚点、
bookInfoTable、馆藏 Ajax JSON（/opac/api/holding/{bookrecno}）全部同构，
无需 quirk 字段。
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

FIXTURES = Path(__file__).parent / "fixtures" / "suzhou"

INDEX = (FIXTURES / "index.html").read_text(encoding="utf-8")
SEARCH_P1 = (FIXTURES / "search_p1.html").read_text(encoding="utf-8")
SEARCH_EMPTY = (FIXTURES / "search_empty.html").read_text(encoding="utf-8")
DETAIL = (FIXTURES / "detail.html").read_text(encoding="utf-8")
HOLDING = json.loads((FIXTURES / "holding.json").read_text(encoding="utf-8"))


def test_interlib_fingerprint():
    # 首页 meta keywords 自报「图创, interlib」；详情页馆藏走 JSON 接口
    assert "interlib" in INDEX.lower()
    assert "图创" in INDEX
    assert "<title>检索系统</title>" in INDEX
    assert "interlib" in DETAIL.lower()
    assert "/opac/api/holding/" in DETAIL


def test_search_p1_parses_books_with_stable_ids():
    r = parse_search(SEARCH_P1)
    assert len(r["books"]) == 10
    for b in r["books"]:
        assert set(b) == {"book_id", "title", "author", "publisher",
                          "publish_year", "availability_summary", "isbn"}
        assert b["book_id"].isdigit()
        assert b["title"]
        assert b["availability_summary"] == ""
    first = r["books"][0]
    assert first["book_id"] == "1006429505"
    assert first["title"] == "三体：典藏版"
    assert first["author"] == "刘慈欣著"
    assert first["publisher"] == "重庆出版社"
    assert first["publish_year"] == "2016"
    # isbn 来自条目后随 expressServiceTab 的 express_isbn 属性（内部字段）
    assert first["isbn"] == "978-7-229-10060-5"
    # 结果条数以 bookmeta 容器为准
    assert SEARCH_P1.count('class="bookmeta"') == 10


def test_search_pagination_semantics():
    r = parse_search(SEARCH_P1)
    assert r["total_results"] == 232
    assert r["total_pages"] == 24
    assert r["has_next"] is True


def test_empty_search_yields_nothing():
    r = parse_search(SEARCH_EMPTY)
    assert r["books"] == []
    assert r["total_results"] == 0
    assert r["has_next"] is False
    # 无分页控件时 total_pages 保守取 1
    assert r["total_pages"] == 1
    assert "检索到: 0 条结果" in SEARCH_EMPTY
    # 苏州空结果页无 bookDetail(数字 书目锚点
    assert not re.search(r"bookDetail\(\d+", SEARCH_EMPTY)


def test_detail_parses_bibliographic_fields():
    d = parse_detail(DETAIL)
    assert d["title"] == "三体：图像小说"
    assert d["author"] == "刘慈欣"
    assert d["publisher"] == "译林出版社"
    assert d["publish_year"] == "2025"
    assert d["isbn"] == "978-7-5753-0280-7"
    # 苏州详情页同样没有独立索书号字段，call_number 取「中图分类法」值
    # （完整索书号 I247.55/1121 在馆藏 JSON 的 callno 里）
    assert d["call_number"] == "I247.55"
    assert d["summary"].startswith("本书改编自科幻巨著《三体》")


def test_holdings_parse_maps_codes_and_due_dates():
    hs = parse_holdings(HOLDING)
    assert len(hs) == 8
    for h in hs:
        assert set(h) == {"library", "location", "call_number", "status", "due_date"}
    first = hs[0]
    # libcodeMap[ST] 原值是「苏图」（苏州图书馆缩写，原值照登）
    assert first["library"] == "苏图"
    assert first["location"] == "一馆外借室(一楼)"
    assert first["call_number"] == "I247.55/1121"
    assert first["status"] == "借出"
    # 借出样例：应还日期来自 loanWorkMap[barcode].returnDate（epoch 毫秒，UTC+8）
    loaned = [h for h in hs if h["status"] == "借出"]
    avail = [h for h in hs if is_available_status(h["status"])]
    assert len(loaned) == 6
    assert len(avail) == 2
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", h["due_date"]) for h in loaned)
    assert first["due_date"] == "2026-04-13"
    # 分馆翻译：渭塘分馆等非 ST 馆码也经 localMap/libcodeMap 出可读名
    assert any(h["location"] == "渭塘分馆" for h in hs)
    assert all(h["library"] and h["location"] and h["call_number"] for h in hs)


def test_availability_conservative_for_suzhou_states():
    # 苏州 holdStateMap 实抓 25 态：只有「在馆」命中可借词；
    # 词表外状态（已签收/已通还/报废/馆际丢失）一律保守判不可借——
    # 不做「已通还＝在架」类预设
    assert is_available_status("在馆") is True
    for s in ("借出", "编目", "丢失", "剔除", "交换", "赠送", "装订", "锁定",
              "预借", "清点", "闭架", "修补", "查找中", "重复锁定", "运回中",
              "已签收", "已通还", "报废", "丢失赔书", "已装订", "调拨",
              "锁定查找中", "共享还回中", "流通还回上架中"):
        assert is_available_status(s) is False
