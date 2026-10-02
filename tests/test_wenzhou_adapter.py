"""温州适配器测试：config 正确、委托 interlib 家族、契约缝生效、输出结构自校验。

温州适配器暂未注册进 _ADAPTERS（注册归协调者统一做），tests/test_adapter_contract.py
的循环盖不到它，所以本文件末尾按契约测试同款方式（Mock 模块级 _client 注入假数据）
自断言三原语输出结构对齐 base.py 的 TypedDict。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters.cn import wenzhou
from mcp_library_search.adapters.base import (
    validate_book_detail,
    validate_holdings,
    validate_search_page,
)


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.interlib import InterlibConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 237, "page": 1, "total_pages": 24, "has_next": True,
                "books": [{"book_id": "2006220724", "title": "三体漫画．起源",
                           "author": "刘慈欣原著", "publisher": "浙江文艺出版社",
                           "publish_year": "2024", "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake)
    page = wenzhou.search_books("三体", page=2, limit=5)
    assert page["total_results"] == 237
    assert page["has_next"] is True
    # 家族 book_id → 契约 record_id 的映射在 _Client.search 内完成（真网冒烟曾抓到此回归）
    assert page["books"][0]["book_id"] == "2006220724"
    assert page["books"][0]["title"] == "三体漫画．起源"
    assert seen["cfg"] == InterlibConfig(
        city="wenzhou", name_cn="温州市图书馆", base_url="https://opac3.wzlib.cn"
    )
    assert seen["args"] == ("三体", 2, 5)


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "温图市府路馆", "location": "二楼少儿文献借阅室NEW",
             "call_number": "J228.2/0287.16/2v4", "status": "在馆",
             "available": True, "due_date": ""},
            {"library": "龙湾馆", "location": "龙湾馆少儿",
             "call_number": "J228.2/a0287.9/v1", "status": "借出",
             "available": False, "due_date": "2026-10-05"},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "三体漫画．起源",
                              "author": "刘慈欣", "publisher": "浙江文艺出版社",
                              "publish_year": "2024", "isbn": "978-7-5339-7402-2",
                              "call_number": "J228.2", "summary": "本书讲述了……"},
    )
    hs = wenzhou.get_holdings("2006220724", only_available=False)
    assert len(hs) == 2
    # 可借的排前面（家族已排序，适配器不破坏顺序）
    assert hs[0]["library"] == "温图市府路馆" and hs[0]["available"] is True
    assert hs[1]["status"] == "借出" and hs[1]["due_date"] == "2026-10-05"
    # only_available 过滤生效
    assert len(wenzhou.get_holdings("2006220724", only_available=True)) == 1
    d = wenzhou.get_book_detail("2006220724")
    assert d["title"] == "三体漫画．起源"
    assert d["book_id"] == "2006220724"


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("温州市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.interlib.search_books", boom)
    with pytest.raises(RuntimeError, match="温州市图书馆"):
        wenzhou.search_books("三体")


# ---------- 契约结构自断言（_ADAPTERS 未注册，契约测试盖不到） ----------


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(wenzhou, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="2006220724", title="三体漫画．起源", author="刘慈欣",
        publisher="浙江文艺出版社", publish_year="2024", availability_summary="",
        isbn="978-7-5339-7402-2", call_number="J228.2", summary="本书讲述了……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_search_output_matches_contract(monkeypatch):
    result = SimpleNamespace(
        success=True,
        error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="2006188837", title="一说《三体》")],
    )
    _patch_client(monkeypatch, search=result)
    validate_search_page(wenzhou.search_books("三体"))


def test_holdings_output_matches_contract(monkeypatch):
    holdings = [
        SimpleNamespace(library="温图市府路馆", location="二楼少儿文献借阅室NEW",
                        call_number="J228.2/0287.16/2v4", status="在馆",
                        is_available=lambda: True, item_id="", due_date=""),
        SimpleNamespace(library="龙湾馆", location="龙湾馆少儿",
                        call_number="J228.2/a0287.9/v1", status="借出",
                        is_available=lambda: False, item_id="item-1", due_date=""),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-10-05")
    items = wenzhou.get_holdings("2006220724", only_available=False)
    validate_holdings(items)
    # 契约形态：已借出且带单册 item_id 时经 get_return_date 补应还日期
    client.get_return_date.assert_called_once_with("item-1")
    assert items[1]["due_date"] == "2026-10-05"


def test_detail_output_matches_contract(monkeypatch):
    _patch_client(monkeypatch, get_book_detail=_book())
    validate_book_detail(wenzhou.get_book_detail("2006220724"))
