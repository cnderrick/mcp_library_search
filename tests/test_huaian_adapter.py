"""淮安适配器测试：config 正确、委托 libstar 家族、契约缝生效。

淮安已注册进 _ADAPTERS（tests/test_adapter_contract.py 覆盖它）；本文件的
输出结构自断言保留，作为城市级的补充钉子（2026-10-03 接入）。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import huaian


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.libstar import LibStarConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 3110, "page": 1, "total_pages": 311, "has_next": True,
                "books": [{"book_id": "733596", "title": "三体 : 图像小说",
                           "author": "原著刘慈欣", "publisher": "译林出版社",
                           "publish_year": "2025", "availability_summary": "纸本2，可借2"}]}

    monkeypatch.setattr("mcp_library_search.libstar.search_books", fake)
    page = huaian.search_books("三体", page=2, limit=10)
    assert page["total_results"] == 3110
    # 家族 book_id → 契约 record_id 的映射在 _Client.search 内完成，必须用非空 books 覆盖
    assert page["books"][0]["book_id"] == "733596"
    assert page["books"][0]["title"] == "三体 : 图像小说"
    assert seen["cfg"] == LibStarConfig(
        city="huaian", name_cn="淮安市图书馆",
        base_url="https://findhastsg.pub.chaoxing.com", groupcode="100382",
    )
    assert seen["args"] == ("三体", 2, 10)
    base.validate_search_page(page)


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.libstar.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "淮安市图书馆", "location": "三楼借阅室",
             "call_number": "I247.5/7744", "status": "在架",
             "available": True, "due_date": ""},
            {"library": "淮安市清江浦区图书馆", "location": "中外文学馆四楼",
             "call_number": "I247.5/7744", "status": "借出-应还日期:2026-11-07",
             "available": False, "due_date": "2026-11-07"},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.libstar.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "三体:图像小说",
                              "author": "原著刘慈欣 编绘吴青松, 三体宇宙",
                              "publisher": "译林出版社", "publish_year": "2025",
                              "isbn": "978-7-5753-0280-7", "call_number": "I247.5",
                              "summary": "…"},
    )
    hs = huaian.get_holdings("733596", only_available=False)
    assert hs[0]["library"] == "淮安市图书馆"
    assert hs[0]["available"] is True
    assert [h["available"] for h in hs] == [True, False]
    base.validate_holdings(hs)
    d = huaian.get_book_detail("733596")
    assert d["title"] == "三体:图像小说"
    assert d["book_id"] == "733596"
    base.validate_book_detail(d)


def test_only_available_filters(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.libstar.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "淮安市图书馆", "location": "", "call_number": "",
             "status": "在架", "available": True, "due_date": ""},
            {"library": "淮安市清江浦区图书馆", "location": "", "call_number": "",
             "status": "借出-应还日期:2026-11-07", "available": False,
             "due_date": "2026-11-07"},
        ],
    )
    hs = huaian.get_holdings("733596", only_available=True)
    assert len(hs) == 1 and hs[0]["status"] == "在架"
    base.validate_holdings(hs)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("淮安市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.libstar.search_books", boom)
    with pytest.raises(RuntimeError, match="淮安市图书馆"):
        huaian.search_books("三体")


# ---------- 契约缝自断言（镜像 tests/test_adapter_contract.py 的注入形态） ----------


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(huaian, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="733596", title="三体:图像小说", author="原著刘慈欣",
        publisher="译林出版社", publish_year="2025", availability_summary="纸本2，可借2",
        isbn="978-7-5753-0280-7", call_number="I247.5/7744", summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_search_books_contract_shape(monkeypatch):
    result = SimpleNamespace(
        success=True,
        error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="733597", title="三体：黑暗森林")],
    )
    _patch_client(monkeypatch, search=result)
    base.validate_search_page(huaian.search_books("三体"))


def test_get_holdings_contract_shape(monkeypatch):
    holdings = [
        SimpleNamespace(library="淮安市图书馆", location="三楼借阅室",
                        call_number="I247.5/7744", status="在架",
                        is_available=lambda: True, item_id=""),
        SimpleNamespace(library="淮安市清江浦区图书馆", location="", call_number="",
                        status="借出-应还日期:2026-11-07",
                        is_available=lambda: False, item_id="item-1"),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-11-07")
    base.validate_holdings(huaian.get_holdings("733596", only_available=False))
    client.get_return_date.assert_called_once_with("item-1")


def test_get_book_detail_contract_shape(monkeypatch):
    _patch_client(monkeypatch, get_book_detail=_book())
    base.validate_book_detail(huaian.get_book_detail("733596"))
