"""金华适配器委托测试：模块级 _client 缝、非空 books 转换、输出结构自校验。

金华暂未注册进 _ADAPTERS（注册归协调者统一做），tests/test_adapter_contract.py
的循环盖不到它，所以本文件按契约测试同款方式（Mock 模块级 _client 注入假数据）
自断言三原语输出结构对齐 base.py 的 TypedDict，并钉住 get_return_date 委托分支
（借出且带 item_id 时必须查归还日期——金华真网路径 item_id 恒空，不会触发，
但契约形态不能破坏）。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import jinhua
from mcp_library_search.adapters.base import (
    validate_book_detail,
    validate_holdings,
    validate_search_page,
)


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(jinhua, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="125479764", title="石经考", author="顾炎武撰",
        publisher="商务印书馆[发行者]", publish_year="1936",
        availability_summary="", isbn="书号不详", call_number="Z121.6",
        summary="石经考一卷,据借月仙房汇钞本影印",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_throttle_is_four_seconds_per_host():
    # 天津 ILAS 家族经验的安全线（NOTES.md）
    assert jinhua._THROTTLE == 4.0


def test_search_delegates_and_maps_nonempty_books(monkeypatch):
    result = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 665, "page": 2, "total_pages": 34, "has_next": True},
        books=[_book(), _book(record_id="126657271", title="我的三体漫画．第一辑．2")],
    )
    client = _patch_client(monkeypatch, search=result)
    page = jinhua.search_books("三体", page=2, limit=20)
    client.search.assert_called_once_with(keyword="三体", page=2, limit=20)
    # record_id → 契约 book_id 的映射（真网冒烟曾抓到此类回归）
    assert page["books"][0]["book_id"] == "125479764"
    assert page["books"][1]["book_id"] == "126657271"
    assert page["books"][1]["title"] == "我的三体漫画．第一辑．2"
    assert page["total_results"] == 665
    assert page["page"] == 2 and page["total_pages"] == 34
    assert page["has_next"] is True
    validate_search_page(page)


def test_search_empty_books_still_valid(monkeypatch):
    result = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 0, "page": 1, "total_pages": 1, "has_next": False},
        books=[],
    )
    _patch_client(monkeypatch, search=result)
    page = jinhua.search_books("zzz不存在")
    assert page["books"] == []
    assert page["total_results"] == 0
    validate_search_page(page)


def test_search_failure_raises_with_library_name(monkeypatch):
    _patch_client(monkeypatch, search=SimpleNamespace(
        success=False, error="boom", statistics={}, books=[]))
    with pytest.raises(RuntimeError, match="金华市图书馆"):
        jinhua.search_books("三体")


def test_holdings_delegates_sorts_filters_and_queries_return_date(monkeypatch):
    holdings = [
        SimpleNamespace(library="金华市图书馆", location="市馆外借部",
                        call_number="I247.5/0287", status="借出",
                        is_available=lambda: False, item_id="JHST10882963"),
        SimpleNamespace(library="磐安县图书馆", location="磐安馆少儿",
                        call_number="I247.5/0287", status="入藏",
                        is_available=lambda: True, item_id=""),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-11-05")
    hs = jinhua.get_holdings("126174120", only_available=False)
    client.get_holdings.assert_called_once_with("126174120")
    # 可借排前
    assert hs[0]["available"] is True and hs[0]["library"] == "磐安县图书馆"
    assert hs[1]["available"] is False and hs[1]["status"] == "借出"
    # 契约：借出且带 item_id 必须查归还日期（金华真网 item_id 恒空，分支不触发）
    client.get_return_date.assert_called_once_with("JHST10882963")
    assert hs[1]["due_date"] == "2026-11-05"
    validate_holdings(hs)
    # only_available 过滤（借出册在查询归还日期之前就被滤掉，不再新增委托调用）
    assert len(jinhua.get_holdings("126174120")) == 1
    client.get_return_date.assert_called_once()


def test_detail_delegates(monkeypatch):
    client = _patch_client(monkeypatch, get_book_detail=_book())
    d = jinhua.get_book_detail("125479764")
    client.get_book_detail.assert_called_once_with("125479764")
    assert d["book_id"] == "125479764"
    assert d["title"] == "石经考"
    assert d["isbn"] == "书号不详"
    assert d["call_number"] == "Z121.6"
    assert d["summary"] == "石经考一卷,据借月仙房汇钞本影印"
    validate_book_detail(d)
