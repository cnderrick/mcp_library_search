"""来宾适配器测试：config 正确、委托 interlib 家族、契约缝生效。

来宾已注册进 _ADAPTERS（tests/test_adapter_contract.py 覆盖它），本文件作城市级补充钉子。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import laibin


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.interlib import InterlibConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 15, "page": 1, "total_pages": 1, "has_next": False,
                "books": [{"book_id": "248234", "title": "三体：新版",
                           "author": "刘慈欣著", "publisher": "重庆出版社",
                           "publish_year": "2022", "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake)
    page = laibin.search_books("三体", page=1, limit=20)
    assert page["total_results"] == 15
    assert page["books"][0]["book_id"] == "248234"
    assert seen["cfg"] == InterlibConfig(
        city="laibin", name_cn="来宾市图书馆",
        base_url="http://180.141.168.199:8086", api_detail=True)
    assert seen["args"] == ("三体", 1, 20)
    base.validate_search_page(page)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("来宾市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.interlib.search_books", boom)
    with pytest.raises(RuntimeError, match="来宾市图书馆"):
        laibin.search_books("三体")


def test_contract_seam(monkeypatch):
    client = Mock()
    client.search.return_value = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 1, "page": 1, "total_pages": 1, "has_next": False},
        books=[SimpleNamespace(record_id="248234", title="三体：新版", author="刘慈欣著",
                               publisher="重庆出版社", publish_year="2022",
                               availability_summary="", isbn="978-7-229-16692-2",
                               call_number="I247.55", summary="")]
    )
    monkeypatch.setattr(laibin, "_client", client)
    page = laibin.search_books("三体")
    assert page["books"][0]["book_id"] == "248234"
    base.validate_search_page(page)
