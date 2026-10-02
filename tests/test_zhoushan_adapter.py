"""舟山适配器测试：config（含 TLS quirk）、委托 uilas 家族、契约缝生效。

舟山已注册进 _ADAPTERS（tests/test_adapter_contract.py 覆盖它）；本文件的
输出结构自断言保留，作为城市级的补充钉子（2026-10-03 接入）。
"""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search import uilas
from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import zhoushan

_SEARCH = (Path(__file__).parent / "fixtures" / "zhoushan" / "search_p1.html").read_text(encoding="utf-8")


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.uilas import UilasConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 266, "page": 1, "total_pages": 27, "has_next": True,
                "books": [{"book_id": "1533337", "title": "不要回答．vol.02",
                           "author": "三体宇宙编著", "publisher": "中信出版集团股份有限公司",
                           "publish_year": "2026", "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.uilas.search_books", fake)
    page = zhoushan.search_books("三体", page=2, limit=10)
    assert page["total_results"] == 266
    assert page["books"][0]["book_id"] == "1533337"
    assert seen["cfg"] == UilasConfig(
        city="zhoushan", name_cn="舟山市图书馆", base_url="https://opac.zsodl.cn",
        ssl_ciphers="AES256-GCM-SHA384:AES128-GCM-SHA256",
    )
    assert seen["args"] == ("三体", 2, 10)
    base.validate_search_page(page)


def test_search_end_to_end_via_family_seam(monkeypatch):
    """mock 家族 client.open，验证适配器走完整链路且配置带 TLS quirk。"""
    calls = []

    def spy(config, req, timeout=30):
        calls.append((config, req))
        return _SEARCH

    monkeypatch.setattr(uilas.client, "open", spy)
    page = zhoushan.search_books("三体", limit=10)
    assert page["total_results"] == 266
    assert page["books"][0]["book_id"] == "1533337"
    cfg, req = calls[0]
    assert cfg.ssl_ciphers  # TLS quirk 已随配置传入
    assert req.full_url.endswith("/NTRdrBookRetr.do")


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.uilas.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "定海区图书馆", "location": "定海少儿外借",
             "call_number": "J228.2/087", "status": "入藏",
             "available": True, "due_date": ""},
            {"library": "定海区图书馆", "location": "定海少儿外借",
             "call_number": "J228.2/087", "status": "借出",
             "available": False, "due_date": ""},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.uilas.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "不要回答．vol.02",
                              "author": "三体宇宙编著", "publisher": "中信出版集团股份有限公司",
                              "publish_year": "2026", "isbn": "9787521786170",
                              "call_number": "I247.7", "summary": "…"},
    )
    hs = zhoushan.get_holdings("1533337", only_available=False)
    assert hs[0]["library"] == "定海区图书馆"
    assert [h["available"] for h in hs] == [True, False]
    base.validate_holdings(hs)
    d = zhoushan.get_book_detail("1533337")
    assert d["title"] == "不要回答．vol.02"
    assert d["book_id"] == "1533337"
    base.validate_book_detail(d)


def test_only_available_filters(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.uilas.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "定海区图书馆", "location": "", "call_number": "",
             "status": "入藏", "available": True, "due_date": ""},
            {"library": "定海区图书馆", "location": "", "call_number": "",
             "status": "借出", "available": False, "due_date": ""},
        ],
    )
    hs = zhoushan.get_holdings("1533337", only_available=True)
    assert len(hs) == 1 and hs[0]["status"] == "入藏"
    base.validate_holdings(hs)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("舟山市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.uilas.search_books", boom)
    with pytest.raises(RuntimeError, match="舟山市图书馆"):
        zhoushan.search_books("三体")


# ---------- 契约缝自断言（镜像 tests/test_adapter_contract.py 的注入形态） ----------


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(zhoushan, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="1533337", title="不要回答．vol.02", author="三体宇宙编著",
        publisher="中信出版集团股份有限公司", publish_year="2026",
        availability_summary="", isbn="9787521786170", call_number="I247.7",
        summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_search_books_contract_shape(monkeypatch):
    result = SimpleNamespace(
        success=True,
        error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="1536644", title="不要回答．vol.03")],
    )
    _patch_client(monkeypatch, search=result)
    base.validate_search_page(zhoushan.search_books("三体"))


def test_get_holdings_contract_shape(monkeypatch):
    holdings = [
        SimpleNamespace(library="定海区图书馆", location="定海少儿外借",
                        call_number="J228.2/087", status="入藏",
                        is_available=lambda: True, item_id=""),
        SimpleNamespace(library="定海区图书馆", location="定海少儿外借",
                        call_number="J228.2/087", status="借出",
                        is_available=lambda: False, item_id="item-1"),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-11-05")
    base.validate_holdings(zhoushan.get_holdings("1533337", only_available=False))
    client.get_return_date.assert_called_once_with("item-1")


def test_get_book_detail_contract_shape(monkeypatch):
    _patch_client(monkeypatch, get_book_detail=_book())
    base.validate_book_detail(zhoushan.get_book_detail("1533337"))
