"""成都适配器测试：config 正确、经模块级 _client 委托、契约缝与 base.py 结构自断言。

适配器暂不注册进 _ADAPTERS（契约测试盖不到），输出结构用 base.validate_* 自断言。
单测全部 monkeypatch interlib.client.get / interlib.get_holdings 打 fixture，不打真网；
节流 _throttle 统一关断（真网路径由冒烟验证）。
"""
from types import SimpleNamespace

import pytest

from mcp_library_search.adapters import chengdu
from mcp_library_search.adapters.base import (
    validate_book_detail, validate_holdings, validate_search_page,
)
from mcp_library_search.interlib import InterlibConfig
from mcp_library_search.interlib import client as _family_client

SEARCH_P1 = open("tests/fixtures/chengdu/search_p1.html", encoding="utf-8").read()
SEARCH_EMPTY = open("tests/fixtures/chengdu/search_empty.html", encoding="utf-8").read()
DETAIL = open("tests/fixtures/chengdu/detail.html", encoding="utf-8").read()
HOLDING = open("tests/fixtures/chengdu/holding.json", encoding="utf-8").read()

# 在 autouse 关断前捕获真节流函数引用（monkeypatch 只换模块属性，不换本引用）
_REAL_THROTTLE = chengdu._throttle


@pytest.fixture(autouse=True)
def _no_throttle(monkeypatch):
    # 单测不睡真节流（真网路径由冒烟验证）；_Client 经模块全局引用，可整体替换
    monkeypatch.setattr(chengdu, "_throttle", lambda: None)


def test_module_client_shape():
    # 契约测试的硬契约形态：模块级 _client，方法 search/get_holdings/get_book_detail
    assert hasattr(chengdu, "_client")
    for meth in ("search", "get_holdings", "get_book_detail"):
        assert callable(getattr(chengdu._client, meth))


def test_throttle_configured_at_least_two_seconds():
    # 任务口径：节流 ≥2 秒/host（家族 client 无限速，本模块自带）
    assert chengdu._THROTTLE >= 2.0


def test_throttle_sleeps_between_requests(monkeypatch):
    # 桩掉 chengdu 模块内的 time 引用（不动全局 time 模块），验证补足差值语义
    slept = []
    stub = SimpleNamespace(monotonic=lambda: 100.0, sleep=slept.append)
    monkeypatch.setattr(chengdu, "time", stub)
    monkeypatch.setattr(chengdu, "_last_request", 99.5)
    _REAL_THROTTLE()
    assert slept == [pytest.approx(1.5)]  # 距上次 0.5 秒，补足到 2.0


def test_config_and_search_delegation(monkeypatch):
    seen = {}

    def fake_get(cfg, path, params=None):
        seen["cfg"] = cfg
        seen["path"] = path
        seen["params"] = params
        return SEARCH_P1

    monkeypatch.setattr(_family_client, "get", fake_get)
    page = chengdu.search_books("三体", page=2, limit=5)
    assert seen["cfg"] == InterlibConfig(
        city="chengdu", name_cn="成都图书馆", base_url="https://opac.cdclib.cn"
    )
    assert seen["path"] == "/opac/search"
    # 检索参数与家族 _search_once 同款（成都实测该参数集可用）
    assert seen["params"] == {
        "q": "三体", "searchType": "standard", "searchWay0": "marc",
        "logical0": "AND", "rows": 5, "sortWay": "score",
        "sortOrder": "desc", "page": 2,
    }
    validate_search_page(page)
    assert page["total_results"] == 1826
    assert page["total_pages"] == 183
    assert page["has_next"] is True
    assert page["page"] == 2
    # 家族 book_id → 契约 record_id 的映射在 _Client.search 内完成（真网冒烟曾抓到此回归），
    # 必须覆盖「非空 books」的转换
    assert len(page["books"]) == 10
    assert page["books"][0]["book_id"] == "1004752340"
    assert page["books"][0]["title"] == "三体"
    assert page["books"][0]["author"] == "刘慈欣著"
    assert page["books"][0]["publisher"] == "重庆出版社"
    assert page["books"][0]["publish_year"] == "2008"
    assert page["books"][0]["availability_summary"] == ""
    # 契约形态不带 isbn（内部字段不进 BookSummary）
    assert "isbn" not in page["books"][0]


