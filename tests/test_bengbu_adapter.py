"""蚌埠适配器测试：config 正确、委托 tccopac 家族、契约缝生效、fixture 可解析。

蚌埠实抓为图创 tcc-opac（`opac-remould` Vue SPA＋纯 JSON＋JWT 访客令牌），
非 Interlib，复用 tccopac/ 家族。已注册进 _ADAPTERS，本文件作城市级补充钉子。
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search import tccopac
from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import bengbu
from mcp_library_search.tccopac import TccOpacConfig

_FIX = Path(__file__).parent / "fixtures" / "bengbu"


def test_config_and_delegation(monkeypatch):
    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 32, "page": 1, "total_pages": 2, "has_next": True,
                "books": [{"book_id": "992392878256480305", "title": "三体",
                           "author": "刘慈欣著", "publisher": "重庆出版社",
                           "publish_year": "2008", "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.tccopac.search_books", fake)
    page = bengbu.search_books("三体", page=1, limit=20)
    assert page["total_results"] == 32
    assert page["books"][0]["book_id"] == "992392878256480305"
    assert seen["cfg"] == TccOpacConfig(
        city="bengbu", name_cn="蚌埠市图书馆",
        base_url="http://58.242.164.105:8090/api/tcc-opac/999",
        referer="http://58.242.164.105:8090/999")
    assert seen["args"] == ("三体", 1, 20)
    base.validate_search_page(page)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("蚌埠市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.tccopac.search_books", boom)
    with pytest.raises(RuntimeError, match="蚌埠市图书馆"):
        bengbu.search_books("三体")


def test_contract_seam(monkeypatch):
    client = Mock()
    client.search.return_value = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 1, "page": 1, "total_pages": 1, "has_next": False},
        books=[SimpleNamespace(record_id="992392878256480305", title="三体",
                               author="刘慈欣著", publisher="重庆出版社",
                               publish_year="2008", availability_summary="",
                               isbn="978-7-5366-9293-0", call_number="",
                               summary="")]
    )
    monkeypatch.setattr(bengbu, "_client", client)
    page = bengbu.search_books("三体")
    assert page["books"][0]["book_id"] == "992392878256480305"
    base.validate_search_page(page)


def test_fixtures_parse():
    # tcc-opac 协议：numFound 字符串、bookList[]；详情报文在 data.biblios，
    # 馆藏在 data.records[]。样本实抓见 fixtures/bengbu/NOTES.md。
    p = tccopac.parser.parse_search(
        json.loads((_FIX / "search_santi.json").read_text(encoding="utf-8")))
    assert p["total_results"] == 32
    assert p["books"][0]["book_id"] == "992392878256480305"
    assert p["books"][0]["title"] == "三体"
    assert p["books"][0]["author"] == "刘慈欣著"
    assert p["books"][0]["availability_summary"] == ""  # 检索条目无馆藏概况（数据边界）
    e = tccopac.parser.parse_search(
        json.loads((_FIX / "search_empty.json").read_text(encoding="utf-8")))
    assert e["total_results"] == 0 and e["books"] == []
    det = tccopac.parser.parse_detail(
        json.loads((_FIX / "detail.json").read_text(encoding="utf-8")),
        "992392878256480305")
    assert det["title"] == "三体"
    assert det["author"] == "刘慈欣著"
    assert det["isbn"] == "978-7-5366-9293-0"
    assert det["publish_year"] == "2008"
    assert det["call_number"] == ""  # shelfno 为 null，classno 分类号不冒充索书号
    hs = tccopac.parser.parse_holdings(
        json.loads((_FIX / "holdings.json").read_text(encoding="utf-8")))
    assert hs and hs[0]["library"] == "蚌埠市图书馆"
    assert any(h["available"] for h in hs)
    assert any(h["due_date"] for h in hs)
