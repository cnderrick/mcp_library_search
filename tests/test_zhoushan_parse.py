"""舟山 fixture 解析测试：UILAS 家族 parser 直打舟山实抓页面。

字段侦察结论见 tests/fixtures/zhoushan/NOTES.md（解析以它为准）。
舟山与金华同款 UILAS，解析器在 uilas/ 家族；差异是旧式 TLS 密码套件。
"""
import json
from pathlib import Path

from mcp_library_search import uilas
from mcp_library_search.adapters.cn import zhoushan
from mcp_library_search.uilas import parser

FIXTURES = Path(__file__).parent / "fixtures" / "zhoushan"

INDEX = (FIXTURES / "index.html").read_text(encoding="utf-8")
SEARCH_P1 = (FIXTURES / "search_p1.html").read_text(encoding="utf-8")
SEARCH_EMPTY = (FIXTURES / "search_empty.html").read_text(encoding="utf-8")
DETAIL = (FIXTURES / "detail.html").read_text(encoding="utf-8")
DETAIL_LOAN = (FIXTURES / "detail_loan.html").read_text(encoding="utf-8")


def test_uilas_fingerprint():
    assert "UILAS" in INDEX
    assert "NTRdrBookRetr.do" in INDEX


def test_search_p1_parses_books():
    assert parser.is_result_page(SEARCH_P1)
    r = parser.parse_search(SEARCH_P1)
    assert r["total_results"] == 266
    assert r["total_pages"] == 27
    assert len(r["books"]) == 10
    first = r["books"][0]
    assert first["book_id"] == "1533337"
    assert first["title"] == "不要回答．vol.02．vol.02：太空军"
    assert first["publisher"] == "中信出版集团股份有限公司"
    assert first["publish_year"] == "2026"


def test_empty_search_yields_nothing():
    r = parser.parse_search(SEARCH_EMPTY)
    assert r["books"] == []
    assert r["total_results"] == 0        # 「共有 []条记录」括号空
    assert r["total_pages"] == 1          # 「页码: 1/」无总页数
    assert not parser.is_result_page("<html>不是结果页</html>")


def test_detail_parses_bibliographic_fields():
    d = parser.parse_detail(DETAIL)
    assert d["title"] == "不要回答．vol.02．vol.02：太空军"
    assert d["publisher"] == "中信出版集团股份有限公司"
    assert d["publish_year"] == "2026"
    assert d["isbn"] == "9787521786170"
    assert d["call_number"] == "I247.7"
    assert d["summary"].startswith("本书以“太空军”为主题")


def test_holdings_single_available_copy():
    hs = parser.parse_holdings(DETAIL)
    assert len(hs) == 1
    h = hs[0]
    assert h["library"] == "舟山市图书馆"
    assert h["location"] == "市馆成人外借"
    assert h["call_number"] == "I247.7/471"
    assert h["status"] == "入藏" and h["available"] is True
    assert h["due_date"] == ""


def test_holdings_two_tables_two_states():
    hs = parser.parse_holdings(DETAIL_LOAN)
    assert len(hs) == 2
    assert hs[0]["status"] == "入藏" and hs[0]["available"] is True
    assert hs[1]["status"] == "借出" and hs[1]["available"] is False
    assert all(h["library"] == "定海区图书馆" for h in hs)


def test_bad_book_id_raises():
    import pytest
    with pytest.raises(RuntimeError, match="book_id"):
        parser.check_recno("i_biblios:1", "舟山市图书馆")


# ---------- 旧式 TLS quirk ----------


def test_zhoushan_config_enables_legacy_tls_ciphers():
    assert zhoushan._CONFIG.ssl_ciphers == "AES256-GCM-SHA384:AES128-GCM-SHA256"


def test_opener_for_ciphers_builds_custom_opener():
    # 非空套件串 → 独立 opener（带自定义 HTTPSHandler），且按串缓存
    a = uilas.client._opener_for("AES256-GCM-SHA384:AES128-GCM-SHA256")
    b = uilas.client._opener_for("AES256-GCM-SHA384:AES128-GCM-SHA256")
    plain = uilas.client._opener_for("")
    assert a is b
    assert a is not plain
