"""青岛适配器测试：Solr 检索通道 + 家族详情/馆藏解析。

检索走 `/opac/api/search`（站点内嵌 Solr 后端，`wt=json`，不经滑动验证码）；
详情 `/opac/book/{id}` 与馆藏 `/opac/api/holding/{id}` 与广州基准同构，复用家族
client 与 parser。fixture 结论以 tests/fixtures/qingdao/NOTES.md 为准。

mock 点为家族 HTTP 入口 `interlib.client.get`；节流单测统一关断（真网路径由冒烟验证）。
"""
import json
from types import SimpleNamespace

import pytest

from mcp_library_search.adapters import qingdao
from mcp_library_search.adapters.base import (
    validate_book_detail, validate_holdings, validate_search_page,
)
from mcp_library_search.interlib import InterlibConfig
from mcp_library_search.interlib import client as _family_client

_FIXTURES = "tests/fixtures/qingdao/"
SEARCH_ONE = open(_FIXTURES + "search_solr.json", encoding="utf-8").read()
SEARCH_SANTI = open(_FIXTURES + "search_solr_santi.json", encoding="utf-8").read()
SEARCH_EMPTY = open(_FIXTURES + "search_solr_empty.json", encoding="utf-8").read()
DETAIL = open(_FIXTURES + "detail.html", encoding="utf-8").read()
HOLDING = open(_FIXTURES + "holding.json", encoding="utf-8").read()

# 越界页样本：numFound=143 但 docs 为空（服务端不报错，实抓验证）
_SANTI = json.loads(SEARCH_SANTI)
SEARCH_OUT_OF_RANGE = json.dumps(
    {**_SANTI, "response": {**_SANTI["response"], "docs": []}}, ensure_ascii=False)

# 在 autouse 关断前捕获真节流函数引用（monkeypatch 只换模块属性，不换本引用）
_REAL_THROTTLE = qingdao._throttle


@pytest.fixture(autouse=True)
def _no_throttle(monkeypatch):
    monkeypatch.setattr(qingdao, "_throttle", lambda: None)


def _patch_get(monkeypatch, pages):
    """按顺序返回 pages；记录 (path, params) 列表。"""
    calls = []
    seq = iter(pages)

    def spy(cfg, path, params=None):
        calls.append((path, params))
        return next(seq)

    monkeypatch.setattr(_family_client, "get", spy)
    return calls


def test_module_client_shape():
    assert hasattr(qingdao, "_client")
    for meth in ("search", "get_holdings", "get_book_detail"):
        assert callable(getattr(qingdao._client, meth))


def test_throttle_configured_at_least_two_seconds():
    # 站点检索入口有滑动验证码门禁，家族 client 无限速，本模块自带保守节流
    assert qingdao._THROTTLE >= 2.0


def test_throttle_sleeps_between_requests(monkeypatch):
    slept = []
    stub = SimpleNamespace(monotonic=lambda: 100.0, sleep=slept.append)
    monkeypatch.setattr(qingdao, "time", stub)
    monkeypatch.setattr(qingdao, "_last_request", 99.5)
    _REAL_THROTTLE()
    assert slept == [pytest.approx(1.5)]  # 距上次 0.5 秒，补足到 2.0


def test_config_and_search_hits_solr_endpoint(monkeypatch):
    calls = _patch_get(monkeypatch, [SEARCH_SANTI])
    page = qingdao.search_books("三体", page=2, limit=5)
    assert qingdao._CONFIG == InterlibConfig(
        city="qingdao", name_cn="青岛市公共图书馆联合目录",
        base_url="http://124.129.202.157",
    )
    path, params = calls[0]
    assert path == "/opac/api/search"
    # Solr 形态：q + rows + page + wt=json；服务端凭 page 自算 start
    # （start 参数被服务端忽略，实抓验证，见 NOTES.md）
    assert params == {"q": "三体", "rows": 5, "page": 2, "wt": "json"}
    validate_search_page(page)


