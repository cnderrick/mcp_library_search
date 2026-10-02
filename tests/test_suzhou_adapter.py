"""苏州适配器测试：config 正确、委托 interlib 家族、契约缝生效。

苏州已注册进 _ADAPTERS（tests/test_adapter_contract.py 覆盖它）；本文件的
输出结构自断言保留，作为城市级的补充钉子（2026-10-03 接入）。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import suzhou


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.interlib import InterlibConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 232, "page": 1, "total_pages": 24, "has_next": True,
                "books": [{"book_id": "1006429505", "title": "三体：典藏版",
                           "author": "刘慈欣著", "publisher": "重庆出版社",
                           "publish_year": "2016", "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake)
    page = suzhou.search_books("三体", page=2, limit=5)
    assert page["total_results"] == 232
    # 家族 book_id → 契约 record_id 的映射在 _Client.search 内完成，
    # 必须用非空 books 覆盖
    assert page["books"][0]["book_id"] == "1006429505"
    assert page["books"][0]["title"] == "三体：典藏版"
    assert seen["cfg"] == InterlibConfig(
        city="suzhou", name_cn="苏州图书馆", base_url="https://reader.szlib.com"
    )
    assert seen["args"] == ("三体", 2, 5)
    base.validate_search_page(page)


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "苏图", "location": "一馆综合室(三楼)",
             "call_number": "I247.55/1121", "status": "在馆",
             "available": True, "due_date": ""},
            {"library": "苏图", "location": "北馆书库",
             "call_number": "I247.55/1121", "status": "借出",
             "available": False, "due_date": "2026-10-31"},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "三体：图像小说",
                              "author": "刘慈欣", "publisher": "译林出版社",
                              "publish_year": "2025", "isbn": "978-7-5753-0280-7",
                              "call_number": "I247.55", "summary": "…"},
    )
    hs = suzhou.get_holdings("1006489923", only_available=False)
    assert hs[0]["library"] == "苏图"
    assert hs[0]["available"] is True
    # 可借的排前面
    assert [h["available"] for h in hs] == [True, False]
    base.validate_holdings(hs)
    d = suzhou.get_book_detail("1006489923")
    assert d["title"] == "三体：图像小说"
    assert d["book_id"] == "1006489923"
    base.validate_book_detail(d)


def test_only_available_filters(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "苏图", "location": "", "call_number": "",
             "status": "在馆", "available": True, "due_date": ""},
            {"library": "苏图", "location": "", "call_number": "",
             "status": "借出", "available": False, "due_date": "2026-10-31"},
        ],
    )
    hs = suzhou.get_holdings("1006489923", only_available=True)
    assert len(hs) == 1 and hs[0]["status"] == "在馆"
    base.validate_holdings(hs)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("苏州图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.interlib.search_books", boom)
    with pytest.raises(RuntimeError, match="苏州图书馆"):
        suzhou.search_books("三体")


# ---------- 契约缝自断言（镜像 tests/test_adapter_contract.py 的注入形态） ----------


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(suzhou, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="1006429505", title="三体：典藏版", author="刘慈欣著",
        publisher="重庆出版社", publish_year="2016", availability_summary="有馆藏",
        isbn="978-7-229-10060-5", call_number="I247.55/1121", summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_search_books_contract_shape(monkeypatch):
    result = SimpleNamespace(
        success=True,
        error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="1005629854", title="三体：典藏版")],
    )
    _patch_client(monkeypatch, search=result)
    base.validate_search_page(suzhou.search_books("三体"))


def test_get_holdings_contract_shape(monkeypatch):
    holdings = [
        SimpleNamespace(library="苏图", location="一馆综合室(三楼)",
                        call_number="I247.55/1121", status="在馆",
                        is_available=lambda: True, item_id=""),
        SimpleNamespace(library="苏图", location="北馆书库", call_number="",
                        status="借出", is_available=lambda: False, item_id="item-1"),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-10-31")
    base.validate_holdings(suzhou.get_holdings("1006489923", only_available=False))
    client.get_return_date.assert_called_once_with("item-1")


def test_get_book_detail_contract_shape(monkeypatch):
    _patch_client(monkeypatch, get_book_detail=_book())
    base.validate_book_detail(suzhou.get_book_detail("1006429505"))