def test_search_empty_page(monkeypatch):
    monkeypatch.setattr(_family_client, "get", lambda cfg, path, params=None: SEARCH_EMPTY)
    page = chengdu.search_books("azbycxq不存在xyz")
    validate_search_page(page)
    assert page["books"] == []
    assert page["total_results"] == 0
    assert page["has_next"] is False


def test_search_retries_isbn_without_hyphens(monkeypatch):
    # 镜像家族 search_raw 语义：首搜为空且关键词含连字符时去连字符重试一次
    calls = []

    def spy(cfg, path, params=None):
        calls.append(params["q"])
        return SEARCH_EMPTY if len(calls) == 1 else SEARCH_P1

    monkeypatch.setattr(_family_client, "get", spy)
    page = chengdu.search_books("978-7-5366-9293-0")
    assert calls == ["978-7-5366-9293-0", "9787536692930"]
    assert page["books"]


def test_holdings_go_through_family(monkeypatch):
    # 馆藏 JSON 与广州基准同构：走家族 get_holdings（client.get 打成都 fixture）
    seen = {}

    def fake_get(cfg, path, params=None):
        seen["path"] = path
        seen["params"] = params
        return HOLDING

    monkeypatch.setattr(_family_client, "get", fake_get)
    hs = chengdu.get_holdings("1002796122", only_available=False)
    assert seen["path"] == "/opac/api/holding/1002796122"
    assert seen["params"] == {"limitLibcodes": "", "isCluster": ""}
    validate_holdings(hs)
    assert len(hs) == 98
    # holdStateMap 原值 2→在馆（可借 84）/3→借出（不可借 14），家族词表判定
    assert sum(1 for h in hs if h["available"]) == 84
    assert {h["status"] for h in hs} == {"在馆", "借出"}
    # 可借在前，组内按馆名排序
    assert hs[0]["available"] is True
    assert hs[0] == {"library": "东坡区图书馆", "location": "中文外借库",
                     "call_number": "I247.55/0287", "status": "在馆",
                     "available": True, "due_date": ""}
    first_un = next(h for h in hs if not h["available"])
    # 借出应还日期来自 loanWorkMap，原值照登（2023-04-10 早于实抓日，逾期形态不判断）
    assert first_un == {"library": "丹棱县图书馆", "location": "中文书库",
                        "call_number": "I247.55/28", "status": "借出",
                        "available": False, "due_date": "2023-04-10"}
    # only_available=True 只留在馆 84 条
    assert len(chengdu.get_holdings("1002796122", only_available=True)) == 84


def test_holdings_sorts_available_first(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "成都图书馆", "location": "外借室", "call_number": "I247.55/02",
             "status": "借出", "available": False, "due_date": "2026-11-08"},
            {"library": "郫都区图书馆", "location": "总书库", "call_number": "I247.55/02",
             "status": "在馆", "available": True, "due_date": ""},
        ],
    )
    hs = chengdu.get_holdings("1002796122", only_available=False)
    validate_holdings(hs)
    assert [h["available"] for h in hs] == [True, False]  # 可借在前
    assert hs[1]["due_date"] == "2026-11-08"


def test_book_detail_parses_default_view(monkeypatch):
    seen = {}

    def fake_get(cfg, path, params=None):
        seen["path"] = path
        seen["params"] = params
        return DETAIL

    monkeypatch.setattr(_family_client, "get", fake_get)
    d = chengdu.get_book_detail("1002796122")
    # 默认视图即完整字段来源（bkTxt 模板）；?return_fmt=json MARC 是可选增强，未采用
    assert seen["path"] == "/opac/book/1002796122"
    assert seen["params"] is None
    validate_book_detail(d)
    assert d["book_id"] == "1002796122"
    assert d["title"] == "三体"
    assert d["author"] == "刘慈欣"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2008"
    assert d["isbn"] == "978-7-5366-9293-0"
    assert d["call_number"] == "I247.55"
    assert d["summary"] == ""


def test_book_detail_not_found(monkeypatch):
    monkeypatch.setattr(_family_client, "get",
                        lambda cfg, path, params=None: "<html><body></body></html>")
    with pytest.raises(RuntimeError, match="未找到"):
        chengdu.get_book_detail("9999999999")


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, path, params=None):
        raise RuntimeError("成都图书馆请求失败：reset")

    monkeypatch.setattr(_family_client, "get", boom)
    with pytest.raises(RuntimeError, match="成都图书馆"):
        chengdu.search_books("三体")
    with pytest.raises(RuntimeError, match="成都图书馆"):
        chengdu.get_book_detail("1002796122")
