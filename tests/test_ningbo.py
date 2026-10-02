"""宁波(tcc-opac 全市联合目录)适配器:令牌流、三原语解析、风控停手。

mock 点为模块级 `_open(req, timeout)`:按顺序返回 fixture JSON 文本(首个
API 调用前必有一次令牌响应),记录 (full_url, body_bytes)。
fixture 结论以 tests/fixtures/ningbo/NOTES.md 为准。
"""
import json
from pathlib import Path

import pytest

from mcp_library_search.adapters.cn import ningbo
from mcp_library_search.adapters.base import validate_book_detail, validate_search_page

_FIXTURES = Path(__file__).parent / "fixtures" / "ningbo"
_TOKEN = json.dumps({"code": 200, "data": {"token": "tk-fake", "expiresIn": "2523"},
                     "desc": "获取accessToken成功！"})
_TOKEN2 = json.dumps({"code": 200, "data": {"token": "tk-fake-2", "expiresIn": "3600"},
                      "desc": "获取accessToken成功！"})
_SEARCH_SANTI = (_FIXTURES / "search_santi.json").read_text(encoding="utf-8")
_SEARCH_HUOZHE = (_FIXTURES / "search_huozhe_hasholding.json").read_text(encoding="utf-8")
_DETAIL = (_FIXTURES / "detail_huozhe.json").read_text(encoding="utf-8")
_HOLDINGS = (_FIXTURES / "holdings_huozhe.json").read_text(encoding="utf-8")
_HUOZHE_ID = "670379643136847935"
_SANTI_HOLD_ID = "670380481158787137"  # hasholding=1 首条:有馆藏书目(36 册)
_SANTI_AGG_ID = "1849291138475802626"  # 聚合条目:详情「数据不存在」、馆藏 0 条


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    """令牌缓存与节流计时是模块级状态,逐测试复位。"""
    monkeypatch.setattr(ningbo, "_token", "")
    monkeypatch.setattr(ningbo, "_token_exp", 0.0)
    monkeypatch.setattr(ningbo, "_last_request", 0.0)


def _mock_open(monkeypatch, pages):
    """按顺序返回 pages;记录 (full_url, data) 列表。"""
    calls = []
    seq = iter(pages)

    def spy(req, timeout=30):
        calls.append((req.full_url, req.data))
        return next(seq)

    monkeypatch.setattr(ningbo, "_open", spy)
    return calls


# ---------- 检索 ----------


def test_search_parses_list_and_stats(monkeypatch):
    calls = _mock_open(monkeypatch, [_TOKEN, _SEARCH_SANTI])
    page = ningbo.search_books("三体")
    # 首次 API 调用前先取访客令牌
    assert calls[0][0].endswith("/system/user/getOpenApiAccessToken")
    assert json.loads(calls[0][1]) == {}
    # 检索走 /search/(尾斜杠),body 是前端逆向出的 searchLists 形态
    url, body = calls[1]
    assert url.endswith("/api/tcc-opac/999/search/")
    payload = json.loads(body)
    assert payload["q"] == "三体"
    assert payload["searchWay"] == "marc"
    assert payload["current"] == 1
    assert payload["size"] == 20
    assert payload["hasholding"] == 1  # 1=只看有馆藏(源站默认);0 是空壳子集,勿用
    # numFound 是字符串 '375' → int;ceil(375/20)=19 页
    assert page["total_results"] == 375
    assert page["page"] == 1
    assert page["total_pages"] == 19
    assert page["has_next"] is True
    assert len(page["books"]) == 10
    b0 = page["books"][0]
    assert b0["book_id"] == _SANTI_HOLD_ID
    assert b0["title"] == "三体"
    assert b0["author"] == "刘慈欣著"
    assert b0["publisher"] == "重庆出版社"
    assert b0["publish_year"] == "2017"  # 有馆藏条目索引已富化(无馆藏子集才常空)
    assert b0["availability_summary"] == ""  # 检索条目无馆藏概况(数据边界)
    validate_search_page(page)
    assert all(isinstance(b["book_id"], str) and b["book_id"] for b in page["books"])


