"""大连适配器检索：会话/token 流、ISBN→GENERAL 路由、分页 JUMP、会话失效重建、
非空 books 的 record_id→book_id 委托转换、base.validate_search_page 自断言。

mock 点为模块级 `_open(req, timeout)`：按请求内容路由到 fixture，记录 (url, data)。
单测严禁触网。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters.cn import dalian
from mcp_library_search.adapters.base import validate_search_page

_FIX = Path(__file__).parent / "fixtures" / "dalian"
_ENTRY = (_FIX / "entry_raw.html").read_text(encoding="utf-8")
_SEARCH = (_FIX / "search.html").read_text(encoding="utf-8")
_P2 = (_FIX / "search_p2.html").read_text(encoding="utf-8")
_EMPTY = (_FIX / "search_empty.html").read_text(encoding="utf-8")
_PHRASE = (_FIX / "search_phrase.html").read_text(encoding="utf-8")


def _router(monkeypatch, search_resp=_SEARCH, jump_resp=_P2, entry_resp=_ENTRY):
    """按请求内容路由：GET→入口页；JUMP POST→翻页页；其余 POST(检索)→search_resp。"""
    calls = []

    def spy(req, timeout=25):
        calls.append((req.full_url, req.data))
        if req.data is None:
            return entry_resp
        body = req.data.decode()
        if "JUMP%5E" in body:
            return jump_resp
        return search_resp

    monkeypatch.setattr(dalian, "_open", spy)
    return calls


def _seq(monkeypatch, pages):
    """按顺序返回 pages；记录 (url, data)。用于会话失效重建分支。"""
    calls = []
    seq = iter(pages)

    def spy(req, timeout=25):
        calls.append((req.full_url, req.data))
        return next(seq)

    monkeypatch.setattr(dalian, "_open", spy)
    return calls


def test_search_posts_to_form_action_with_general_field(monkeypatch):
    calls = _router(monkeypatch)
    page = dalian.search_books("三体")
    # 第一步 GET 入口页，第二步 POST 到入口页 searchform 的 action（带当次 ps token）
    assert calls[0][1] is None
    assert "cgisirsi" in calls[0][0]
    assert calls[1][1] is not None
    body = calls[1][1].decode()
    assert "searchdata1=" in body
    # 无 ISBN 专用字段 → 统一 GENERAL（所有字段）
    assert "srchfield1=GENERAL" in body
    assert "library=ALL" in body and "sort_by=ANY" in body
    validate_search_page(page)


def test_search_sends_quoted_phrase(monkeypatch):
    calls = _router(monkeypatch, search_resp=_PHRASE)
    page = dalian.search_books("三体")
    body = calls[1][1].decode()
    # 源站裸词是逐字 AND 宽匹配（无相关度）→ 一律按短语（ASCII 双引号）下发
    assert "searchdata1=%22%E4%B8%89%E4%BD%93%22" in body
    # 所有字段短语检索实测 132 条（裸词同一关键词为 27944 条）
    assert page["total_results"] == 132
    assert page["books"][0]["title"].startswith("赡养人类")
    validate_search_page(page)


def test_user_supplied_quotes_not_double_wrapped(monkeypatch):
    calls = _router(monkeypatch)
    dalian.search_books('"三体"')
    body = calls[1][1].decode()
    assert "searchdata1=%22%E4%B8%89%E4%BD%93%22" in body
    assert "%22%22" not in body  # 不二次包裹


def test_search_phrase_zero_falls_back_to_bare(monkeypatch):
    # 词含源站短语索引不收的字符（罗马数字 Ⅲ）→ 短语 0 命中 → 退回裸词再试一次
    calls = []

    def spy(req, timeout=25):
        calls.append((req.full_url, req.data))
        if req.data is None:
            return _ENTRY
        body = req.data.decode()
        return _EMPTY if "%22" in body else _SEARCH

    monkeypatch.setattr(dalian, "_open", spy)
    page = dalian.search_books("三体Ⅲ")
    posts = [c for c in calls if c[1] is not None]
    assert "searchdata1=%22%E4%B8%89%E4%BD%93%E2%85%A2%22" in posts[0][1].decode()
    assert "%22" not in posts[1][1].decode()
    assert page["total_results"] == 862


def test_search_parses_total_and_maps_book_id(monkeypatch):
    _router(monkeypatch)
    page = dalian.search_books("三体")
    assert page["total_results"] == 862
    assert page["page"] == 1
    assert page["total_pages"] == 44  # ceil(862/20)
    assert page["has_next"] is True
    assert len(page["books"]) == 20
    # 委托转换：_Book.record_id → BookSummary.book_id（architecture.md 硬契约）
    b0 = page["books"][0]
    assert b0["book_id"].startswith("3351016:")
    assert b0["title"].startswith("腾格里沙漠的造林人")
    assert b0["author"] == "王也丹 著"
    assert b0["publish_year"] == "2021"
    assert b0["availability_summary"] == "1 馆藏于 长海分馆 在 长海少儿库"
    # 三体Ⅲ（catkey 3305715）在第 3 位
    ids = [b["book_id"] for b in page["books"]]
    assert any(i.startswith("3305715:") for i in ids)


def test_isbn_keyword_routes_to_general(monkeypatch):
    calls = _router(monkeypatch)
    dalian.search_books("9787229100629")
    body = calls[1][1].decode()
    # ISBN 形态也走 GENERAL（iLink 无 ISBN 字段，NOTES 已记录）；同样按短语下发
    assert "srchfield1=GENERAL" in body
    assert "searchdata1=%229787229100629%22" in body


def test_search_empty_result(monkeypatch):
    _router(monkeypatch, search_resp=_EMPTY)
    page = dalian.search_books("zzz不存在书名qqq9527")
    assert page["total_results"] == 0
    assert page["books"] == []
    assert page["total_pages"] == 1
    assert page["has_next"] is False
    validate_search_page(page)


def test_page_two_uses_jump_post(monkeypatch):
    calls = _router(monkeypatch, jump_resp=_P2)
    page = dalian.search_books("三体", page=2)
    # 翻页走 hitlist 表单 POST form_type=JUMP^21
    jump_calls = [c for c in calls if c[1] and "JUMP%5E21" in c[1].decode()]
    assert len(jump_calls) == 1
    assert page["page"] == 2
    assert page["total_pages"] == 44
    assert page["has_next"] is True
    assert page["books"][0]["book_id"].startswith("2646511:")
    validate_search_page(page)


def test_search_session_rebuild_once(monkeypatch):
    # 检索 POST 首次退回入口页(会话失效特征)→重建→第二次成功
    calls = _seq(monkeypatch, [_ENTRY, _ENTRY, _ENTRY, _SEARCH])
    page = dalian.search_books("三体")
    assert len(calls) == 4
    assert page["total_results"] == 862
    assert page["books"][0]["book_id"].startswith("3351016:")


def test_search_rebuild_only_once_then_raises(monkeypatch):
    calls = _seq(monkeypatch, [_ENTRY, _ENTRY, _ENTRY, _ENTRY])
    with pytest.raises(RuntimeError, match="大连图书馆"):
        dalian.search_books("三体")
    assert len(calls) == 4  # 重建后仅重试一次，不无限循环
