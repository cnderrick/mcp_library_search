"""郑州（SirsiDynix Enterprise）fixture 解析测试（2026-10-03）。

字段侦察结论见 tests/fixtures/zhengzhou/NOTES.md（解析以它为准）。
"""
import json
from pathlib import Path

from mcp_library_search.sirsi_ent import parser

FIXTURES = Path(__file__).parent / "fixtures" / "zhengzhou"

INDEX = (FIXTURES / "index.html").read_text(encoding="utf-8")
SEARCH = (FIXTURES / "search_santi.html").read_text(encoding="utf-8")
SEARCH_EMPTY = (FIXTURES / "search_empty.html").read_text(encoding="utf-8")
DETAIL = (FIXTURES / "detail_santi.html").read_text(encoding="utf-8")
HOLDING = json.loads((FIXTURES / "holding.json").read_text(encoding="utf-8"))


def test_fingerprint():
    assert "com_sirsi_ent_widgets" in INDEX
    assert "SirsiDynix" in INDEX or "sirsidynix" in INDEX.lower()
    assert "<title>Home Room</title>" in INDEX


def test_search_parses():
    r = parser.parse_search(SEARCH)
    assert r["total_results"] == 23312
    assert len(r["books"]) == 12
    first = r["books"][0]
    assert first["book_id"] == "ent://SD_ILS/2207/SD_ILS:2207712"
    assert first["title"] == "三体"
    assert first["author"] == "刘慈欣"
    assert first["isbn"] == "9787536692930"
    # 检索页不渲染出版社/出版年
    assert first["publisher"] == "" and first["publish_year"] == ""


def test_empty_search():
    r = parser.parse_search(SEARCH_EMPTY)
    assert r["total_results"] == 0
    assert r["books"] == []


def test_detail_parses():
    d = parser.parse_detail(DETAIL)
    assert d["title"] == "三体"
    assert d["author"] == "刘慈欣"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2008"
    assert d["isbn"] == "9787536692930"
    assert d["call_number"] == "I247.55-YC/ 37"
    assert d["summary"] == "“地球往事”三部曲之一"


def test_holdings_inline_plus_availability():
    hs = parser.parse_holdings(DETAIL, HOLDING)
    assert len(hs) == 5
    for h in hs:
        assert h["library"] == "永城馆流通书库"
        assert h["call_number"] == "I247.55-YC/ 37"
        assert h["status"] == "永城馆流通书库"
        assert h["available"] is True
        assert h["due_date"] == ""


def test_holdings_borrowed_due_date():
    # 「到期 24-3-8」→ 不可借 + 归一应还日期
    html = ('<tr class="detailItemsTableRow"><td>流通书</td><td>B1</td>'
            '<td>I247.5/1</td><td>正在检索...</td></tr>')
    avail = {"ids": ["B1"], "strings": ["到期 24-3-8"], "totalAvailable": 0}
    hs = parser.parse_holdings(html, avail)
    assert hs[0]["available"] is False
    assert hs[0]["due_date"] == "2024-03-08"
    assert hs[0]["library"] == ""


def test_decode_ent():
    assert parser.decode_ent("ent:$002f$002fSD_ILS$002f2207$002fSD_ILS:2207712") == \
        "ent://SD_ILS/2207/SD_ILS:2207712"
