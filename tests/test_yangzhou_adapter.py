"""扬州适配器：三原语、URL 形态、securitycam 配置与「壳页响铃」端到端。

解析层（家族）由 test_uopac_parse.py 用两站 fixture 同跑钉住，这里只测城市级
包装行为。全部离线：家族 HTTP 入口 `client.get` 或更底层的 urlopen 被 mock。
fixture 结论见 tests/fixtures/yangzhou/NOTES.md。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters.cn import yangzhou
from mcp_library_search.adapters.base import (
    validate_book_detail, validate_holdings, validate_search_page)
from mcp_library_search.uopac import UopacConfig
from mcp_library_search.uopac import client as uopac_client

_FIX = Path(__file__).parent / "fixtures" / "yangzhou"


def _f(name):
    return (_FIX / name).read_text(encoding="utf-8")


def _mock_get(monkeypatch, pages=None, router=None):
    """mock 家族 HTTP 入口：按顺序返回 pages，或按 URL 走 router。"""
    calls = []
    seq = iter(pages or [])

    def spy(url, cfg):
        calls.append(url)
        if router is not None:
            return router(url)
        return next(seq)

    monkeypatch.setattr(uopac_client, "get", spy)
    return calls


def _holding_router(url):
    if "detail.action" in url:
        return _f("uopac_detail_multi.html")
    if "lib=YZLIB" in url:
        return _f("uopac_holding_yzlib.html")
    if "lib=YZHJQG" in url:
        return _f("uopac_holding_hjq.html")
    return ""


# ---------- 配置与形态 ----------

def test_config_carries_static_securitycam_cookie():
    assert isinstance(yangzhou._YZ, UopacConfig)
    assert yangzhou._YZ.base_url == "http://ytlmopac.cn:8080"
    # 静态挑战解出的固定 cookie，值本身在 NOTES.md 有推导记录
    assert yangzhou._YZ.securitycam == "6322e5171be855cb6e0f4e8b640895e6"


def test_module_shape():
    # 契约形态硬要求：模块级 _client
    for meth in ("search", "get_holdings", "get_book_detail"):
        assert callable(getattr(yangzhou._client, meth))


# ---------- 检索 ----------

def test_search_parses_and_maps_contract(monkeypatch):
    calls = _mock_get(monkeypatch, [_f("uopac_result_santi.html")])
    page = yangzhou.search_books("三体")
    # URL 形态：站点根 + /uopac/s/search_result.action + meta=20（任意）
    assert calls[0].startswith("http://ytlmopac.cn:8080/uopac/s/search_result.action?")
    assert "meta=20" in calls[0]
    assert "q=%E4%B8%89%E4%BD%93" in calls[0]
    assert "page=1" in calls[0]
    assert page["total_results"] == 73
    assert page["total_pages"] == 4
    assert page["has_next"] is True
    assert len(page["books"]) == 20
    b0 = page["books"][0]
    assert b0["book_id"] == "780232"          # 单源：裸 uopac 数字 id
    assert b0["title"] == "三体漫画 起源 地球大危机"
    assert b0["availability_summary"] == "所在馆：扬州市图书馆"
    validate_search_page(page)
    assert set(b0) == {"book_id", "title", "author", "publisher",
                       "publish_year", "availability_summary"}


def test_isbn_keyword_routes_to_wildcard_meta14(monkeypatch):
    calls = _mock_get(monkeypatch, [_f("uopac_result_isbn_wild.html")])
    page = yangzhou.search_books("978-7-5339-7402-2")
    assert "meta=14" in calls[0]
    assert "q=9%2A7%2A8%2A7%2A5%2A3%2A3%2A9%2A7%2A4%2A0%2A2%2A2" in calls[0]
    assert page["total_results"] == 1
    assert page["books"][0]["book_id"] == "780232"


def test_last_page_has_no_next(monkeypatch):
    _mock_get(monkeypatch, [_f("uopac_result_santi_p2.html")])
    page = yangzhou.search_books("三体", page=2)
    assert page["page"] == 2
    assert page["total_pages"] == 4
    assert page["has_next"] is True


def test_empty_result(monkeypatch):
    _mock_get(monkeypatch, [_f("uopac_result_empty.html")])
    page = yangzhou.search_books("zzzzqqqxyz")
    assert page["total_results"] == 0
    assert page["books"] == []
    assert page["total_pages"] == 0
    assert page["has_next"] is False


def test_non_result_page_raises(monkeypatch):
    # 响应不是结果页（如被拦截）→ 抛含馆名的 RuntimeError，不静默当空结果
    _mock_get(monkeypatch, ["<html><body>别的什么</body></html>"])
    with pytest.raises(RuntimeError, match="扬州市图书馆联盟"):
        yangzhou.search_books("三体")


# ---------- 详情 ----------

def test_get_book_detail_fields(monkeypatch):
    calls = _mock_get(monkeypatch, [_f("uopac_detail_single.html")])
    d = yangzhou.get_book_detail("780232")
    assert calls[0] == "http://ytlmopac.cn:8080/uopac/s/detail.action?id=780232"
    assert d["book_id"] == "780232"
    assert d["title"] == "三体漫画:起源.地球大危机"
    assert d["publisher"] == "浙江文艺出版社"
    assert d["isbn"] == "978-7-5339-7402-2"
    assert d["call_number"] == ""          # 详情页无索书号字段，不冒充
    validate_book_detail(d)


def test_bad_book_id_raises_without_request(monkeypatch):
    calls = _mock_get(monkeypatch, [])
    for bad in ("abc", "", "12a"):
        with pytest.raises(RuntimeError, match="book_id"):
            yangzhou.get_book_detail(bad)
    assert calls == []                     # 非法 id 不发请求


# ---------- 馆藏 ----------

def test_get_holdings_aggregates_member_tabs(monkeypatch):
    calls = _mock_get(monkeypatch, router=_holding_router)
    hs = yangzhou.get_holdings("1054519", only_available=False)
    # 1 次详情 + 2 次 ajax（每个持有馆一次）
    assert sum(1 for u in calls if "detail.action" in u) == 1
    assert sum(1 for u in calls if "ajax_holding.action" in u) == 2
    assert len(hs) == 5                    # 市馆 4 册 + 邗江区馆 1 册
    assert {h["library"] for h in hs} == {"扬州市图书馆", "扬州市邗江区图书馆"}
    assert sum(1 for h in hs if h["available"]) == 4
    # 可借排前
    assert hs[0]["available"] is True
    assert hs[-1]["available"] is False
    assert hs[-1]["status"] == "借出"       # 原值照登
    assert hs[-1]["due_date"] == ""        # 扬州站不给应还日期
    validate_holdings(hs)


def test_get_holdings_only_available_default(monkeypatch):
    _mock_get(monkeypatch, router=_holding_router)
    hs = yangzhou.get_holdings("1054519")
    assert len(hs) == 4
    assert all(h["available"] and h["status"] == "可借" for h in hs)


def test_member_tab_failure_tolerated(monkeypatch):
    # 某成员馆代理失败 → 该馆 0 条，不拖垮整体
    def router(url):
        if "detail.action" in url:
            return _f("uopac_detail_multi.html")
        if "lib=YZLIB" in url:
            raise RuntimeError("扬州市图书馆请求失败：HTTP Error 503")
        return _f("uopac_holding_hjq.html")

    _mock_get(monkeypatch, router=router)
    hs = yangzhou.get_holdings("1054519", only_available=False)
    assert len(hs) == 1
    assert hs[0]["library"] == "扬州市邗江区图书馆"


# ---------- securitycam 壳页：端到端响铃 ----------

def test_challenge_shell_raises_end_to_end(monkeypatch):
    """cookie 常量被轮换时：真 HTTP 层认出壳页 → 抛含馆名的错误，不静默空结果。"""
    shell = _f("uopac_challenge.html")

    class _Resp:
        def read(self):
            return shell.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    uopac_client._last_request.clear()
    monkeypatch.setattr(uopac_client.urllib.request, "urlopen",
                        lambda req, timeout=None: _Resp())
    with pytest.raises(RuntimeError) as ei:
        yangzhou.search_books("三体")
    msg = str(ei.value)
    assert "扬州市图书馆联盟" in msg and "securitycam" in msg
