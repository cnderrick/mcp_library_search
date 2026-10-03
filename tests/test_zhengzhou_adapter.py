"""郑州适配器测试：config 正确、委托 sirsi_ent 家族、契约缝生效。

郑州已注册进 _ADAPTERS（tests/test_adapter_contract.py 覆盖它），本文件作城市级补充钉子。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import zhengzhou
from mcp_library_search.sirsi_ent import SirsiEntConfig


def test_config():
    assert zhengzhou._CONFIG == SirsiEntConfig(
        city="zhengzhou", name_cn="郑州图书馆",
        base_url="http://123.15.53.180:62280")


def test_delegation(monkeypatch):
    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 23312, "page": 2, "total_pages": 1943, "has_next": True,
                "books": [{"book_id": "ent://SD_ILS/2207/SD_ILS:2207712", "title": "三体",
                           "author": "刘慈欣", "publisher": "", "publish_year": "",
                           "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.sirsi_ent.search_books", fake)
    page = zhengzhou.search_books("三体", page=2, limit=12)
    assert page["total_results"] == 23312
    assert page["books"][0]["book_id"] == "ent://SD_ILS/2207/SD_ILS:2207712"
    assert seen["cfg"] == SirsiEntConfig(
        city="zhengzhou", name_cn="郑州图书馆",
        base_url="http://123.15.53.180:62280")
    assert seen["args"] == ("三体", 2, 12)
    base.validate_search_page(page)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("郑州图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.sirsi_ent.search_books", boom)
    with pytest.raises(RuntimeError, match="郑州图书馆"):
        zhengzhou.search_books("三体")


def test_contract_seam(monkeypatch):
    client = Mock()
    client.search.return_value = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 1, "page": 1, "total_pages": 1, "has_next": False},
        books=[SimpleNamespace(record_id="ent://SD_ILS/2207/SD_ILS:2207712", title="三体",
                               author="刘慈欣", publisher="重庆出版社", publish_year="2008",
                               availability_summary="", isbn="9787536692930",
                               call_number="I247.55", summary="...")])
    monkeypatch.setattr(zhengzhou, "_client", client)
    page = zhengzhou.search_books("三体")
    assert page["books"][0]["book_id"] == "ent://SD_ILS/2207/SD_ILS:2207712"
    base.validate_search_page(page)