def test_search_parses_solr_docs(monkeypatch):
    _patch_get(monkeypatch, [SEARCH_SANTI])
    page = qingdao.search_books("三体", page=1, limit=10)
    validate_search_page(page)
    assert page["total_results"] == 143
    assert page["total_pages"] == 15   # ceil(143 / 10)
    assert page["has_next"] is True
    assert page["page"] == 1
    assert len(page["books"]) == 10
    first = page["books"][0]
    assert first == {
        "book_id": "912374345",
        "title": "三体",
        "author": "刘慈欣",
        "publisher": "重庆出版社",
        "publish_year": "2017",
        "availability_summary": "",   # Solr 无逐书目可借概况（数据边界）
    }
    # 契约形态不带 isbn（内部字段不进 BookSummary）
    assert "isbn" not in first
    # pubdate_meta 可带月「2019.01」，取四位年份
    assert page["books"][1]["publish_year"] == "2019"


def test_search_result_total_pages_uses_requested_limit(monkeypatch):
    _patch_get(monkeypatch, [SEARCH_SANTI])
    page = qingdao.search_books("三体", page=1, limit=20)
    assert page["total_pages"] == 8    # ceil(143 / 20)


def test_search_last_page_has_no_next(monkeypatch):
    _patch_get(monkeypatch, [SEARCH_SANTI])
    page = qingdao.search_books("三体", page=15, limit=10)
    assert page["has_next"] is False
    assert page["page"] == 15


def test_search_empty_result(monkeypatch):
    _patch_get(monkeypatch, [SEARCH_EMPTY])
    page = qingdao.search_books("zzzz不存在")
    validate_search_page(page)
    assert page["books"] == []
    assert page["total_results"] == 0
    assert page["total_pages"] == 0
    assert page["has_next"] is False


def test_search_book_id_matches_detail_fixture(monkeypatch):
    # 检索 fixture（id=177071）与详情/馆藏 fixture 是同一本书，三方对得上
    _patch_get(monkeypatch, [SEARCH_ONE])
    page = qingdao.search_books("中国古代造纸史渊源")
    assert page["total_results"] == 1
    assert page["books"][0]["book_id"] == "177071"
    assert page["books"][0]["title"] == "中国古代造纸史渊源"
    assert page["books"][0]["publisher"] == "三秦出版社"


def test_search_retries_isbn_without_hyphens(monkeypatch):
    # 镜像家族 search_raw 语义：带连字符 ISBN 在 Solr 下同样命中不了（实抓验证），
    # 首搜为空且关键词含连字符时去连字符重试一次
    calls = _patch_get(monkeypatch, [SEARCH_EMPTY, SEARCH_ONE])
    page = qingdao.search_books("978-7-80628-555-3")
    assert [params["q"] for _, params in calls] == ["978-7-80628-555-3", "9787806285553"]
    assert page["books"]


def test_throttle_runs_before_every_http_request(monkeypatch):
    # ISBN 重试会发第二次请求：节流必须按「每次请求」生效，不能只在原语入口节流一次
    ticks = []
    monkeypatch.setattr(qingdao, "_throttle", lambda: ticks.append(1))
    calls = _patch_get(monkeypatch, [SEARCH_EMPTY, SEARCH_ONE])
    qingdao.search_books("978-7-80628-555-3")
    assert len(calls) == 2
    assert len(ticks) == 2


def test_hyphenated_isbn_not_retried_when_results_exist_elsewhere(monkeypatch):
    # 越界页 docs 为空但 numFound>0：关键词本身有命中，不该再白发一次去连字符请求
    calls = _patch_get(monkeypatch, [SEARCH_OUT_OF_RANGE])
    page = qingdao.search_books("978-7-5366-9293-0", page=99, limit=10)
    assert len(calls) == 1
    assert page["books"] == []
    assert page["total_results"] == 143
    assert page["has_next"] is False


def test_search_clamps_page_zero_to_served_page(monkeypatch):
    # 服务端把 page=0 当 1 服务，适配器按实际服务的页回填，否则 has_next 会指向重复页
    calls = _patch_get(monkeypatch, [SEARCH_SANTI])
    page = qingdao.search_books("三体", page=0, limit=10)
    assert calls[0][1]["page"] == 1
    assert page["page"] == 1
    assert page["has_next"] is True


def test_search_clamps_limit_zero(monkeypatch):
    # limit<=0 不能产出「total_results=143 但 total_pages=0」这种自相矛盾的分页
    calls = _patch_get(monkeypatch, [SEARCH_SANTI])
    page = qingdao.search_books("三体", limit=0)
    assert calls[0][1]["rows"] == 1
    assert page["total_results"] == 143
    assert page["total_pages"] == 143


