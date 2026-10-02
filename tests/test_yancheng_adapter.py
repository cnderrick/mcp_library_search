"""盐城适配器测试：config 正确、委托 libstar 家族、契约缝生效。

盐城已注册进 _ADAPTERS（tests/test_adapter_contract.py 覆盖它）；本文件的
输出结构自断言保留，作为城市级的补充钉子（2026-10-03 接入）。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import yancheng


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.libstar import LibStarConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 857, "page": 1, "total_pages": 86, "has_next": True,
                "books": [{"book_id": "671583", "title": "三体 : 图像小说",
                           "author": "原著刘慈欣,吴青松", "publisher": "译林出版社",
                           "publish_year": "2025", "availability_summary": "纸本3，可借3"}]}

    monkeypatch.setattr("mcp_library_search.libstar.search_books", fake)
    page = yancheng.search_books("三体", page=2, limit=10)
    assert page["total_results"] == 857
    # 家族 book_id → 契约 record_id 的映射在 _Client.search 内完成，必须用非空 books 覆盖
    assert page["books"][0]["book_id"] == "671583"
    assert page["books"][0]["title"] == "三体 : 图像小说"
    assert seen["cfg"] == LibStarConfig(
        city="yancheng", name_cn="盐城市图书馆",
        base_url="https://findyctsg.libsp.com", groupcode="100026",
    )
    assert seen["args"] == ("三体", 2, 10)
    base.validate_search_page(page)


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.libstar.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "盐城市图书馆", "location": "社科室",
             "call_number": "J228.2/4768", "status": "在架",
             "available": True, "due_date": ""},
            {"library": "盐城市图书馆", "location": "社科室",
             "call_number": "J228.2/4768", "status": "借出-应还日期:2026-01-10",
             "available": False, "due_date": "2026-01-10"},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.libstar.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "三体:图像小说",
                              "author": "原著刘慈欣 编绘吴青松, 三体宇宙",
                              "publisher": "译林出版社", "publish_year": "2025",
                              "isbn": "978-7-5753-0280-7", "call_number": "J228.2",
                              "summary": "…"},
    )
    hs = yancheng.get_holdings("671583", only_available=False)
    assert hs[0]["library"] == "盐城市图书馆"
    assert hs[0]["available"] is True
    assert [h["available"] for h in hs] == [True, False]
    base.validate_holdings(hs)
    d = yancheng.get_book_detail("671583")
    assert d["title"] == "三体:图像小说"
    assert d["book_id"] == "671583"
    base.validate_book_detail(d)


def test_only_available_filters(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.libstar.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "盐城市图书馆", "location": "", "call_number": "",
             "status": "在架", "available": True, "due_date": ""},
            {"library": "盐城市图书馆", "location": "", "call_number": "",
             "status": "借出-应还日期:2026-01-10", "available": False,
             "due_date": "2026-01-10"},
        ],
    )
    hs = yancheng.get_holdings("671583", only_available=True)
    assert len(hs) == 1 and hs[0]["status"] == "在架"
    base.validate_holdings(hs)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("盐城市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.libstar.search_books", boom)
    with pytest.raises(RuntimeError, match="盐城市图书馆"):
        yancheng.search_books("三体")


# ---------- 契约缝自断言（镜像 tests/test_adapter_contract.py 的注入形态） ----------


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(yancheng, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="671583", title="三体:图像小说", author="原著刘慈欣",
        publisher="译林出版社", publish_year="2025", availability_summary="纸本3，可借3",
        isbn="978-7-5753-0280-7", call_number="J228.2/4768", summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_search_books_contract_shape(monkeypatch):
    result = SimpleNamespace(
        success=True,
        error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="671584", title="三体：黑暗森林")],
    )
    _patch_client(monkeypatch, search=result)
    base.validate_search_page(yancheng.search_books("三体"))


def test_get_holdings_contract_shape(monkeypatch):
    holdings = [
        SimpleNamespace(library="盐城市图书馆", location="社科室",
                        call_number="J228.2/4768", status="在架",
                        is_available=lambda: True, item_id=""),
        SimpleNamespace(library="盐城市图书馆", location="社科室", call_number="",
                        status="借出-应还日期:2026-01-10",
                        is_available=lambda: False, item_id="item-1"),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-01-10")
    base.validate_holdings(yancheng.get_holdings("671583", only_available=False))
    client.get_return_date.assert_called_once_with("item-1")


def test_get_book_detail_contract_shape(monkeypatch):
    _patch_client(monkeypatch, get_book_detail=_book())
    base.validate_book_detail(yancheng.get_book_detail("671583"))
