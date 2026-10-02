"""徐州适配器测试：config 正确、委托 libstar 家族、契约缝生效。

徐州已注册进 _ADAPTERS（tests/test_adapter_contract.py 覆盖它）；本文件的
输出结构自断言保留，作为城市级的补充钉子（2026-10-03 接入）。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import xuzhou


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.libstar import LibStarConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 407, "page": 1, "total_pages": 41, "has_next": True,
                "books": [{"book_id": "439114", "title": "三体. Ⅲ. 死神永生",
                           "author": "刘慈欣著", "publisher": "重庆出版社",
                           "publish_year": "2010", "availability_summary": "纸本1，可借1"}]}

    monkeypatch.setattr("mcp_library_search.libstar.search_books", fake)
    page = xuzhou.search_books("三体", page=2, limit=5)
    assert page["total_results"] == 407
    # 家族 book_id → 契约 record_id 的映射在 _Client.search 内完成，必须用非空 books 覆盖
    assert page["books"][0]["book_id"] == "439114"
    assert page["books"][0]["title"] == "三体. Ⅲ. 死神永生"
    assert seen["cfg"] == LibStarConfig(
        city="xuzhou", name_cn="徐州市图书馆",
        base_url="https://findxz.libsp.com", groupcode="3203001001",
    )
    assert seen["args"] == ("三体", 2, 5)
    base.validate_search_page(page)


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.libstar.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "徐州图书馆", "location": "三楼借阅室",
             "call_number": "I247.55/4:3", "status": "在架",
             "available": True, "due_date": ""},
            {"library": "徐州鼓楼区", "location": "鼓楼区自采成人",
             "call_number": "I247.57/257", "status": "借出-应还日期:2026-04-08",
             "available": False, "due_date": "2026-04-08"},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.libstar.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "三体.Ⅲ.死神永生",
                              "author": "刘慈欣著", "publisher": "重庆出版社",
                              "publish_year": "2010", "isbn": "978-7-229-03093-3",
                              "call_number": "I247.55", "summary": "…"},
    )
    hs = xuzhou.get_holdings("439114", only_available=False)
    assert hs[0]["library"] == "徐州图书馆"
    assert hs[0]["available"] is True
    # 可借的排前面
    assert [h["available"] for h in hs] == [True, False]
    base.validate_holdings(hs)
    d = xuzhou.get_book_detail("439114")
    assert d["title"] == "三体.Ⅲ.死神永生"
    assert d["book_id"] == "439114"
    base.validate_book_detail(d)


def test_only_available_filters(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.libstar.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "徐州图书馆", "location": "", "call_number": "",
             "status": "在架", "available": True, "due_date": ""},
            {"library": "徐州鼓楼区", "location": "", "call_number": "",
             "status": "借出-应还日期:2026-04-08", "available": False,
             "due_date": "2026-04-08"},
        ],
    )
    hs = xuzhou.get_holdings("439114", only_available=True)
    assert len(hs) == 1 and hs[0]["status"] == "在架"
    base.validate_holdings(hs)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("徐州市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.libstar.search_books", boom)
    with pytest.raises(RuntimeError, match="徐州市图书馆"):
        xuzhou.search_books("三体")


# ---------- 契约缝自断言（镜像 tests/test_adapter_contract.py 的注入形态） ----------


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(xuzhou, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="439114", title="三体.Ⅲ.死神永生", author="刘慈欣著",
        publisher="重庆出版社", publish_year="2010", availability_summary="纸本1，可借1",
        isbn="978-7-229-03093-3", call_number="I247.55/4:3", summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_search_books_contract_shape(monkeypatch):
    result = SimpleNamespace(
        success=True,
        error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="439115", title="三体：黑暗森林")],
    )
    _patch_client(monkeypatch, search=result)
    base.validate_search_page(xuzhou.search_books("三体"))


def test_get_holdings_contract_shape(monkeypatch):
    holdings = [
        SimpleNamespace(library="徐州图书馆", location="三楼借阅室",
                        call_number="I247.55/4:3", status="在架",
                        is_available=lambda: True, item_id=""),
        SimpleNamespace(library="徐州鼓楼区", location="", call_number="",
                        status="借出-应还日期:2026-04-08",
                        is_available=lambda: False, item_id="item-1"),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-04-08")
    base.validate_holdings(xuzhou.get_holdings("439114", only_available=False))
    client.get_return_date.assert_called_once_with("item-1")


def test_get_book_detail_contract_shape(monkeypatch):
    _patch_client(monkeypatch, get_book_detail=_book())
    base.validate_book_detail(xuzhou.get_book_detail("439114"))