def test_search_page_and_size_params(monkeypatch):
    calls = _mock_open(monkeypatch, [_TOKEN, _SEARCH_HUOZHE])
    page = ningbo.search_books("活着", page=2, limit=10)
    payload = json.loads(calls[1][1])
    assert payload["current"] == 2
    assert payload["size"] == 10
    assert page["page"] == 2
    # hasholding=1 fixture:numFound '3594' → ceil(3594/10)=360 页
    assert page["total_results"] == 3594
    assert page["total_pages"] == 360
    assert page["has_next"] is True
    assert page["books"][0]["book_id"] == _HUOZHE_ID
    assert page["books"][0]["title"] == "活着．"  # 原生句点照登


def test_search_size_clamped(monkeypatch):
    calls = _mock_open(monkeypatch, [_TOKEN, _SEARCH_SANTI, _SEARCH_SANTI])
    ningbo.search_books("三体", limit=100)
    assert json.loads(calls[1][1])["size"] == 50
    ningbo.search_books("三体", limit=0)
    assert json.loads(calls[2][1])["size"] == 1


@pytest.mark.parametrize("code", [43001, -1, -402])
def test_search_captcha_code_stops(monkeypatch, code):
    # code 43001/-1/-402 是前端滑块验证触发码 → 程序化停手,不硬闯
    _mock_open(monkeypatch, [_TOKEN, json.dumps({"code": code, "desc": "系统出现异常，请稍后重试。"})])
    with pytest.raises(RuntimeError, match="滑块验证"):
        ningbo.search_books("三体")


def test_search_non_json_raises(monkeypatch):
    _mock_open(monkeypatch, [_TOKEN, "<html>拦截页</html>"])
    with pytest.raises(RuntimeError, match="不是 JSON"):
        ningbo.search_books("三体")


# ---------- 令牌生命周期 ----------


def test_token_cached_across_calls(monkeypatch):
    calls = _mock_open(monkeypatch, [_TOKEN, _SEARCH_SANTI, _SEARCH_SANTI])
    ningbo.search_books("三体")
    ningbo.search_books("三体")
    token_calls = [c for c in calls if "getOpenApiAccessToken" in c[0]]
    assert len(token_calls) == 1  # expiresIn 2523s 内不重取
    assert len(calls) == 3


def test_token_1003_refetch_and_retry(monkeypatch):
    stale = json.dumps({"code": 1003, "desc": "令牌过期"})
    calls = _mock_open(monkeypatch, [_TOKEN, stale, _TOKEN2, _SEARCH_SANTI])
    page = ningbo.search_books("三体")
    assert page["total_results"] == 375
    token_calls = [c for c in calls if "getOpenApiAccessToken" in c[0]]
    assert len(token_calls) == 2  # 1003 → 重取一次重试
    assert len(calls) == 4


def test_token_failure_raises(monkeypatch):
    bad = json.dumps({"code": 500, "data": None, "desc": "内部错误"})
    _mock_open(monkeypatch, [bad])
    with pytest.raises(RuntimeError, match="访客令牌失败"):
        ningbo.search_books("三体")


# ---------- 详情 ----------


def test_detail_merges_biblios_and_fielditem(monkeypatch):
    calls = _mock_open(monkeypatch, [_TOKEN, _DETAIL])
    d = ningbo.get_book_detail(_HUOZHE_ID)
    url, body = calls[1]
    # getbyid 是 axios params 形态:参数走查询串、空 body
    assert "/service/biblios/getbyid?" in url
    assert f"id={_HUOZHE_ID}" in url
    assert "fields=300a%2C314a%2C327a%2C330a" in url
    assert json.loads(body) == {}
    assert d["book_id"] == _HUOZHE_ID
    assert d["title"] == "活着．"       # biblios 主行,原生句点照登
    assert d["author"] == "余华[著"     # 未闭合方括号照登
    assert d["isbn"] == "9787506365390"
    assert d["publisher"] == ""         # biblios null 且 MARC 210 空 → 空串
    assert d["publish_year"] == "2003"  # 兜底 100$a 定长字段 d2003
    assert d["call_number"] == ""       # classno I247.57 不冒充索书号
    assert d["summary"] == ""           # 四附注字段全空串
    validate_book_detail(d)


