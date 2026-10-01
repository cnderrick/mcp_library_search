"""Interlib 家族三原语接线测试（monkeypatch client.get，打 fixture）。

馆藏走 /opac/api/holding/{bookrecno} JSON 接口（见 NOTES.md），
与详情页是两条独立请求。
"""
import json

import pytest

from mcp_library_search.interlib import (
    InterlibConfig, search_books, get_holdings, get_book_detail,
)
from mcp_library_search.interlib import client as _client

_CFG = InterlibConfig(city="guangzhou", name_cn="广州图书馆", base_url="https://opac.gzlib.org.cn")
_SEARCH = open("tests/fixtures/guangzhou/search_p1.html", encoding="utf-8").read()
_DETAIL = open("tests/fixtures/guangzhou/detail.html", encoding="utf-8").read()
_HOLDING = open("tests/fixtures/guangzhou/holding.json", encoding="utf-8").read()

_BOOK_ID = "3004742677"  # fixture 对应的书目 ID
_EMPTY = open("tests/fixtures/guangzhou/search_empty.html", encoding="utf-8").read()


def test_search_books_maps_to_contract(monkeypatch):
    monkeypatch.setattr(_client, "get", lambda cfg, path, params=None: _SEARCH)
    page = search_books(_CFG, "活着", page=1, limit=10)
    assert set(page) == {"total_results", "page", "total_pages", "has_next", "books"}
    assert page["page"] == 1
    assert page["total_results"] == 2763
    assert page["books"][0]["book_id"].isdigit()


def test_search_books_wraps_errors(monkeypatch):
    def boom(cfg, path, params=None):
        raise RuntimeError("广州图书馆请求失败：reset")

    monkeypatch.setattr(_client, "get", boom)
    with pytest.raises(RuntimeError, match="广州图书馆"):
        search_books(_CFG, "活着")


def test_search_retries_isbn_without_hyphens(monkeypatch):
    # 带连字符的 ISBN 在 marc 检索下命中不了，须去连字符重试（真网实测）
    calls = []

    def spy(cfg, path, params=None):
        calls.append(params["q"])
        return _EMPTY if len(calls) == 1 else _SEARCH

    monkeypatch.setattr(_client, "get", spy)
    page = search_books(_CFG, "978-7-5086-8719-3")
    assert calls == ["978-7-5086-8719-3", "9787508687193"]
    assert page["books"]


def test_get_holdings_sorts_available_first(monkeypatch):
    monkeypatch.setattr(_client, "get", lambda cfg, path, params=None: _HOLDING)
    hs = get_holdings(_CFG, _BOOK_ID, only_available=False)
    assert hs
    flags = [h["available"] for h in hs]
    assert flags == sorted(flags, reverse=True)  # True 在前


def test_get_holdings_classifies_synthetic_states(monkeypatch):
    payload = {
        "holdingList": [
            {"state": 2, "barcode": "b1", "callno": "c1", "curlib": "GT",
             "curlocal": "CKWX01", "loan": None},
            {"state": 3, "barcode": "b2", "callno": "c2", "curlib": "GT",
             "curlocal": "CKWX01", "loan": None},
            {"state": 13, "barcode": "b3", "callno": "c3", "curlib": "GT",
             "curlocal": "CKWX01", "loan": None},
        ],
        "holdStateMap": {"2": {"stateName": "在馆"}, "3": {"stateName": "借出"},
                         "13": {"stateName": "闭架"}},
        "libcodeMap": {"GT": "广州图书馆"},
        "localMap": {"CKWX01": "参考文献馆•港台书区"},
        "loanWorkMap": {},
    }
    monkeypatch.setattr(_client, "get",
                        lambda cfg, path, params=None: json.dumps(payload))
    hs = get_holdings(_CFG, _BOOK_ID, only_available=False)
    assert [h["available"] for h in hs] == [True, False, False]


def test_get_holdings_only_requests_holding_api(monkeypatch):
    calls = []

    def spy(cfg, path, params=None):
        calls.append(path)
        return _HOLDING

    monkeypatch.setattr(_client, "get", spy)
    hs = get_holdings(_CFG, _BOOK_ID, only_available=True)
    assert all(h["available"] for h in hs)
    # 馆藏只有一个 JSON 接口请求，不依赖详情页
    assert calls == [f"/opac/api/holding/{_BOOK_ID}"]


def test_get_book_detail_contract(monkeypatch):
    monkeypatch.setattr(_client, "get", lambda cfg, path, params=None: _DETAIL)
    d = get_book_detail(_CFG, _BOOK_ID)
    assert set(d) == {"book_id", "title", "author", "publisher", "publish_year",
                      "isbn", "call_number", "summary"}
    assert d["book_id"] == _BOOK_ID
    assert d["title"] == "无论如何都要活著"


def test_get_book_detail_not_found(monkeypatch):
    monkeypatch.setattr(_client, "get",
                        lambda cfg, path, params=None: "<html><body></body></html>")
    with pytest.raises(RuntimeError, match="未找到"):
        get_book_detail(_CFG, "9999999999")
