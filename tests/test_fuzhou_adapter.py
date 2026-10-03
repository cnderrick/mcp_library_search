"""福州适配器测试：config 正确、委托 interlib 家族、契约缝生效、fixture 可解析。

福州已注册进 _ADAPTERS（tests/test_adapter_contract.py 覆盖它），本文件作城市级补充钉子。
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import fuzhou
from mcp_library_search.interlib import InterlibConfig
from mcp_library_search.interlib import parser as ilparser

_FIX = Path(__file__).parent / "fixtures" / "fuzhou"


def test_config_and_delegation(monkeypatch):
    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 138, "page": 1, "total_pages": 7, "has_next": True,
                "books": [{"book_id": "901104374", "title": "三体", "author": "刘慈欣",
                           "publisher": "重庆出版社", "publish_year": "2008",
                           "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake)
    page = fuzhou.search_books("三体", page=1, limit=20)
    assert page["total_results"] == 138
    assert page["books"][0]["book_id"] == "901104374"
    assert seen["cfg"] == InterlibConfig(
        city="fuzhou", name_cn="福州市图书馆",
        base_url="https://opcs.fzlib.org:8082", api_detail=True)
    assert seen["args"] == ("三体", 1, 20)
    base.validate_search_page(page)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("福州市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.interlib.search_books", boom)
    with pytest.raises(RuntimeError, match="福州市图书馆"):
        fuzhou.search_books("三体")


def test_contract_seam(monkeypatch):
    client = Mock()
    client.search.return_value = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 1, "page": 1, "total_pages": 1, "has_next": False},
        books=[SimpleNamespace(record_id="901104374", title="三体", author="刘慈欣",
                               publisher="重庆出版社", publish_year="2008",
                               availability_summary="", isbn="978-7-5366-9293-0",
                               call_number="I247.55", summary="")]
    )
    monkeypatch.setattr(fuzhou, "_client", client)
    page = fuzhou.search_books("三体")
    assert page["books"][0]["book_id"] == "901104374"
    base.validate_search_page(page)


def test_fixtures_parse():
    # 默认模板直连（bookmeta）＋ api_detail；样本实抓见 fixtures/fuzhou/NOTES.md
    p = ilparser.parse_search(
        (_FIX / "search_p1.html").read_text(encoding="utf-8", errors="replace"))
    assert p["total_results"] == 138
    assert p["books"][0]["book_id"] == "901104374"
    assert p["books"][0]["title"] == "三体"
    e = ilparser.parse_search(
        (_FIX / "search_empty.html").read_text(encoding="utf-8", errors="replace"))
    assert e["total_results"] == 0 and e["books"] == []
    det = ilparser.parse_detail_api(
        json.loads((_FIX / "detail_api.json").read_text(encoding="utf-8")))
    assert det["title"] == "三体"
    hs = ilparser.parse_holdings(
        json.loads((_FIX / "holding.json").read_text(encoding="utf-8")))
    assert hs and hs[0]["library"] == "马尾馆"
