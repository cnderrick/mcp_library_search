"""苏州工业园区图书馆适配器测试：config、委托 interlib 家族、契约缝生效。

已注册进 _ADAPTERS（tests/test_adapter_contract.py 覆盖它）；本文件作城市级补充钉子。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import suzhou_sip


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.interlib import InterlibConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 98, "page": 1, "total_pages": 10, "has_next": True,
                "books": [{"book_id": "872372", "title": "一说《三体》",
                           "author": "王一", "publisher": "人民邮电出版社",
                           "publish_year": "2023", "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake)
    page = suzhou_sip.search_books("三体", page=2, limit=5)
    assert page["total_results"] == 98
    assert page["books"][0]["book_id"] == "872372"
    assert seen["cfg"] == InterlibConfig(
        city="suzhou_sip", name_cn="苏州工业园区图书馆",
        base_url="http://opac.sdll.cn:8088")
    assert seen["args"] == ("三体", 2, 5)
    base.validate_search_page(page)


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "工业园区图书馆", "location": "科技阅览室",
             "call_number": "N49/681", "status": "在馆",
             "available": True, "due_date": ""},
            {"library": "工业园区图书馆", "location": "网借书库（联创产业园）",
             "call_number": "N49/681", "status": "借出",
             "available": False, "due_date": "2026-10-21"},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "一说《三体》",
                              "author": "王一", "publisher": "人民邮电出版社",
                              "publish_year": "2023", "isbn": "978-7-115-60591-7",
                              "call_number": "I207.425", "summary": "…"},
    )
    hs = suzhou_sip.get_holdings("872372", only_available=False)
    assert hs[0]["library"] == "工业园区图书馆"
    assert [h["available"] for h in hs] == [True, False]
    base.validate_holdings(hs)
    d = suzhou_sip.get_book_detail("872372")
    assert d["title"] == "一说《三体》"
    assert d["book_id"] == "872372"
    base.validate_book_detail(d)


def test_only_available_filters(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "工业园区图书馆", "location": "", "call_number": "",
             "status": "在馆", "available": True, "due_date": ""},
            {"library": "工业园区图书馆", "location": "", "call_number": "",
             "status": "借出", "available": False, "due_date": "2026-10-21"},
        ],
    )
    hs = suzhou_sip.get_holdings("872372", only_available=True)
    assert len(hs) == 1 and hs[0]["status"] == "在馆"
    base.validate_holdings(hs)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("苏州工业园区图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.interlib.search_books", boom)
    with pytest.raises(RuntimeError, match="苏州工业园区图书馆"):
        suzhou_sip.search_books("三体")


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(suzhou_sip, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="872372", title="一说《三体》", author="王一",
        publisher="人民邮电出版社", publish_year="2023", availability_summary="有馆藏",
        isbn="978-7-115-60591-7", call_number="I207.425", summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_contract_seam(monkeypatch):
    result = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="937281", title="三体漫画．接触．上")],
    )
    _patch_client(monkeypatch, search=result)
    page = suzhou_sip.search_books("三体")
    assert page["books"][0]["book_id"] == "872372"
    assert page["books"][1]["book_id"] == "937281"
    base.validate_search_page(page)
