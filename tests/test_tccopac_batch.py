"""第二批 tcc-opac 城市测试：济南市图书馆、鄂尔多斯市图书馆。

协议与解析在 `tccopac/` 家族（宁波原独立实现已上收）。fixture 结论见
tests/fixtures/{jinan,eerduosi}/NOTES.md。
"""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search import tccopac
from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import eerduosi, jinan
from mcp_library_search.tccopac import TccOpacConfig

FIXTURES = Path(__file__).parent / "fixtures"

CASES = [
    # label, total, first_id, first_title
    ("jinan", 96, "91073308111000001", "三体：新版"),
    ("eerduosi", 253, "834992670938284143", "三体：三体"),
]


def _load(city, name):
    return json.loads((FIXTURES / city / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("city,total,bid,title", CASES)
def test_parse_search(city, total, bid, title):
    r = tccopac.parser.parse_search(_load(city, "search_santi.json"))
    assert r["total_results"] == total
    assert r["books"][0]["book_id"] == bid
    assert r["books"][0]["title"] == title
    e = tccopac.parser.parse_search(_load(city, "search_empty.json"))
    assert e["total_results"] == 0
    assert e["books"] == []


@pytest.mark.parametrize("city,total,bid,title", CASES)
def test_parse_detail_and_holdings(city, total, bid, title):
    d = tccopac.parser.parse_detail(_load(city, "detail.json"), bid)
    assert d["title"]
    assert d["isbn"]
    hs = tccopac.parser.parse_holdings(_load(city, "holdings.json"))
    for h in hs:
        assert set(h) == {"library", "location", "call_number", "status",
                          "available", "due_date"}


def test_configs():
    assert jinan._CONFIG == TccOpacConfig(
        city="jinan", name_cn="济南市图书馆",
        base_url="https://www.jnlib.net.cn:8087/api/tcc-opac/999",
        referer="https://www.jnlib.net.cn:8087/999")
    assert eerduosi._CONFIG == TccOpacConfig(
        city="eerduosi", name_cn="鄂尔多斯市图书馆",
        base_url="http://1.183.72.92:8089/api/tcc-opac/ordoslib",
        referer="http://1.183.72.92:8089/ordoslib")


@pytest.mark.parametrize("mod", [jinan, eerduosi])
def test_contract_seam(monkeypatch, mod):
    client = Mock()
    client.search.return_value = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 1, "page": 1, "total_pages": 1, "has_next": False},
        books=[SimpleNamespace(record_id="rid-1", title="三体", author="刘慈欣",
                               publisher="重庆出版社", publish_year="2022",
                               availability_summary="")])
    monkeypatch.setattr(mod, "_client", client)
    page = mod.search_books("三体")
    assert page["books"][0]["book_id"] == "rid-1"
    base.validate_search_page(page)
