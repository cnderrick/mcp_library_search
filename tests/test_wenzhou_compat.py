"""温州 OPAC 结构与 Interlib 家族解析器的兼容性证据（打实抓 fixture，不打真网）。

温州与广州/杭州同款图创 Interlib 模板，家族 parse_search/parse_detail/parse_holdings
应零改动可用；本文件用 tests/fixtures/wenzhou/ 的实抓页面钉住这一事实，
并钉住温州的 quirk 与数据边界。字段侦察结论详见 tests/fixtures/wenzhou/NOTES.md。
"""
import json
import re
from pathlib import Path

from mcp_library_search.interlib import parser

FIXTURES = Path(__file__).parent / "fixtures" / "wenzhou"

SEARCH = (FIXTURES / "search_p1.html").read_text(encoding="utf-8")
EMPTY = (FIXTURES / "search_empty.html").read_text(encoding="utf-8")
DETAIL = (FIXTURES / "detail.html").read_text(encoding="utf-8")
DETAIL_NO_AUTHOR = (FIXTURES / "detail_no_primary_author.html").read_text(encoding="utf-8")
HOLDING = json.loads((FIXTURES / "holding.json").read_text(encoding="utf-8"))
HOLDING_EMPTY = json.loads((FIXTURES / "holding_empty.json").read_text(encoding="utf-8"))


def test_interlib_fingerprint():
    # meta keywords「opac, 图创, interlib」+ footer www.interlib.com.cn（图创版权）
    assert "interlib" in SEARCH.lower()
    assert "interlib" in DETAIL.lower()
    assert "图创" in SEARCH


def test_search_parses_with_family_parser():
    r = parser.parse_search(SEARCH)
    assert r["total_results"] == 237
    assert r["total_pages"] == 24
    assert r["has_next"] is True
    assert len(r["books"]) == 10
    first = r["books"][0]
    assert first["book_id"] == "2006188837"
    assert first["title"] == "一说《三体》：《三体》中的前沿科学漫谈"
    assert first["author"] == "王一著"
    assert first["publisher"] == "人民邮电出版社"
    assert first["publish_year"] == "2023"
    # express_isbn 内部字段（天津三源归并用）温州同款存在
    assert first["isbn"] == "9787115605917"


def test_search_anchor_is_bookmeta_container():
    # 书目锚点按「bookDetail( 后跟数字」计；结果条数以 bookmeta 容器为准
    assert len(re.findall(r"bookDetail\(\d+", SEARCH)) > 0
    assert SEARCH.count('class="bookmeta"') == 10


def test_empty_page_quirk_same_as_hangzhou():
    # 空结果页含 JS 函数定义 function bookDetail(bookrecno,index,flag){，
    # 裸「bookDetail(」计 1 次但不是书目锚点；家族按 bookmeta 容器解析不受影响。
    assert "检索到: 0 条结果" in EMPTY
    assert EMPTY.count("bookDetail(") == 1
    assert not re.search(r"bookDetail\(\d+", EMPTY)
    r = parser.parse_search(EMPTY)
    assert r["books"] == []
    assert r["total_results"] == 0
    assert r["has_next"] is False


def test_detail_parses_with_family_parser():
    d = parser.parse_detail(DETAIL)
    assert d["title"] == "三体漫画．起源"
    assert d["author"] == "刘慈欣"          # 「主要责任者」行第一个 <a> 文本
    assert d["publisher"] == "浙江文艺出版社"
    assert d["publish_year"] == "2024"
    assert d["isbn"] == "978-7-5339-7402-2"
    assert d["call_number"] == "J228.2"     # 「中图分类法」取「版次」前文本
    assert d["summary"].startswith("本书讲述了：汪淼")


def test_detail_no_primary_author_is_data_boundary():
    # 该书目 MARC 无「主要责任者」「内容提要」行（记录级差异，非站点 quirk）：
    # author/summary 空串是数据边界，广州遇同款记录行为相同。
    d = parser.parse_detail(DETAIL_NO_AUTHOR)
    assert d["title"] == "一说《三体》：《三体》中的前沿科学漫谈"
    assert d["author"] == ""
    assert d["summary"] == ""
    assert d["isbn"] == "9787115605917"
    assert d["publisher"] == "人民邮电出版社"
    assert d["publish_year"] == "2023"


def test_detail_without_author_rows_call_number_not_polluted():
    # 家族 parser 的 tagTr 标签悬挂污染已于 2026-10-02 修复（interlib/parser.py
    # _finish_value 标签一对一消费）：「标签」行值「没有标签」不再挂到
    # 「中图分类法」名下，call_number 取回正确值 Z228
    d = parser.parse_detail(DETAIL_NO_AUTHOR)
    assert d["call_number"] == "Z228"


def test_holdings_parse_with_family_parser():
    hs = parser.parse_holdings(HOLDING)
    assert len(hs) == 21
    # 12 在馆（可借）+ 9 借出（不可借），状态词表全部命中，无一落到保守判定
    avail = [h for h in hs if parser.is_available_status(h["status"])]
    loaned = [h for h in hs if h["status"] == "借出"]
    assert len(avail) == 12
    assert len(loaned) == 9
    # loanWorkMap[barcode].returnDate epoch 毫秒 → YYYY-MM-DD 归一，借出单册全带
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", h["due_date"]) for h in loaned)
    # 馆名/位置经 libcodeMap/localMap 翻译成中文，不是代码
    assert "温图市府路馆" in {h["library"] for h in hs}
    assert all(h["library"] and h["location"] and h["call_number"] for h in hs)


def test_holding_empty_is_data_fact_not_failure():
    # 仅虚拟电子书的书目无实体单册：holdingList 空但 maps 齐全，返回空列表是数据事实
    assert HOLDING_EMPTY["holdingList"] == []
    assert HOLDING_EMPTY["libcodeMap"]
    assert parser.parse_holdings(HOLDING_EMPTY) == []
