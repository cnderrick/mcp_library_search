"""无锡适配器测试：图星 LibStar Find 三原语 + 天津式多源预留。

mock 点在模块 HTTP 出口 `_request`（对应青岛的 `interlib.client.get`）；
必需请求头另有一条直接打到 `urlopen` 的回归测试（本城最大的坑，见 NOTES.md）。
"""
import json

import pytest

from mcp_library_search.adapters.cn import wuxi
from mcp_library_search.adapters.base import (
    validate_book_detail, validate_holdings, validate_search_page,
)

_FIXTURES = "tests/fixtures/wuxi/"
SEARCH_SANTI = json.loads(open(_FIXTURES + "search_santi.json", encoding="utf-8").read())
SEARCH_SHANGYIN = json.loads(open(_FIXTURES + "search_shangyin.json", encoding="utf-8").read())
DETAIL = json.loads(open(_FIXTURES + "detail_shangyin.json", encoding="utf-8").read())
DETAIL_SIKAO = json.loads(open(_FIXTURES + "detail_sikao.json", encoding="utf-8").read())
HOLDINGS = json.loads(open(_FIXTURES + "holdings_shangyin.json", encoding="utf-8").read())


@pytest.fixture(autouse=True)
def _no_throttle(monkeypatch):
    monkeypatch.setattr(wuxi, "_throttle", lambda: None)


def _patch_request(monkeypatch, responses):
    """按顺序返回 responses；记录 (path, payload, params) 列表。"""
    calls = []
    seq = iter(responses)

    def spy(path, payload=None, params=None):
        calls.append((path, payload, params))
        return next(seq)

    monkeypatch.setattr(wuxi, "_request", spy)
    return calls


# ---------- HTTP 层与必需请求头 ----------


class _FakeResponse:
    def __init__(self, body):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_request_always_sends_referer_and_groupcode(monkeypatch):
    """本城核心回归：缺 Referer 全站内容端点回 9999，缺 groupcode 静默 0 结果。

    2026-10-02 初判「无锡不通」正是漏了 Referer——这条测试锁死它不再发生。
    """
    seen = {}

    def fake_urlopen(req, timeout=None):
        seen["headers"] = {k.lower(): v for k, v in req.header_items()}
        seen["url"] = req.full_url
        return _FakeResponse('{"success": true, "data": {"numFound": 0, "searchResult": []}}')

    monkeypatch.setattr(wuxi.urllib.request, "urlopen", fake_urlopen)
    wuxi._request("/find/unify/search", payload={"a": 1})

    assert seen["headers"]["referer"] == wuxi._BASE + "/"
    assert seen["headers"]["groupcode"] == "800507"
    assert seen["url"] == wuxi._BASE + "/find/unify/search"


def test_request_missing_referer_error_names_the_header():
    """errCode 9999 是本站的反爬兜底，报错要把它翻译成「漏带 Referer」。"""
    payload = {"success": False, "message": "系统访问中断，请稍后再试！", "errCode": 9999, "data": None}
    with pytest.raises(RuntimeError, match="9999[\\s\\S]*Referer"):
        wuxi._parse_search(payload)


def test_request_network_error_wraps_with_library_name(monkeypatch):
    """网络层失败（TLS 重置/超时）要带上馆名上抛，不能裸抛 URLError。"""
    def boom(req, timeout=None):
        raise wuxi.urllib.error.URLError("connection reset by peer")

    monkeypatch.setattr(wuxi.urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError, match="无锡市新吴区图书馆"):
        wuxi.search_books("三体")


def test_request_non_json_body_raises_with_library_name(monkeypatch):
    """被中间层换成 HTML（登录页/拦截页）时要点名，不静默降级。"""
    monkeypatch.setattr(wuxi.urllib.request, "urlopen",
                        lambda req, timeout=None: _FakeResponse("<html>拦截</html>"))
    with pytest.raises(RuntimeError, match="无锡市新吴区图书馆"):
        wuxi.search_books("三体")


# ---------- 契约缝 ----------


def test_module_client_shape():
    assert hasattr(wuxi, "_client")
    for meth in ("search", "get_holdings", "get_book_detail"):
        assert callable(getattr(wuxi._client, meth))


