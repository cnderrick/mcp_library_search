"""江阴适配器测试：config 正确、委托 interlib 家族、契约缝生效。

江阴暂未注册进 _ADAPTERS（注册由协调者统一处理），tests/test_adapter_contract.py
盖不到它，所以本文件按同款形态自断言输出结构对齐 base.py TypedDict。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters import jiangyin


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.interlib import InterlibConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 82, "page": 1, "total_pages": 9, "has_next": True,
                "books": [{"book_id": "1139334", "title": "《三体》导读",
                           "author": "詹琰，路姜波著", "publisher": "天津人民出版社",
                           "publish_year": "2016", "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake)
    page = jiangyin.search_books("三体", page=2, limit=5)
    assert page["total_results"] == 82
    # 家族 book_id → 契约 record_id 的映射在 _Client.search 内完成（真网冒烟曾抓到此回归），
    # 必须用非空 books 覆盖
    assert page["books"][0]["book_id"] == "1139334"
    assert page["books"][0]["title"] == "《三体》导读"
    assert seen["cfg"] == InterlibConfig(
        city="jiangyin", name_cn="江阴市图书馆", base_url="http://libopac.jylib.cn:9090"
    )
    assert seen["args"] == ("三体", 2, 5)
    base.validate_search_page(page)


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "江阴图书馆", "location": "综合借阅室",
             "call_number": "I207.4/247", "status": "在馆",
             "available": True, "due_date": ""},
            {"library": "江阴图书馆", "location": "华士分馆",
             "call_number": "I207.4/247", "status": "借出",
             "available": False, "due_date": "2026-12-23"},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "《三体》导读",
                              "author": "路姜波", "publisher": "天津人民出版社",
                              "publish_year": "2016", "isbn": "978-7-201-10892-6",
                              "call_number": "I207.4", "summary": "…"},
    )
    hs = jiangyin.get_holdings("1139334", only_available=False)
    assert hs[0]["library"] == "江阴图书馆"
    assert hs[0]["available"] is True
    # 可借的排前面
    assert [h["available"] for h in hs] == [True, False]
    base.validate_holdings(hs)
    d = jiangyin.get_book_detail("1139334")
    assert d["title"] == "《三体》导读"
    assert d["book_id"] == "1139334"
    base.validate_book_detail(d)


def test_only_available_filters(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "江阴图书馆", "location": "", "call_number": "",
             "status": "在馆", "available": True, "due_date": ""},
            {"library": "江阴图书馆", "location": "", "call_number": "",
             "status": "借出", "available": False, "due_date": "2026-12-23"},
        ],
    )
    hs = jiangyin.get_holdings("1139334", only_available=True)
    assert len(hs) == 1 and hs[0]["status"] == "在馆"
    base.validate_holdings(hs)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("江阴市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.interlib.search_books", boom)
    with pytest.raises(RuntimeError, match="江阴市图书馆"):
        jiangyin.search_books("三体")


# ---------- 契约缝自断言（镜像 tests/test_adapter_contract.py 的注入形态） ----------


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(jiangyin, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="1139334", title="《三体》导读", author="路姜波",
        publisher="天津人民出版社", publish_year="2016", availability_summary="有馆藏",
        isbn="978-7-201-10892-6", call_number="I207.4/247", summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_search_books_contract_shape(monkeypatch):
    result = SimpleNamespace(
        success=True,
        error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="1167504", title="三体：典藏版")],
    )
    _patch_client(monkeypatch, search=result)
    base.validate_search_page(jiangyin.search_books("三体"))


def test_get_holdings_contract_shape(monkeypatch):
    holdings = [
        SimpleNamespace(library="江阴图书馆", location="综合借阅室",
                        call_number="I207.4/247", status="在馆",
                        is_available=lambda: True, item_id=""),
        SimpleNamespace(library="青阳高中分馆", location="", call_number="",
                        status="借出", is_available=lambda: False, item_id="item-1"),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-12-23")
    base.validate_holdings(jiangyin.get_holdings("1139334", only_available=False))
    client.get_return_date.assert_called_once_with("item-1")


def test_get_book_detail_contract_shape(monkeypatch):
    _patch_client(monkeypatch, get_book_detail=_book())
    base.validate_book_detail(jiangyin.get_book_detail("1139334"))