def test_search_bad_json_raises_with_library_name(monkeypatch):
    _patch_get(monkeypatch, ["<html>opac验证</html>"])
    with pytest.raises(RuntimeError, match="青岛市公共图书馆联合目录"):
        qingdao.search_books("三体")


def test_search_missing_response_key_raises(monkeypatch):
    # 接口形态漂移或被中间层替换时，「解析不到」不得静默降级成 0 条结果
    _patch_get(monkeypatch, ['{"responseHeader": {"status": 0, "QTime": 3}}'])
    with pytest.raises(RuntimeError, match="缺少 response"):
        qingdao.search_books("三体")


def test_search_solr_error_surfaces_upstream_msg(monkeypatch):
    # Solr 查询出错同样只返回 responseHeader＋error：把上游 msg 带出来，
    # 免得把「查询本身有问题」误报成「接口形态变了」
    _patch_get(monkeypatch, [
        '{"responseHeader": {"status": 400, "QTime": 1},'
        ' "error": {"msg": "undefined field xyz", "code": 400}}',
    ])
    with pytest.raises(RuntimeError, match="undefined field xyz"):
        qingdao.search_books("三体")


def test_holdings_go_through_family(monkeypatch):
    calls = _patch_get(monkeypatch, [HOLDING, HOLDING])
    hs = qingdao.get_holdings("177071", only_available=False)
    path, params = calls[0]
    assert path == "/opac/api/holding/177071"
    assert params == {"limitLibcodes": "", "isCluster": ""}
    validate_holdings(hs)
    assert len(hs) == 4
    assert all(h["available"] for h in hs)      # 4 条全「在馆」，实抓样本无借出样例
    assert {h["library"] for h in hs} == {"崂山图书馆", "胶州图书馆", "青岛市图书馆"}
    assert hs[0]["call_number"] == "F426.83/2"
    # only_available=True 时同样 4 条（本样本全可借）
    assert len(qingdao.get_holdings("177071", only_available=True)) == 4


def test_holdings_sorts_available_first(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "胶州图书馆", "location": "九龙街道_西石河城市书房",
             "call_number": "F426.83/1", "status": "借出", "available": False,
             "due_date": "2026-11-08"},
            {"library": "青岛市图书馆", "location": "库密1（闭架5、6楼查阅）",
             "call_number": "F426.83/1", "status": "在馆", "available": True,
             "due_date": ""},
        ],
    )
    hs = qingdao.get_holdings("177071", only_available=False)
    validate_holdings(hs)
    assert [h["available"] for h in hs] == [True, False]
    assert hs[1]["due_date"] == "2026-11-08"


def test_book_detail_parses_family_view(monkeypatch):
    calls = _patch_get(monkeypatch, [DETAIL])
    d = qingdao.get_book_detail("177071")
    path, params = calls[0]
    assert path == "/opac/book/177071"
    assert params is None                       # 青岛详情无需 curlibcode 参数
    validate_book_detail(d)
    assert d == {
        "book_id": "177071",
        "title": "中国古代造纸史渊源",
        "author": "杨巨中",
        "publisher": "三秦出版社",
        "publish_year": "2001",
        "isbn": "7-80628-555-5",
        # 家族口径：call_number 取「中图分类法」值；页内独立「索书号」行不参与解析，
        # 完整索书号（F426.83/2）在馆藏 JSON callno 里
        "call_number": "F426.83",
        "summary": "本书主要内容包括：中国古代纸源问题的研讨方法；春秋战国时期的茧絮纸；"
                   "西汉纸；东汉蔡侯纸；蔡侯纸的历史意义等。",
    }


def test_book_detail_not_found(monkeypatch):
    _patch_get(monkeypatch, ["<html><body></body></html>"])
    with pytest.raises(RuntimeError, match="未找到"):
        qingdao.get_book_detail("1")


def test_error_wraps_with_library_name(monkeypatch):
    def boom(cfg, path, params=None):
        raise RuntimeError("青岛市公共图书馆联合目录请求失败：reset")

    monkeypatch.setattr(_family_client, "get", boom)
    with pytest.raises(RuntimeError, match="青岛市公共图书馆联合目录"):
        qingdao.search_books("三体")
    with pytest.raises(RuntimeError, match="青岛市公共图书馆联合目录"):
        qingdao.get_book_detail("177071")
