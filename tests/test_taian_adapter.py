"""泰安市图书馆适配器测试：config 正确、委托 interlib 家族、契约缝生效。

泰安市图书馆已注册进 _ADAPTERS（tests/test_adapter_contract.py 覆盖它），本文件作城市级补充钉子。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import taian


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.interlib import InterlibConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 26, "page": 1, "total_pages": 2, "has_next": True,
                "books": [{"book_id": "900149166", "title": "三体",
                           "author": "三体", "publisher": "重庆出版社",
                           "publish_year": "2017", "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake)
    page = taian.search_books("三体", page=1, limit=20)
    assert page["total_results"] == 26
    assert page["books"][0]["book_id"] == "900149166"
    assert seen["cfg"] == InterlibConfig(
        city="taian", name_cn="泰安市图书馆",
        base_url="http://112.245.16.82", api_detail=True)
    assert seen["args"] == ("三体", 1, 20)
    base.validate_search_page(page)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("泰安市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.interlib.search_books", boom)
    with pytest.raises(RuntimeError, match="泰安市图书馆"):
        taian.search_books("三体")


def test_contract_seam(monkeypatch):
    client = Mock()
    client.search.return_value = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 1, "page": 1, "total_pages": 1, "has_next": False},
        books=[SimpleNamespace(record_id="900149166", title="三体", author="三体",
                               publisher="重庆出版社", publish_year="2017",
                               availability_summary="", isbn="", call_number="", summary="")]
    )
    monkeypatch.setattr(taian, "_client", client)
    page = taian.search_books("三体")
    assert page["books"][0]["book_id"] == "900149166"
    base.validate_search_page(page)