def test_search_hits_search_endpoint_with_echoed_body(monkeypatch):
    calls = _patch_request(monkeypatch, [SEARCH_SANTI])
    wuxi.search_books("三体", page=2, limit=5)
    path, payload, params = calls[0]
    assert path == "/find/unify/search"
    assert params is None
    assert payload["searchFieldContent"] == "三体"
    assert payload["searchField"] == "keyWord"
    assert payload["matchMode"] == "2"
    assert payload["page"] == 2
    assert payload["rows"] == 5
    assert payload["indexSearch"] == 1


def test_search_body_is_a_copy_not_mutating_the_template(monkeypatch):
    """模板是模块级常量，逐次调用必须复制，否则关键词会串到下次请求。"""
    _patch_request(monkeypatch, [SEARCH_SANTI, SEARCH_SHANGYIN])
    wuxi.search_books("三体")
    wuxi.search_books("上瘾")
    assert wuxi._SEARCH_BODY["searchFieldContent"] == ""


# ---------- 检索 ----------


def test_search_books_prefixes_source_id(monkeypatch):
    """book_id 带源前缀，将来并入市图源时不改变既有 id 契约。"""
    _patch_request(monkeypatch, [SEARCH_SHANGYIN])
    page = wuxi.search_books("上瘾", page=1, limit=10)
    validate_search_page(page)
    assert page["books"][0]["book_id"] == "WXXW:703048"


def test_search_paging_math(monkeypatch):
    _patch_request(monkeypatch, [SEARCH_SHANGYIN])
    page = wuxi.search_books("上瘾", page=1, limit=10)
    assert page["total_results"] == 83
    assert page["total_pages"] == 9      # ceil(83 / 10)
    assert page["has_next"] is True
    assert page["page"] == 1


def test_search_last_page_has_no_next(monkeypatch):
    _patch_request(monkeypatch, [SEARCH_SHANGYIN])
    page = wuxi.search_books("上瘾", page=9, limit=10)
    assert page["has_next"] is False


def test_search_empty_result(monkeypatch):
    _patch_request(monkeypatch, [{"success": True, "errCode": 200,
                                  "data": {"numFound": 0, "searchResult": []}}])
    page = wuxi.search_books("zzz不存在")
    validate_search_page(page)
    assert page["books"] == []
    assert page["total_results"] == 0
    assert page["total_pages"] == 0


def test_search_zero_groupcode_hits_raise_not_silent_empty(monkeypatch):
    """漏带 groupcode 时站点回 200 + numFound=0——本适配器无法在响应里分辨，
    但 errCode 9999 必须报错（见上）。此条只锁「真 0 命中」不报错。"""
    _patch_request(monkeypatch, [{"success": True, "errCode": 200,
                                  "data": {"numFound": 0, "searchResult": []}}])
    assert wuxi.search_books("zzz")["total_results"] == 0


# ---------- 馆藏 ----------


def test_holdings_strip_source_prefix_before_request(monkeypatch):
    calls = _patch_request(monkeypatch, [HOLDINGS])
    wuxi.get_holdings("WXXW:703048", only_available=False)
    path, payload, _ = calls[0]
    assert path == "/find/physical/groupItemsByLibCode"
    assert payload == {"recordId": "703048"}


def test_holdings_maps_and_sorts(monkeypatch):
    _patch_request(monkeypatch, [HOLDINGS])
    hs = wuxi.get_holdings("WXXW:703048", only_available=False)
    validate_holdings(hs)
    assert len(hs) == 5
    assert hs[0]["available"] is True          # 可借的排前面
    assert [h["available"] for h in hs] == [True, True, True, False, False]
    borrowed = [h for h in hs if not h["available"]]
    assert {h["due_date"] for h in borrowed} == {"2025-10-10", "2026-10-30"}


def test_holdings_only_available_filters(monkeypatch):
    _patch_request(monkeypatch, [HOLDINGS])
    hs = wuxi.get_holdings("WXXW:703048", only_available=True)
    assert len(hs) == 3
    assert all(h["available"] for h in hs)


def test_holdings_empty_for_record_the_index_still_counts(monkeypatch):
    """数据边界：源站检索索引的 `physicalCount` 与馆藏端点会不一致。

    实抓 143656（《活着》李玉霄版）：索引计 1 册，而 `groupItemsByLibCode`、
    `physical/groupitems`、`getCatalog` 三种取法都返回空。馆藏端点为准，如实返回
    空列表，不拿索引计数编造馆藏。
    """
    _patch_request(monkeypatch, [{"success": True, "errCode": 200, "data": {"sortedList": {}}}])
    assert wuxi.get_holdings("WXXW:143656", only_available=False) == []


