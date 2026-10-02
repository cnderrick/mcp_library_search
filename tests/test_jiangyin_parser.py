"""江阴 fixture 解析测试：家族 parser 直打江阴实抓页面，钉死结构兼容与差异。

字段侦察结论见 tests/fixtures/jiangyin/NOTES.md（解析以它为准）。
江阴与广州同模板：bookmeta/bookrecno 容器、class 锚点、bookInfoTable、
馆藏 Ajax JSON（/opac/api/holding/{bookrecno}）全部同构，无需 quirk 字段。
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

FIXTURES = Path(__file__).parent / "fixtures" / "jiangyin"

SEARCH_P1 = (FIXTURES / "search_p1.html").read_text(encoding="utf-8")
SEARCH_EMPTY = (FIXTURES / "search_empty.html").read_text(encoding="utf-8")
DETAIL = (FIXTURES / "detail.html").read_text(encoding="utf-8")
HOLDING = json.loads((FIXTURES / "holding.json").read_text(encoding="utf-8"))


def test_interlib_fingerprint():
    # 详情页带 interlib 指纹，馆藏走 JSON 接口（与广州/杭州同款模板）
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
    # 钉死第一条（值以实抓 fixture 为准；该记录是《三体》的导读 companion 作品）
    assert r["books"][0]["book_id"] == "1139334"
    assert r["books"][0]["title"] == "《三体》导读"
    assert r["books"][0]["author"] == "詹琰，路姜波著"
    assert r["books"][0]["publisher"] == "天津人民出版社"
    assert r["books"][0]["publish_year"] == "2016"
    # isbn 来自条目后随 expressServiceTab 的 express_isbn 属性（内部字段）
    assert r["books"][0]["isbn"] == "978-7-201-10892-6"
    # 正主也在页内（三体：典藏版）
    ids = [b["book_id"] for b in r["books"]]
    assert "1167504" in ids


def test_search_pagination_semantics():
    r = parse_search(SEARCH_P1)
    assert r["total_results"] == 82
    assert r["total_pages"] == 9
    assert r["has_next"] is True


def test_empty_search_yields_nothing():
    r = parse_search(SEARCH_EMPTY)
    assert r["books"] == []
    assert r["total_results"] == 0
    assert r["has_next"] is False
    # 无分页控件时 total_pages 保守取 1
    assert r["total_pages"] == 1
    # 江阴空结果页连 bookDetail(数字 锚点都没有（杭州空页含 JS 函数定义
    # function bookDetail(bookrecno,...)，江阴无此定义，更干净）
    assert not re.search(r"bookDetail\(\d+", SEARCH_EMPTY)
    assert "检索到: 0 条结果" in SEARCH_EMPTY


def test_detail_parses_bibliographic_fields():
    d = parse_detail(DETAIL)
    # 标题在 data-sort=0 行的首个 h2（与广州同构）
    assert d["title"] == "《三体》导读"
    assert d["publisher"] == "天津人民出版社"
    assert d["publish_year"] == "2016"
    assert d["isbn"] == "978-7-201-10892-6"
    # 江阴详情页同样没有独立索书号字段，call_number 取「中图分类法」值
    # （完整索书号 I207.4/247 在馆藏 JSON 的 callno 里）
    assert d["call_number"] == "I207.4"
    assert d["summary"].startswith("本书意在对《三体》三部曲进行全方位简化解读")


def test_detail_author_not_polluted_by_tag_row():
    # 家族 parser stale-label 缺陷已于 2026-10-02 修复（interlib/parser.py
    # _finish_value 标签一对一消费）：tagTr「没有标签」不再污染 author，
    # 正确值为最后一个「主要责任者」行首个 <a> 文本
    d = parse_detail(DETAIL)
    assert d["author"] == "路姜波"


def test_holdings_parse_maps_codes_and_due_dates():
    hs = parse_holdings(HOLDING)
    assert len(hs) == 8
    for h in hs:
        assert set(h) == {"library", "location", "call_number", "status", "due_date"}
    first = hs[0]
    # libcodeMap[JYLIB] 原值是「江阴图书馆」（与馆名全称「江阴市图书馆」不同，原值照登）
    assert first["library"] == "江阴图书馆"
    assert first["location"] == "月城水韵社区（24H）"
    assert first["call_number"] == "I207.4/247"
    assert first["status"] == "在馆"
    # 借出样例：应还日期来自 loanWorkMap[barcode].returnDate（epoch 毫秒，UTC+8）。
    # 2024-10-06 相对抓取日已过期，原值照登不判断
    loaned = [h for h in hs if h["status"] == "借出"]
    assert len(loaned) == 2
    assert {h["due_date"] for h in loaned} == {"2024-10-06", "2026-12-23"}
    # 分馆翻译：农家书屋/青阳高中分馆等非 JYLIB 馆码也经 libcodeMap 出馆名
    assert any(h["library"] == "农家书屋" for h in hs)
    assert any(h["library"] == "青阳高中分馆" for h in hs)


def test_availability_conservative_for_jiangyin_states():
    # 江阴 holdStateMap 实抓 23 态：只有「在馆」命中可借词；
    # 词表外状态（已签收/已通还/报废/已装订/锁定/清点/修补/查找中/重复锁定/运回中）
    # 一律保守判不可借——不做「已通还＝在架」类预设
    assert is_available_status("在馆") is True
    for s in ("借出", "已签收", "已通还", "报废", "丢失赔书", "已装订", "装订",
              "锁定", "清点", "修补", "查找中", "重复锁定", "运回中", "馆际丢失",
              "流通还回上架中", "编目", "丢失", "剔除", "交换", "赠送", "预借",
              "闭架"):
        assert is_available_status(s) is False
