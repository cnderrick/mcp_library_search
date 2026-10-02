"""第二批 UILAS 城市测试：新版 UILAS REST（兰州、江门）＋老版 UILAS HTML（河南）。

fixture 结论见 tests/fixtures/{lanzhou,jiangmen,henan_prov}/NOTES.md。
"""
import json
from pathlib import Path

from mcp_library_search.uilas import parser as uhp
from mcp_library_search.uilas_rest import parser as up

FIXTURES = Path(__file__).parent / "fixtures"

# 新版 UILAS REST：(city, total, first_id, first_title, isbn)
REST_CASES = [
    ("lanzhou", 521, "483939", "三体 ：死神永生", "978-7-229-03093-3"),
    ("jiangmen", 367, "9560678", "三体", "978-7-5366-9293-0"),
]


def _load(city, name):
    return json.loads((FIXTURES / city / name).read_text(encoding="utf-8"))


def test_rest_search_and_detail():
    for city, total, bid, title, isbn in REST_CASES:
        r = up.parse_search(_load(city, "search_santi.json"))
        assert r["total_results"] == total, city
        assert r["books"][0]["book_id"] == bid, city
        assert r["books"][0]["title"] == title, city
        assert r["books"][0]["isbn"] == isbn, city
        e = up.parse_search(_load(city, "search_empty.json"))
        assert e["total_results"] == 0
        assert e["books"] == []
        d = up.parse_detail(_load(city, "detail_santi.json"))
        assert d["book"]["title"], city
        assert d["book"]["isbn"] == isbn, city
        for h in d["holdings"]:
            assert set(h) == {"library", "location", "call_number", "status",
                              "available", "due_date"}


def test_henan_prov_uilas_html():
    r = uhp.parse_search((FIXTURES / "henan_prov" / "search_p1.html").read_text(encoding="utf-8"))
    assert r["total_results"] == 57
    assert r["books"][0]["book_id"] == "900077191"
    assert r["books"][0]["title"] == "我的三体漫画．第一辑．1"
    e = uhp.parse_search((FIXTURES / "henan_prov" / "search_empty.html").read_text(encoding="utf-8"))
    assert e["total_results"] == 0
    assert e["books"] == []
    detail = (FIXTURES / "henan_prov" / "detail.html").read_text(encoding="utf-8")
    d = uhp.parse_detail(detail)
    assert d["isbn"] == "978-7-5728-2657-3"
    hs = uhp.parse_holdings(detail)
    assert len(hs) == 3
    assert all(h["status"] in uhp.AVAILABLE_STATUS for h in hs)


def test_adapter_configs():
    from mcp_library_search.adapters.cn import henan_prov, jiangmen, lanzhou
    from mcp_library_search.uilas import UilasConfig
    from mcp_library_search.uilas_rest import UilasRestConfig
    assert lanzhou._CONFIG == UilasRestConfig(
        city="lanzhou", name_cn="兰州市图书馆",
        base_url="http://36.137.50.135:8082", referer="http://36.137.50.135:8082/")
    assert jiangmen._CONFIG == UilasRestConfig(
        city="jiangmen", name_cn="江门市图书馆",
        base_url="http://125.93.12.202:9188", referer="http://125.93.12.202:9188/")
    assert henan_prov._CONFIG == UilasConfig(
        city="henan_prov", name_cn="河南省图书馆",
        base_url="http://218.28.6.78:8081/ILASOPAC")
