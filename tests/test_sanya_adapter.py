"""三亚适配器测试：config 正确、委托 tccopac 家族、契约缝生效、fixture 可解析。

三亚实抓为图创 tcc-opac（Vue SPA＋纯 JSON＋JWT 访客令牌），非 Interlib，
复用 tccopac/ 家族。已注册进 _ADAPTERS，本文件作城市级补充钉子。
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search import tccopac
from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import sanya
from mcp_library_search.tccopac import TccOpacConfig

_FIX = Path(__file__).parent / "fixtures" / "sanya"


def test_config_and_delegation(monkeypatch):
    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 49, "page": 1, "total_pages": 5, "has_next": True,
                "books": [{"book_id": "1983722455542755330", "title": "三体漫画．起源",
                           "author": "刘慈欣原著", "publisher": "浙江文艺出版社",
                           "publish_year": "2023", "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.tccopac.search_books", fake)
    page = sanya.search_books("三体", page=1, limit=20)
    assert page["total_results"] == 49
    assert page["books"][0]["book_id"] == "1983722455542755330"
    assert seen["cfg"] == TccOpacConfig(
        city="sanya", name_cn="三亚市图书馆",
        base_url="https://opac.sanyalib.com:8888/api/tcc-opac/SY",
        referer="https://opac.sanyalib.com:8888/opac/SY")
    assert seen["args"] == ("三体", 1, 20)
    base.validate_search_page(page)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("三亚市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.tccopac.search_books", boom)
    with pytest.raises(RuntimeError, match="三亚市图书馆"):
        sanya.search_books("三体")


def test_contract_seam(monkeypatch):
    client = Mock()
    client.search.return_value = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 1, "page": 1, "total_pages": 1, "has_next": False},
        books=[SimpleNamespace(record_id="1983722455542755330", title="三体漫画．起源",
                               author="刘慈欣原著", publisher="浙江文艺出版社",
                               publish_year="2023", availability_summary="",
                               isbn="978-7-5339-7402-2", call_number="J228.2/2037:1",
                               summary="")]
    )
    monkeypatch.setattr(sanya, "_client", client)
    page = sanya.search_books("三体")
    assert page["books"][0]["book_id"] == "1983722455542755330"
    base.validate_search_page(page)


def test_fixtures_parse():
    # tcc-opac 协议：numFound 字符串、bookList[]；详情报文在 data.biblios，
    # 馆藏在 data.records[]。样本实抓见 fixtures/sanya/NOTES.md。
    p = tccopac.parser.parse_search(
        json.loads((_FIX / "search_santi.json").read_text(encoding="utf-8")))
    assert p["total_results"] == 49
    assert p["books"][0]["book_id"] == "1983722455542755330"
    assert p["books"][0]["title"] == "三体漫画．起源"
    e = tccopac.parser.parse_search(
        json.loads((_FIX / "search_empty.json").read_text(encoding="utf-8")))
    assert e["total_results"] == 0 and e["books"] == []
    det = tccopac.parser.parse_detail(
        json.loads((_FIX / "detail.json").read_text(encoding="utf-8")),
        "1983722455542755330")
    assert det["title"] == "三体漫画．起源"
    hs = tccopac.parser.parse_holdings(
        json.loads((_FIX / "holdings.json").read_text(encoding="utf-8")))
    assert hs and hs[0]["library"] == "三亚市图书馆"
    assert any(h["available"] for h in hs)
