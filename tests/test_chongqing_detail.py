"""重庆适配器详情与馆藏：字段解析、分馆列表、无单册状态时的保守语义。

fixture 结论（NOTES.md）：详情页无索书号字段；馆藏信息 tab 只有分馆名；
单册状态需读者登录（GetAsset 匿名被拦），故 holdings 一律保守 available=False。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters import chongqing

_FIXTURES = Path(__file__).parent / "fixtures" / "chongqing"
_SESSION = (_FIXTURES / "session.html").read_text(encoding="utf-8")
_DETAIL = (_FIXTURES / "detail.html").read_text(encoding="utf-8")


def _mock_open(monkeypatch, pages):
    calls = []
    seq = iter(pages)

    def spy(req, timeout=20):
        calls.append((req.full_url, req.data))
        return next(seq)

    monkeypatch.setattr(chongqing, "_open", spy)
    return calls


def test_get_book_detail_fields(monkeypatch):
    _mock_open(monkeypatch, [_SESSION, _DETAIL])
    d = chongqing.get_book_detail("i_biblios:2649440")
    assert d["title"] == "三体"
    assert d["author"] == "刘慈欣著"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2022"
    assert d["isbn"] == "9787229166922"
    # 详情页不显示索书号（检索条目有、详情页无），如实返回空
    assert d["call_number"] == ""
    # 本书简介在源站即为空
    assert d["summary"] == ""


def test_get_holdings_lists_libraries(monkeypatch):
    _mock_open(monkeypatch, [_SESSION, _DETAIL])
    hs = chongqing.get_holdings("i_biblios:2649440", only_available=False)
    assert len(hs) == 1
    assert hs[0]["library"] == "重庆图书馆"
    assert hs[0]["location"] == ""
    assert hs[0]["call_number"] == ""
    # 源站不公开单册状态：无原值可返回，保守 False（与穗杭未匹配状态词一致）
    assert hs[0]["status"] == ""
    assert hs[0]["available"] is False
    assert hs[0]["due_date"] == ""


def test_get_holdings_default_only_available_is_empty(monkeypatch):
    _mock_open(monkeypatch, [_SESSION, _DETAIL])
    assert chongqing.get_holdings("i_biblios:2649440") == []


def test_get_book_detail_session_rebuild_then_raises(monkeypatch):
    calls = _mock_open(monkeypatch, [_SESSION, _SESSION, _SESSION, _SESSION])
    with pytest.raises(RuntimeError, match="重庆图书馆"):
        chongqing.get_book_detail("i_biblios:2649440")
    assert len(calls) == 4


def test_bad_book_id_raises(monkeypatch):
    with pytest.raises(RuntimeError, match="book_id"):
        chongqing.get_book_detail("2649440")
