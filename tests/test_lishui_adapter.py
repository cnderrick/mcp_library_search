"""丽水适配器测试：config 正确（pro2018）、委托 interlib 家族、契约缝生效。

丽水已注册进 _ADAPTERS（tests/test_adapter_contract.py 覆盖它）；本文件的
输出结构自断言保留，作为城市级的补充钉子（2026-10-03 接入）。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import lishui


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.interlib import InterlibConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 535, "page": 1, "total_pages": 54, "has_next": True,
                "books": [{"book_id": "181917", "title": "三体X",
                           "author": "宝树著", "publisher": "重庆出版社",
                           "publish_year": "2015", "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake)
    page = lishui.search_books("三体", page=2, limit=5)
    assert page["total_results"] == 535
    # 家族 book_id → 契约 record_id 的映射在 _Client.search 内完成，必须用非空 books 覆盖
    assert page["books"][0]["book_id"] == "181917"
    assert page["books"][0]["title"] == "三体X"
    assert seen["cfg"] == InterlibConfig(
        city="lishui", name_cn="丽水市图书馆",
        base_url="http://60.190.125.252:8086", pro2018=True,
    )
    assert seen["args"] == ("三体", 2, 5)
    base.validate_search_page(page)


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "庆元县图书馆", "location": "庆元二中",
             "call_number": "I247.55/0287", "status": "在馆",
             "available": True, "due_date": ""},
            {"library": "景宁畲族自治县图书馆", "location": "外借",
             "call_number": "I247.5/087.120", "status": "借出",
             "available": False, "due_date": "2026-08-07"},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "三体：新版",
                              "author": "刘慈欣", "publisher": "重庆出版社",
                              "publish_year": "2022", "isbn": "978-7-229-16692-2",
                              "call_number": "I247.55", "summary": ""},
    )
    hs = lishui.get_holdings("2990906", only_available=False)
    assert hs[0]["library"] == "庆元县图书馆"
    assert hs[0]["available"] is True
    # 可借的排前面
    assert [h["available"] for h in hs] == [True, False]
    base.validate_holdings(hs)
    d = lishui.get_book_detail("2990906")
    assert d["title"] == "三体：新版"
    assert d["book_id"] == "2990906"
    base.validate_book_detail(d)


def test_only_available_filters(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "庆元县图书馆", "location": "", "call_number": "",
             "status": "在馆", "available": True, "due_date": ""},
            {"library": "景宁畲族自治县图书馆", "location": "", "call_number": "",
             "status": "借出", "available": False, "due_date": "2026-08-07"},
        ],
    )
    hs = lishui.get_holdings("2990906", only_available=True)
    assert len(hs) == 1 and hs[0]["status"] == "在馆"
    base.validate_holdings(hs)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("丽水市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.interlib.search_books", boom)
    with pytest.raises(RuntimeError, match="丽水市图书馆"):
        lishui.search_books("三体")


# ---------- 契约缝自断言（镜像 tests/test_adapter_contract.py 的注入形态） ----------


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(lishui, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="181917", title="三体X", author="宝树著",
        publisher="重庆出版社", publish_year="2015", availability_summary="有馆藏",
        isbn="978-7-229-10063-6", call_number="I247.5", summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_search_books_contract_shape(monkeypatch):
    result = SimpleNamespace(
        success=True,
        error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="1518564", title="三体．1")],
    )
    _patch_client(monkeypatch, search=result)
    base.validate_search_page(lishui.search_books("三体"))


def test_get_holdings_contract_shape(monkeypatch):
    holdings = [
        SimpleNamespace(library="庆元县图书馆", location="庆元二中",
                        call_number="I247.55/0287", status="在馆",
                        is_available=lambda: True, item_id=""),
        SimpleNamespace(library="景宁畲族自治县图书馆", location="外借",
                        call_number="I247.5/087.120", status="借出",
                        is_available=lambda: False, item_id="item-1"),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-08-07")
    base.validate_holdings(lishui.get_holdings("2990906", only_available=False))
    client.get_return_date.assert_called_once_with("item-1")


def test_get_book_detail_contract_shape(monkeypatch):
    _patch_client(monkeypatch, get_book_detail=_book())
    base.validate_book_detail(lishui.get_book_detail("181917"))
