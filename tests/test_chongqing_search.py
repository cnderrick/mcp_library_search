"""重庆适配器检索：会话建立、ISBN 路由、分页统计、会话失效重建一次。

mock 点为模块级 `_open(req, timeout)`：req 是 urllib Request，
测试里按顺序返回 fixture 文本并记录 (full_url, data)。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters.cn import chongqing

_FIXTURES = Path(__file__).parent / "fixtures" / "chongqing"
_SESSION = (_FIXTURES / "session.html").read_text(encoding="utf-8")
_SEARCH = (_FIXTURES / "search.html").read_text(encoding="utf-8")


def _mock_open(monkeypatch, pages):
    """按顺序返回 pages；记录 (full_url, data)。"""
    calls = []
    seq = iter(pages)

    def spy(req, timeout=20):
        calls.append((req.full_url, req.data))
        return next(seq)

    monkeypatch.setattr(chongqing, "_open", spy)
    return calls


def test_search_establishes_session_then_posts(monkeypatch):
    calls = _mock_open(monkeypatch, [_SESSION, _SEARCH])
    page = chongqing.search_books("三体")
    assert calls[0][0].endswith("SearchIndex!simple.action?opacType=local")
    assert calls[0][1] is None  # 会话页是 GET
    assert "OpacMarcSearchSolr!simpleSearch.action" in calls[1][0]
    body = calls[1][1].decode()
    assert "select1=all" in body
    assert "text1=" in body
    assert page["books"][0]["book_id"] == "i_biblios:2649440"
    assert page["books"][0]["title"] == "三体"
    assert page["total_pages"] == 38
    assert page["total_results"] is None  # 源站只给总页数，不给总条数
    assert page["has_next"] is True


def test_isbn_keyword_uses_isbn_select1(monkeypatch):
    calls = _mock_open(monkeypatch, [_SESSION, _SEARCH])
    chongqing.search_books("9787508687193")
    assert "select1=isbn" in calls[1][1].decode()


def test_hyphenated_isbn_uses_isbn_select1(monkeypatch):
    calls = _mock_open(monkeypatch, [_SESSION, _SEARCH])
    chongqing.search_books("978-7-5086-8719-3")
    assert "select1=isbn" in calls[1][1].decode()


def test_page_two_uses_get_pageno(monkeypatch):
    calls = _mock_open(monkeypatch, [_SESSION, _SEARCH])
    page = chongqing.search_books("三体", page=2)
    assert "pageNo=2" in calls[1][0]
    assert calls[1][1] is None  # 翻页走 GET（结果页分页链接形态）
    assert page["has_next"] is True
    assert page["total_pages"] == 38


def test_session_expired_rebuilds_once(monkeypatch):
    # GET 会话页 → POST 返回检索首页（会话失效特征）→ 重建会话 → POST 成功
    calls = _mock_open(monkeypatch, [_SESSION, _SESSION, _SESSION, _SEARCH])
    page = chongqing.search_books("三体")
    assert len(calls) == 4
    assert page["books"][0]["book_id"] == "i_biblios:2649440"


def test_session_rebuild_only_once_then_raises(monkeypatch):
    calls = _mock_open(monkeypatch, [_SESSION, _SESSION, _SESSION, _SESSION])
    with pytest.raises(RuntimeError, match="重庆图书馆"):
        chongqing.search_books("三体")
    assert len(calls) == 4  # 重建后仅重试一次，不无限循环