def test_detail_missing_raises(monkeypatch):
    gone = json.dumps({"code": -1, "data": None, "desc": "数据不存在"})
    _mock_open(monkeypatch, [_TOKEN, gone])
    with pytest.raises(RuntimeError, match="未找到该书详情"):
        ningbo.get_book_detail(_SANTI_AGG_ID)


def test_book_id_validation(monkeypatch):
    calls = _mock_open(monkeypatch, [])
    with pytest.raises(RuntimeError, match="book_id 格式"):
        ningbo.get_book_detail("abc-123")
    with pytest.raises(RuntimeError, match="book_id 格式"):
        ningbo.get_holdings("NB:1")
    assert calls == []  # 校验在发请求之前


# ---------- 馆藏 ----------


def test_holdings_maps_sorts_and_filters(monkeypatch):
    calls = _mock_open(monkeypatch, [_TOKEN, _HOLDINGS])
    items = ningbo.get_holdings(_HUOZHE_ID, only_available=False)
    url, body = calls[1]
    assert url.endswith("/service/hold/pagelist")
    assert json.loads(body) == {"current": 1, "size": 500, "bibliosId": _HUOZHE_ID}
    assert len(items) == 9
    # 可借排前:7 在馆 + 2 借出
    assert [it["available"] for it in items] == [True] * 7 + [False] * 2
    assert all(it["status"] == "在馆" for it in items[:7])
    assert all(it["status"] == "借出" for it in items[7:])
    # 借出带 due_date:returnTime 完整时间戳取日期段(2020 老数据照登)
    assert items[7]["due_date"] == "2020-01-07"
    assert items[8]["due_date"] == "2020-01-07"
    assert all(it["due_date"] == "" for it in items[:7])
    # 馆/位置/索书号取当前馆口径,原值照登(含下划线前缀)
    by_lib = {it["library"] for it in items}
    assert by_lib == {"慈溪_宗汉图书馆", "奉化区图书馆", "慈溪_桥头图书馆", "慈溪_周巷图书馆"}
    zonghan = next(it for it in items if it["library"] == "慈溪_宗汉图书馆")
    assert zonghan["location"] == "慈溪宗汉外借"
    assert zonghan["call_number"] == "I247.57/679"
    assert zonghan["status"] == "在馆" and zonghan["available"] is True


def test_holdings_only_available(monkeypatch):
    _mock_open(monkeypatch, [_TOKEN, _HOLDINGS])
    items = ningbo.get_holdings(_HUOZHE_ID)
    assert len(items) == 7
    assert all(it["available"] and it["status"] == "在馆" for it in items)


def test_holdings_aggregate_entry_empty(monkeypatch):
    # 聚合条目:pagelist 200+0 条(实测)与 code -1(防御)都归为空列表
    empty = json.dumps({"code": 200, "desc": "操作成功",
                        "data": {"records": [], "total": 0, "size": 500, "current": 1}})
    _mock_open(monkeypatch, [_TOKEN, empty])
    assert ningbo.get_holdings(_SANTI_AGG_ID, only_available=False) == []
    gone = json.dumps({"code": -1, "data": None, "desc": "数据不存在"})
    _mock_open(monkeypatch, [_TOKEN, gone])
    assert ningbo.get_holdings(_SANTI_AGG_ID, only_available=False) == []


# ---------- 模块形态 ----------


def test_module_shape():
    # 独立实现范式:模块级 _client + _open(契约形态硬要求,别破坏)
    assert hasattr(ningbo, "_client")
    for meth in ("search", "get_holdings", "get_book_detail"):
        assert callable(getattr(ningbo._client, meth))
    assert callable(ningbo._open)
