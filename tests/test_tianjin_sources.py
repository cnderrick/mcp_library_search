"""天津三源容错、复合详情路由与单册接口口径。

spec 口径：search ≥1 源成功即返回存活源结果，三源全失败抛 RuntimeError（含「天津」）；
get_holdings 目标源（首成员）失败报错、附属源失败跳过；get_book_detail 取复合 id 首成员。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters.cn import tianjin
from mcp_library_search.aleph import client as aleph_client

_FIX = Path(__file__).parent / "fixtures" / "tianjin"


def _load(name):
    return (_FIX / name).read_text(encoding="utf-8")


def _stub_zxyh(monkeypatch, result=None, error=None):
    def spy(cfg, keyword, page=1, limit=20):
        if error:
            raise error
        return result if result is not None else {
            "books": [], "total_results": 0, "total_pages": 1, "has_next": False}

    monkeypatch.setattr(tianjin, "il_search", spy)


def test_search_tolerates_single_aleph_failure(monkeypatch):
    _stub_zxyh(monkeypatch)

    def spy(url, config=None, timeout=20):
        if "local_base=TJC01" in url:
            raise RuntimeError("天津图书馆请求失败：HTTP Error 500")
        return _load("find_tjl01.html")

    monkeypatch.setattr(aleph_client, "get", spy)
    r = tianjin._Client().search("三体")
    assert r.success
    assert any(b.record_id.startswith("TJL01:") for b in r.books)
    assert not any(b.record_id.startswith("TJC01:") for b in r.books)
    # 存活源合计仍可知：TJL01 156 + ZXYH stub 0
    assert r.statistics["total_results"] == 156


def test_search_all_sources_fail_raises(monkeypatch):
    _stub_zxyh(monkeypatch, error=RuntimeError("中新友好图书馆请求失败：reset"))

    def spy(url, config=None, timeout=20):
        raise RuntimeError("天津图书馆请求失败：HTTP Error 500")

    monkeypatch.setattr(aleph_client, "get", spy)
    with pytest.raises(RuntimeError, match="天津"):
        tianjin._Client().search("三体")


def test_get_holdings_secondary_failure_skipped(monkeypatch):
    monkeypatch.setattr(aleph_client, "get",
                        lambda url, config=None, timeout=20: _load("item_tjl01.html"))

    def boom(cfg, book_id, only_available=True):
        raise RuntimeError("中新友好图书馆请求失败：reset")

    monkeypatch.setattr(tianjin, "il_holdings", boom)
    hs = tianjin._Client().get_holdings("TJL01:002892667+ZXYH:217795")
    assert len(hs) == 3  # 附属源失败跳过，主源部分原样返回
    # 天津馆藏不带 item_id：模块级 get_holdings 的归还日期补查分支真网不触发
    assert all(h.item_id == "" for h in hs)


def test_get_holdings_primary_failure_raises(monkeypatch):
    def spy(url, config=None, timeout=20):
        raise RuntimeError("天津图书馆请求失败：HTTP Error 500")

    monkeypatch.setattr(aleph_client, "get", spy)
    called = []
    monkeypatch.setattr(tianjin, "il_holdings",
                        lambda *a, **k: called.append(a) or [])
    with pytest.raises(RuntimeError, match="天津图书馆"):
        tianjin._Client().get_holdings("TJL01:002892667+ZXYH:217795")
    assert not called  # 主源已失败，不再打附属源


def test_get_holdings_aleph_error_names_source(monkeypatch):
    def spy(url, config=None, timeout=20):
        raise RuntimeError("天津图书馆请求失败：HTTP Error 500")

    monkeypatch.setattr(aleph_client, "get", spy)
    with pytest.raises(RuntimeError, match="天津市少年儿童图书馆"):
        tianjin._Client().get_holdings("TJC01:000000001")


def test_get_book_detail_first_member_wins(monkeypatch):
    urls = []

    def spy(url, config=None, timeout=20):
        urls.append(url)
        return _load("detail_tjl01_sys.html")

    monkeypatch.setattr(aleph_client, "get", spy)
    d = tianjin._Client().get_book_detail("ZXYH:217795+TJL01:000856840")
    # 复合 id 取优先级最高成员（TJL01），record_id 保留查询原样
    assert len(urls) == 1
    assert "find_code=SYS" in urls[0] and "request=000856840" in urls[0]
    assert d.record_id == "ZXYH:217795+TJL01:000856840"
    assert d.title == "三体" and d.author == "刘慈欣"


def test_get_book_detail_sys_live_shape(monkeypatch):
    # 真网 SYS 单命中直出完整记录页（detail_tjl01_sys.html 为实抓样本）
    monkeypatch.setattr(aleph_client, "get",
                        lambda url, config=None, timeout=20: _load("detail_tjl01_sys.html"))
    d = tianjin._Client().get_book_detail("TJL01:000856840")
    assert d.title == "三体"
    assert d.isbn == "978-7-5366-9293-0"
    assert d.call_number == "I247.55/235"
    assert d.publisher == "重庆出版社"
    # IMPRINT 原值无年份 → publish_year 空串，如实
    assert d.publish_year == ""


def test_get_book_detail_zxyh_routes_family(monkeypatch):
    seen = []

    def spy(cfg, book_id):
        seen.append((cfg, book_id))
        return {"book_id": book_id, "title": "三体", "author": "刘慈欣",
                "publisher": "重庆出版社", "publish_year": "2008",
                "isbn": "978-7-5366-9293-0", "call_number": "I247.55/107",
                "summary": ""}

    monkeypatch.setattr(tianjin, "il_detail", spy)
    d = tianjin._Client().get_book_detail("ZXYH:217795")
    assert seen == [(tianjin._ZXYH, "217795")]
    assert d.title == "三体" and d.call_number == "I247.55/107"


def test_get_book_detail_missing_record_raises(monkeypatch):
    monkeypatch.setattr(aleph_client, "get",
                        lambda url, config=None, timeout=20: "<html><body></body></html>")
    with pytest.raises(RuntimeError, match="未找到"):
        tianjin._Client().get_book_detail("TJL01:999999999")


def test_get_return_date_defined_but_unreachable():
    # 天津无按单册查归还日期的接口（应还日期在单册页/馆藏 JSON 直取），
    # 定义仅为契约形状；真网永不触发
    with pytest.raises(RuntimeError, match="天津"):
        tianjin._Client().get_return_date("item-1")
