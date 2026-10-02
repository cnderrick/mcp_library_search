"""重庆适配器详情与馆藏：字段解析、单册级馆藏（GetAsset 根路径）、回退与保守语义。

fixture 结论（NOTES.md）：详情页无索书号字段；单册数据走根路径 GetAsset.action
（匿名 200，两次实证）；frontV2 前缀同名 action 有登录拦截（302），不用。
可借口径统一保守：源站无明确「可借/在架」状态词，「入藏」语义不确定也判 False，
status 原值照登；确定借出（status 含「借出」）带 due_date。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters import chongqing

_FIXTURES = Path(__file__).parent / "fixtures" / "chongqing"
_SESSION = (_FIXTURES / "session.html").read_text(encoding="utf-8")
_DETAIL = (_FIXTURES / "detail.html").read_text(encoding="utf-8")
_ASSET = (_FIXTURES / "get_asset.json").read_text(encoding="utf-8")
_LOGIN = (_FIXTURES / "get_asset_anonymous.html").read_text(encoding="utf-8")


def _mock_open(monkeypatch, pages):
    calls = []
    seq = iter(pages)

    def spy(req, timeout=20):
        calls.append((req.full_url, req.data))
        return next(seq)

    monkeypatch.setattr(chongqing, "_open", spy)
    return calls


def _mock_open_by_url(monkeypatch, asset_response):
    """按 URL 路由：GetAsset → asset_response；SearchIndex → 会话页；其余 → 详情页。"""
    calls = []

    def spy(req, timeout=20):
        calls.append((req.full_url, req.data))
        if "GetAsset.action" in req.full_url:
            return asset_response
        if "SearchIndex" in req.full_url:
            return _SESSION
        return _DETAIL

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


def test_get_holdings_per_item_from_getasset(monkeypatch):
    calls = _mock_open_by_url(monkeypatch, _ASSET)
    hs = chongqing.get_holdings("i_biblios:2925752", only_available=False)
    # 首请求即根路径 GetAsset（无需会话），POST 参数齐全
    assert "InDigLib/GetAsset.action" in calls[0][0]
    assert "frontV2" not in calls[0][0]
    body = calls[0][1].decode()
    assert "metatables=i_biblios" in body
    assert "metaids=2925752" in body and "type=map" in body
    # 5 册单册数据：索书号/馆藏地点/状态原值全齐
    assert len(hs) == 5
    assert all(h["library"] == "重庆图书馆" for h in hs)
    assert all(h["call_number"] == "TS976.15/585" for h in hs)
    assert {h["location"] for h in hs} == {"重庆馆通借库", "重图基藏库(四楼)", "重图在线借阅"}
    assert {h["status"] for h in hs} == {"入藏", "普通借出"}
    # 统一保守口径：无明确「可借」状态词，「入藏」也判 False
    assert all(h["available"] is False for h in hs)
    # 确定借出的那册带应还日期
    loaned = [h for h in hs if h["status"] == "普通借出"]
    assert len(loaned) == 1
    assert loaned[0]["due_date"] == "2026-08-17"
    assert all(h["due_date"] == "" for h in hs if h["status"] == "入藏")


def test_get_holdings_blocked_getasset_falls_back_to_library_level(monkeypatch):
    # 根路径若哪天也被拦（返回登录页 HTML 而非 JSON）→ 回退详情页馆名级（旧行为）
    calls = _mock_open_by_url(monkeypatch, _LOGIN)
    hs = chongqing.get_holdings("i_biblios:2649440", only_available=False)
    assert len(hs) == 1
    assert hs[0]["library"] == "重庆图书馆"
    assert hs[0]["status"] == "" and hs[0]["available"] is False
    urls = [u for u, _ in calls]
    assert any("SearchIndex" in u for u in urls)
    assert any("BookDetail.action" in u for u in urls)


def test_get_holdings_default_only_available_is_empty(monkeypatch):
    # 统一保守口径的直接后果：only_available=True 恒为空，调用方需用 False 看全部原值
    _mock_open_by_url(monkeypatch, _ASSET)
    assert chongqing.get_holdings("i_biblios:2925752") == []


def test_get_book_detail_session_rebuild_then_raises(monkeypatch):
    calls = _mock_open(monkeypatch, [_SESSION, _SESSION, _SESSION, _SESSION])
    with pytest.raises(RuntimeError, match="重庆图书馆"):
        chongqing.get_book_detail("i_biblios:2649440")
    assert len(calls) == 4


def test_bad_book_id_raises(monkeypatch):
    with pytest.raises(RuntimeError, match="book_id"):
        chongqing.get_book_detail("2649440")
