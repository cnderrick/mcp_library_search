"""契约测试：_ADAPTERS 里每个适配器的输出必须符合 base.py 的模型。

新增城市注册进 _ADAPTERS（地区 → 城市两级）后会被这里的循环自动校验；
字段名写歪、类型不对、缺字段，测试直接红。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search import adapters
from mcp_library_search.adapters import base

CASES = [
    (region, city)
    for region, by_city in adapters._ADAPTERS.items()
    for city in sorted(by_city)
]


def _patch_client(monkeypatch, module, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(module, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="rid-1", title="三体", author="刘慈欣", publisher="重庆出版社",
        publish_year="2022", availability_summary="有馆藏",
        isbn="9787536692930", call_number="I247.55/L62", summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


@pytest.mark.parametrize("region, city", CASES)
def test_search_books_contract(monkeypatch, region, city):
    mod = adapters._ADAPTERS[region][city]
    result = SimpleNamespace(
        success=True,
        error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="rid-2", title="三体Ⅱ")],
    )
    _patch_client(monkeypatch, mod, search=result)
    base.validate_search_page(mod.search_books("三体"))


@pytest.mark.parametrize("region, city", CASES)
def test_get_holdings_contract(monkeypatch, region, city):
    mod = adapters._ADAPTERS[region][city]
    holdings = [
        SimpleNamespace(library="A馆", location="2楼", call_number="I247.5", status="可借", is_available=lambda: True, item_id=""),
        SimpleNamespace(library="B馆", location="", call_number="", status="已借出", is_available=lambda: False, item_id="item-1"),
    ]
    client = _patch_client(monkeypatch, mod, get_holdings=holdings, get_return_date="2026-11-05")
    base.validate_holdings(mod.get_holdings("rid-1", only_available=False))
    client.get_return_date.assert_called_once_with("item-1")


@pytest.mark.parametrize("region, city", CASES)
def test_get_book_detail_contract(monkeypatch, region, city):
    mod = adapters._ADAPTERS[region][city]
    _patch_client(monkeypatch, mod, get_book_detail=_book())
    base.validate_book_detail(mod.get_book_detail("rid-1"))
