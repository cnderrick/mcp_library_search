"""泰州（江苏）适配器测试：config 正确、委托 libstar 家族、契约缝生效、fixture 可解析。

泰州标识用 `taizhou_js`（`taizhou` 已被浙江省台州市占用）。已注册进 _ADAPTERS
（tests/test_adapter_contract.py 覆盖它）；本文件作城市级补充钉子。
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search import libstar
from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import taizhou_js
from mcp_library_search.libstar import LibStarConfig

_FIX = Path(__file__).parent / "fixtures" / "taizhou_js"


def test_config_and_delegation(monkeypatch):
    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        seen["args"] = (keyword, page, limit)
        return {"total_results": 179, "page": 1, "total_pages": 36, "has_next": True,
                "books": [{"book_id": "345767", "title": "三体 : 图像小说",
                           "author": "刘慈欣原著", "publisher": "译林出版社",
                           "publish_year": "2025", "availability_summary": "纸本2，可借2"}]}

    monkeypatch.setattr("mcp_library_search.libstar.search_books", fake)
    page = taizhou_js.search_books("三体", page=1, limit=20)
    assert page["total_results"] == 179
    assert page["books"][0]["book_id"] == "345767"
    assert seen["cfg"] == LibStarConfig(
        city="taizhou_js", name_cn="泰州市图书馆",
        base_url="https://findjstzlib.pub.chaoxing.com", groupcode="100508",
    )
    assert seen["args"] == ("三体", 1, 20)
    base.validate_search_page(page)


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.libstar.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "泰州市图书馆", "location": "社科借阅室",
             "call_number": "J228.2/6319", "status": "在架",
             "available": True, "due_date": ""},
            {"library": "泰州市图书馆", "location": "社科借阅室",
             "call_number": "J228.2/6319", "status": "借出-应还日期:2026-05-01",
             "available": False, "due_date": "2026-05-01"},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.libstar.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "三体:图像小说",
                              "author": "刘慈欣原著 吴青松编绘", "publisher": "译林出版社",
                              "publish_year": "2025", "isbn": "978-7-5753-0280-7",
                              "call_number": "J228.2", "summary": "…"},
    )
    hs = taizhou_js.get_holdings("345767", only_available=False)
    assert hs[0]["library"] == "泰州市图书馆"
    assert [h["available"] for h in hs] == [True, False]
    base.validate_holdings(hs)
    d = taizhou_js.get_book_detail("345767")
    assert d["title"] == "三体:图像小说"
    assert d["book_id"] == "345767"
    base.validate_book_detail(d)


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, keyword, page=1, limit=20):
        raise RuntimeError("泰州市图书馆请求失败：reset")

    monkeypatch.setattr("mcp_library_search.libstar.search_books", boom)
    with pytest.raises(RuntimeError, match="泰州市图书馆"):
        taizhou_js.search_books("三体")


# ---------- 契约缝自断言（镜像 tests/test_adapter_contract.py 的注入形态） ----------


def _patch_client(monkeypatch, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(taizhou_js, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="345767", title="三体:图像小说", author="刘慈欣原著",
        publisher="译林出版社", publish_year="2025", availability_summary="纸本2，可借2",
        isbn="978-7-5753-0280-7", call_number="J228.2/6319", summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_search_books_contract_shape(monkeypatch):
    result = SimpleNamespace(
        success=True,
        error="",
        statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
        books=[_book(), _book(record_id="345768", title="三体Ⅱ")],
    )
    _patch_client(monkeypatch, search=result)
    base.validate_search_page(taizhou_js.search_books("三体"))


def test_get_holdings_contract_shape(monkeypatch):
    holdings = [
        SimpleNamespace(library="泰州市图书馆", location="社科借阅室",
                        call_number="J228.2/6319", status="在架",
                        is_available=lambda: True, item_id=""),
        SimpleNamespace(library="泰州市图书馆", location="", call_number="",
                        status="借出-应还日期:2026-05-01",
                        is_available=lambda: False, item_id="item-1"),
    ]
    client = _patch_client(monkeypatch, get_holdings=holdings,
                           get_return_date="2026-05-01")
    base.validate_holdings(taizhou_js.get_holdings("345767", only_available=False))
    client.get_return_date.assert_called_once_with("item-1")


def test_get_book_detail_contract_shape(monkeypatch):
    _patch_client(monkeypatch, get_book_detail=_book())
    base.validate_book_detail(taizhou_js.get_book_detail("345767"))


# ---------- fixture 解析（LibStar 家族 parser 直打实抓页面） ----------


def test_fixtures_parse():
    search = libstar.parser.parse_search(
        json.loads((_FIX / "search_santi.json").read_text(encoding="utf-8")))
    assert search["total_results"] == 179
    assert search["books"][0]["book_id"] == "345767"
    assert search["books"][0]["title"] == "三体 : 图像小说"
    assert search["books"][0]["author"] == "刘慈欣原著"
    assert search["books"][0]["publisher"] == "译林出版社"
    assert search["books"][0]["publish_year"] == "2025"
    assert search["books"][0]["availability_summary"] == "纸本2，可借2"
    assert search["books"][0]["isbn"] == "978-7-5753-0280-7"
    empty = libstar.parser.parse_search(
        json.loads((_FIX / "search_empty.json").read_text(encoding="utf-8")))
    assert empty["total_results"] == 0 and empty["books"] == []
    detail = libstar.parser.parse_detail(
        json.loads((_FIX / "detail_santi.json").read_text(encoding="utf-8")))
    assert detail["title"] == "三体:图像小说"
    assert detail["author"] == "刘慈欣原著 吴青松编绘"
    assert detail["publisher"] == "译林出版社"
    assert detail["publish_year"] == "2025"
    assert detail["isbn"] == "978-7-5753-0280-7"
    assert detail["call_number"] == "J228.2"
    holdings = libstar.parser.parse_holdings(
        json.loads((_FIX / "holding_santi.json").read_text(encoding="utf-8")))
    assert len(holdings) == 2
    assert holdings[0]["library"] == "泰州市图书馆"
    assert holdings[0]["status"] == "在架" and holdings[0]["available"] is True
    assert holdings[0]["call_number"] == "J228.2/6319"
