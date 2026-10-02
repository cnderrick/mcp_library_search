"""合肥适配器契约形态测试：模块级 _client 注入、输出结构对齐 base.py 自断言。

合肥暂未注册进 _ADAPTERS，tests/test_adapter_contract.py 盖不到，本文件自断言，
断言形态对齐契约测试（含 record_id → book_id 的非空 books 转换——architecture.md
记录过该映射的真网故障，委托测试必须覆盖）。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import hefei


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(hefei, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="AH:1901181704+HF:1001460005", title="三体", author="刘慈欣",
        publisher="重庆出版社", publish_year="2008", availability_summary="",
        isbn="978-7-5366-9293-0", call_number="I247.55", summary="",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_search_books_contract_and_record_id_mapping(monkeypatch):
    # 非空 books：内部 record_id → 契约 book_id 的映射必须覆盖
    result = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 351, "page": 1, "total_pages": 21,
                    "has_next": True},
        books=[_book(), _book(record_id="HF:1001096470", title="三体：新版")],
    )
    _patch_client(monkeypatch, search=result)
    page = hefei.search_books("三体")
    base.validate_search_page(page)
    assert page["books"][0]["book_id"] == "AH:1901181704+HF:1001460005"
    assert page["books"][1]["book_id"] == "HF:1001096470"
    assert page["books"][1]["title"] == "三体：新版"
    assert page["total_results"] == 351
    assert page["total_pages"] == 21
    assert page["has_next"] is True


def test_search_books_total_none_passes_contract(monkeypatch):
    # 任一存活源无总数 → total_results=None（契约允许 Optional[int]）
    result = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": None, "page": 2, "total_pages": 21,
                    "has_next": True},
        books=[_book()],
    )
    _patch_client(monkeypatch, search=result)
    page = hefei.search_books("三体", page=2)
    base.validate_search_page(page)
    assert page["total_results"] is None
    assert page["page"] == 2


def test_search_books_failure_raises(monkeypatch):
    _patch_client(monkeypatch, search=SimpleNamespace(
        success=False, error="两源检索均失败", statistics={}, books=[]))
    with pytest.raises(RuntimeError, match="合肥"):
        hefei.search_books("三体")


def test_get_holdings_contract(monkeypatch):
    holdings = [
        SimpleNamespace(library="合肥少儿图书馆", location="过渡馆图书外借处",
                        call_number="I427.55/40:1/2016", status="借出",
                        is_available=lambda: False, item_id="item-1",
                        due_date="2026-10-05"),
        SimpleNamespace(library="安徽省馆", location="文学室(西楼四楼)",
                        call_number="I247.55/0405/2024", status="在馆",
                        is_available=lambda: True, item_id="", due_date=""),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-11-05")
    hs = hefei.get_holdings("AH:1+HF:2", only_available=False)
    base.validate_holdings(hs)
    # 可借在前
    assert [h["available"] for h in hs] == [True, False]
    # 已借出且带单册 item_id → 走 get_return_date 补应还日期（契约行为）
    client.get_return_date.assert_called_once_with("item-1")
    assert hs[1]["due_date"] == "2026-11-05"
    assert hs[0]["library"] == "安徽省馆"


def test_get_holdings_only_available_filters(monkeypatch):
    holdings = [
        SimpleNamespace(library="安徽省馆", location="", call_number="",
                        status="在馆", is_available=lambda: True, item_id="",
                        due_date=""),
        SimpleNamespace(library="合肥少儿图书馆", location="", call_number="",
                        status="借出", is_available=lambda: False, item_id="",
                        due_date="2026-10-05"),
    ]
    _patch_client(monkeypatch, get_holdings=holdings)
    hs = hefei.get_holdings("AH:1", only_available=True)
    base.validate_holdings(hs)
    assert len(hs) == 1
    assert hs[0]["status"] == "在馆"


def test_get_book_detail_contract(monkeypatch):
    _patch_client(monkeypatch, get_book_detail=_book())
    d = hefei.get_book_detail("AH:1901181704+HF:1001460005")
    base.validate_book_detail(d)
    # book_id 保留查询原样（复合 id 不拆）
    assert d["book_id"] == "AH:1901181704+HF:1001460005"
    assert d["title"] == "三体"
    assert d["isbn"] == "978-7-5366-9293-0"


def test_get_return_date_not_supported():
    # Interlib 应还日期在馆藏 JSON 内解析，无单册接口；形状对齐契约、调用即报错
    with pytest.raises(RuntimeError, match="无单册归还日期接口"):
        hefei._Client().get_return_date("item-1")
