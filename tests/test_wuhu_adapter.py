"""芜湖市图书馆适配器测试：config、委托 uilas 家族、错误包装、_client 契约缝。

芜湖市图书馆已注册进 adapters/_ADAPTERS（tests/test_adapter_contract.py 覆盖它）；
本文件的输出结构自断言作为城市级补充钉子（2026-10-03 接入）。字段侦察结论见
tests/fixtures/wuhu/NOTES.md。
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search import uilas
from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import wuhu
from mcp_library_search.uilas import UilasConfig

_FIX = Path(__file__).parent / "fixtures" / "wuhu"


def test_config():
    assert wuhu._CONFIG == UilasConfig(
        city="wuhu", name_cn="芜湖市图书馆",
        base_url="https://ilas.whstsg.org.cn:18086/ILASOPAC",
    )


def test_search_end_to_end_via_family_seam(monkeypatch):
    """mock 家族 client.open，验证适配器走完整链路（POST 检索页由家族解析）。"""
    text = (_FIX / "search_p1.html").read_text(encoding="utf-8")
    calls = []

    def spy(config, req, timeout=30):
        calls.append((config, req))
        return text

    monkeypatch.setattr(uilas.client, "open", spy)
    page = wuhu.search_books("三体", limit=20)
    assert page["total_results"] == 143
    assert page["books"][0]["book_id"] == "3163574"
    assert page["books"][0]["title"] == "三体：图像小说"
    base.validate_search_page(page)
    cfg, req = calls[0]
    assert cfg == wuhu._CONFIG
    assert req.full_url.endswith("/NTRdrBookRetr.do")


def test_empty_fixture_parses_to_zero(monkeypatch):
    text = (_FIX / "search_empty.html").read_text(encoding="utf-8")
    monkeypatch.setattr(uilas.client, "open", lambda config, req, timeout=30: text)
    page = wuhu.search_books("zzz")
    assert page["total_results"] == 0
    assert page["books"] == []
    base.validate_search_page(page)


def test_detail_and_holdings_fixtures(monkeypatch):
    detail = (_FIX / "detail.html").read_text(encoding="utf-8")
    monkeypatch.setattr(uilas.client, "open", lambda config, req, timeout=30: detail)
    d = wuhu.get_book_detail("3163574")
    assert d["title"] == "三体：图像小说"
    assert d["isbn"] == "978-7-5753-0280-7"
    base.validate_book_detail(d)
    hs = wuhu.get_holdings("3163574", only_available=False)
    assert [h["status"] for h in hs] == ['入藏', '入藏', '借出']
    base.validate_holdings(hs)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("芜湖市图书馆检索未返回结果页")

    monkeypatch.setattr("mcp_library_search.uilas.search_books", boom)
    with pytest.raises(RuntimeError, match="芜湖市图书馆"):
        wuhu.search_books("三体")


def test_search_failure_raises_with_library_name(monkeypatch):
    client = Mock()
    client.search.return_value = SimpleNamespace(
        success=False, error="boom", statistics={}, books=[])
    monkeypatch.setattr(wuhu, "_client", client)
    with pytest.raises(RuntimeError, match="芜湖市图书馆"):
        wuhu.search_books("三体")


def test_holdings_delegates_sorts_and_queries_return_date(monkeypatch):
    holdings = [
        SimpleNamespace(library="芜湖市图书馆", location="外借", call_number="I247.5",
                        status="借出", is_available=lambda: False, item_id="X1"),
        SimpleNamespace(library="分馆", location="少儿", call_number="I247.5",
                        status="入藏", is_available=lambda: True, item_id=""),
    ]
    client = Mock()
    client.get_holdings.return_value = holdings
    client.get_return_date.return_value = "2026-11-05"
    monkeypatch.setattr(wuhu, "_client", client)
    hs = wuhu.get_holdings("1", only_available=False)
    assert hs[0]["available"] is True and hs[0]["library"] == "分馆"
    assert hs[1]["due_date"] == "2026-11-05"
    client.get_return_date.assert_called_once_with("X1")
    base.validate_holdings(hs)


def test_get_book_detail_contract_shape(monkeypatch):
    client = Mock()
    client.get_book_detail.return_value = SimpleNamespace(
        title="三体：图像小说", author="a", publisher="p", publish_year="2024",
        isbn="978-7-5753-0280-7", call_number="I247.5", summary="",
    )
    monkeypatch.setattr(wuhu, "_client", client)
    d = wuhu.get_book_detail("3163574")
    assert d["book_id"] == "3163574"
    base.validate_book_detail(d)
