"""iLink 家族会话流测试（离线，monkeypatch `client._open`）：验证三城共用同一实例、
仅以 Config 的 `library_code` 做馆别过滤，以及 token 逐步解析、翻页、会话重建、
短语优先/裸词兜底。真网请求一律被 fixture 路由替换。
"""
import urllib.parse
from pathlib import Path

import pytest

from mcp_library_search.adapters.cn import gannan, gansu_prov, longnan
from mcp_library_search.ilink import client as ilink_client
from mcp_library_search.ilink import parser

_FIX = Path(__file__).parent / "fixtures"
_ENTRY = (_FIX / "gansu_prov" / "entry_raw.html").read_text(encoding="utf-8")
_GS_SEARCH = (_FIX / "gansu_prov" / "search_prov.html").read_text(encoding="utf-8")
_GS_P2 = (_FIX / "gansu_prov" / "search_p2.html").read_text(encoding="utf-8")
_GS_EMPTY = (_FIX / "gansu_prov" / "search_empty.html").read_text(encoding="utf-8")

# (适配器模块, 馆别码, 实抓检索页, 实抓「三体」总数)
_CASES = [
    (gansu_prov, "甘肃馆", "gansu_prov/search_prov.html", 101),
    (longnan, "陇南馆", "longnan/search.html", 4),
    (gannan, "甘南馆", "gannan/search.html", 3),
]


def _router(monkeypatch, search_resp, jump_resp=None, entry_resp=_ENTRY):
    """按请求内容路由：GET→入口页；JUMP POST→翻页页；其余检索 POST→search_resp。"""
    calls = []

    def spy(cfg, req, timeout=25):
        calls.append((req.full_url, req.data))
        if req.data is None:
            return entry_resp
        body = req.data.decode()
        if "JUMP%5E" in body:
            return jump_resp if jump_resp is not None else search_resp
        return search_resp

    monkeypatch.setattr(ilink_client, "_open", spy)
    return calls


def _posts(calls):
    return [urllib.parse.parse_qs(c[1].decode()) for c in calls if c[1] is not None]


@pytest.mark.parametrize("mod, code, search_file, total", _CASES)
def test_library_code_is_posted_and_result_mapped(monkeypatch, mod, code, search_file, total):
    search = (_FIX / search_file).read_text(encoding="utf-8")
    calls = _router(monkeypatch, search)
    page = mod.search_books("三体")
    # 第一步 GET 入口页，第二步 POST 检索
    assert calls[0][1] is None
    search_post = [q for q in _posts(calls) if "searchdata1" in q][0]
    assert search_post["library"] == [code]           # 馆别过滤：三城仅此不同
    assert search_post["searchdata1"] == ['"三体"']    # 一律按 ASCII 双引号短语下发
    assert search_post["srchfield1"] == ["GENERAL^SUBJECT^GENERAL^^所有字段"]
    assert search_post["sort_by"] == ["TI"]           # 入口页 hidden sort_by 原值
    assert page["total_results"] == total
    assert page["page"] == 1
    assert len(page["books"]) == (total if total < 20 else 20)


def test_gansu_phrase_first_zero_falls_back_to_bare(monkeypatch):
    calls = []

    def spy(cfg, req, timeout=25):
        calls.append((req.full_url, req.data))
        if req.data is None:
            return _ENTRY
        # 短语（带 %22）0 命中 → 退回裸词返回非空结果页
        return _GS_EMPTY if "%22" in req.data.decode() else _GS_SEARCH

    monkeypatch.setattr(ilink_client, "_open", spy)
    page = gansu_prov.search_books("三体")
    sent = [q["searchdata1"][0] for q in _posts(calls)]
    assert sent[0] == '"三体"' and sent[1] == "三体"
    assert page["total_results"] == 101


def test_gansu_page_two_uses_jump(monkeypatch):
    calls = _router(monkeypatch, _GS_SEARCH, jump_resp=_GS_P2)
    page = gansu_prov.search_books("三体", page=2)
    assert any("JUMP%5E21" in c[1].decode() for c in calls if c[1])
    assert page["page"] == 2
    assert page["total_pages"] == 6  # ceil(101/20)
    assert page["books"][0]["book_id"].startswith("1493012:")


def test_gansu_session_rebuild_once(monkeypatch):
    seq = iter([_ENTRY, _ENTRY, _ENTRY, _GS_SEARCH])
    calls = []

    def spy(cfg, req, timeout=25):
        calls.append((req.full_url, req.data))
        return next(seq)

    monkeypatch.setattr(ilink_client, "_open", spy)
    page = gansu_prov.search_books("三体")
    assert len(calls) == 4  # 检索 POST 首次退回入口页（会话失效）→ 重建 → 成功
    assert page["total_results"] == 101


def test_helpers_shared_by_family():
    assert parser.is_result_page(_GS_SEARCH)
    assert gansu_prov._CONFIG.base_url == longnan._CONFIG.base_url == gannan._CONFIG.base_url
    assert {gansu_prov._CONFIG.library_code, longnan._CONFIG.library_code,
            gannan._CONFIG.library_code} == {"甘肃馆", "陇南馆", "甘南馆"}