def test_holdings_library_is_plain_name_not_prefixed(monkeypatch):
    """馆名原值照登（不带源前缀），位置与索书号各取对字段。"""
    _patch_request(monkeypatch, [HOLDINGS])
    hs = wuxi.get_holdings("WXXW:703048", only_available=True)
    # 可借的排前面：原第 2 册（借出册被排到后面）升到首位
    assert hs[0]["library"] == "无锡市新吴区图书馆"
    assert hs[0]["location"] == "伯渎河文化中心图书馆三层"
    assert hs[0]["call_number"] == "TB472/0027 2017 C:3"


# ---------- 详情 ----------


def test_book_detail_hits_get_endpoint(monkeypatch):
    calls = _patch_request(monkeypatch, [DETAIL])
    d = wuxi.get_book_detail("WXXW:703048")
    path, payload, params = calls[0]
    assert path == "/find/searchResultDetail/getBookDetail"
    assert payload is None                     # 详情是 GET（POST 同参数回 9999）
    assert params == {"recordId": "703048"}
    validate_book_detail(d)
    assert d["book_id"] == "WXXW:703048"
    assert d["title"] == "上瘾:让用户养成使用习惯的四大产品逻辑"
    assert d["isbn"] == "978-7-5086-6831-4"


def test_book_detail_keeps_queried_id_verbatim(monkeypatch):
    """复合 id 取首成员详情时，回填的 book_id 是查询原样（天津口径）。"""
    _patch_request(monkeypatch, [DETAIL])
    assert wuxi.get_book_detail("WXXW:703048")["book_id"] == "WXXW:703048"


# ---------- 多源预留（天津口径） ----------


def test_source_table_reserves_city_library():
    """市图源槽位预留：优先级在主馆在前，但尚未接入（不在 _SOURCES 里）。"""
    assert wuxi._SOURCE_PRIORITY[0] == "WXST"
    assert "WXXW" in wuxi._SOURCES
    assert "WXST" not in wuxi._SOURCES


def test_split_book_id_single_member():
    assert wuxi._split_book_id("WXXW:703048") == [("WXXW", "703048")]


def test_split_book_id_composite_ordered_by_priority():
    assert wuxi._split_book_id("WXXW:2+WXST:1") == [("WXST", "1"), ("WXXW", "2")]


def test_split_book_id_rejects_malformed():
    with pytest.raises(RuntimeError, match="未知 book_id 形态"):
        wuxi._split_book_id("703048")


def test_split_book_id_rejects_unknown_source():
    with pytest.raises(RuntimeError, match="未知 book_id 形态"):
        wuxi._split_book_id("BOGUS:1")


def test_reserved_source_search_is_not_dispatched():
    """预留源未接入：拿它的 book_id 查馆藏要给出明确报错，而不是静默空。"""
    with pytest.raises(RuntimeError, match="尚未接入"):
        wuxi.get_holdings("WXST:1", only_available=False)


def test_merge_books_single_source_passes_through():
    b = wuxi._Book(record_id="WXXW:1", title="三体", isbn="9787536692930")
    assert wuxi._merge_books({"WXXW": [b]}) == [b]


def test_merge_books_joins_same_isbn_across_sources():
    """同 ISBN 跨源命中合成复合 id（主馆在前），书目字段取优先级最高成员。"""
    zhu = wuxi._Book(record_id="WXST:1", title="三体（市图）", isbn="978-7-5366-9293-0")
    xin = wuxi._Book(record_id="WXXW:2", title="三体（新吴）", isbn="9787536692930")
    merged = wuxi._merge_books({"WXXW": [xin], "WXST": [zhu]})
    assert len(merged) == 1
    assert merged[0].record_id == "WXST:1+WXXW:2"
    assert merged[0].title == "三体（市图）"


def test_merge_books_keeps_isbn_less_entries_separate():
    a = wuxi._Book(record_id="WXXW:1", title="无 ISBN 甲", isbn="")
    b = wuxi._Book(record_id="WXST:2", title="无 ISBN 乙", isbn="")
    merged = wuxi._merge_books({"WXXW": [a], "WXST": [b]})
    assert [m.record_id for m in merged] == ["WXST:2", "WXXW:1"]
