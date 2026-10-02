"""大连适配器详情与馆藏：题名重检索→catkey 定位→VIEW^N 取详情、字段解析、
索书号级馆藏、在架上/馆藏于可借口径、会话失效重建、base.validate_* 自断言。

mock 点为模块级 `_open`：按请求内容路由（GET→入口、VIEW POST→详情、其余→检索页）。
单测严禁触网。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters import dalian
from mcp_library_search.adapters.base import validate_book_detail, validate_holdings

_FIX = Path(__file__).parent / "fixtures" / "dalian"
_ENTRY = (_FIX / "entry_raw.html").read_text(encoding="utf-8")
_SEARCH = (_FIX / "search.html").read_text(encoding="utf-8")
_EMPTY = (_FIX / "search_empty.html").read_text(encoding="utf-8")
_ERROR = (_FIX / "error_message.html").read_text(encoding="utf-8")
_DETAIL = (_FIX / "detail.html").read_text(encoding="utf-8")
_LOCATED = (_FIX / "detail_located.html").read_text(encoding="utf-8")

_ID_SANTI = "3305715:三体 Ⅲ 死神永生 专著 典藏版 刘慈欣著"
_ID_TENGELI = "3351016:腾格里沙漠的造林人——八步沙林场“六老汉”三代人治沙造林先进群体 专著 王也丹著 冉少丹绘"


def _router(monkeypatch, search_resp=_SEARCH, view_resp=_DETAIL):
    calls = []

    def spy(req, timeout=25):
        calls.append((req.full_url, req.data))
        if req.data is None:
            return _ENTRY
        if "VIEW%5E" in req.data.decode():
            return view_resp
        return search_resp

    monkeypatch.setattr(dalian, "_open", spy)
    return calls


def _seq(monkeypatch, pages):
    calls = []
    seq = iter(pages)

    def spy(req, timeout=25):
        calls.append((req.full_url, req.data))
        return next(seq)

    monkeypatch.setattr(dalian, "_open", spy)
    return calls


def test_get_book_detail_relocates_and_parses(monkeypatch):
    calls = _router(monkeypatch, view_resp=_DETAIL)
    d = dalian.get_book_detail(_ID_SANTI)
    # 重检索(TI 题名)→在 hitlist 里按 catkey 定位到第 3 位→POST VIEW^3
    view_calls = [c for c in calls if c[1] and "VIEW%5E3" in c[1].decode()]
    assert len(view_calls) == 1
    # 重检索用 TI 字段、按短语下发
    search_calls = [c for c in calls if c[1] and "searchdata1=" in c[1].decode()]
    assert search_calls and "srchfield1=TI" in search_calls[0][1].decode()
    assert "searchdata1=%22" in search_calls[0][1].decode()
    assert d["book_id"] == _ID_SANTI
    assert d["title"] == "三体 Ⅲ 死神永生 专著 典藏版 刘慈欣著"
    assert d["author"] == "刘慈欣 (1963-) 著"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2016"
    assert d["isbn"] == "9787229100629"
    assert d["call_number"] == "I247.55/9275-PT"
    assert d["summary"] == ""  # 匿名详情页无内容提要字段
    validate_book_detail(d)


def test_detail_ladder_falls_back_to_bare_title(monkeypatch):
    # 短语题名 0 命中（Ⅲ 等非索引字符）→ 候选梯度退到裸截断题名，再定位并 VIEW^N
    calls = []

    def spy(req, timeout=25):
        calls.append((req.full_url, req.data))
        if req.data is None:
            return _ENTRY
        body = req.data.decode()
        if "VIEW%5E" in body:
            return _DETAIL
        return _EMPTY if "%22" in body else _SEARCH

    monkeypatch.setattr(dalian, "_open", spy)
    d = dalian.get_book_detail(_ID_SANTI)
    bodies = [c[1].decode() for c in calls if c[1] and "searchdata1=" in c[1].decode()]
    assert "%22" in bodies[0]                                   # 首选短语截断题名
    assert bodies[1].startswith("searchdata1=%E4%B8%89%E4%BD%93+")  # 退到裸截断题名
    assert any("VIEW%5E3" in c[1].decode() for c in calls if c[1])
    assert d["isbn"] == "9787229100629"


def test_detail_ladder_skips_rejected_phrase_candidate(monkeypatch):
    # 含罗马数字 Ⅲ 的短语被源站拒答（回 Error message 页）→ 换下一候选，不当中断
    calls = []

    def spy(req, timeout=25):
        calls.append((req.full_url, req.data))
        if req.data is None:
            return _ENTRY
        body = req.data.decode()
        if "VIEW%5E" in body:
            return _DETAIL
        return _ERROR if "%22" in body else _SEARCH

    monkeypatch.setattr(dalian, "_open", spy)
    d = dalian.get_book_detail(_ID_SANTI)
    bodies = [c[1].decode() for c in calls if c[1] and "searchdata1=" in c[1].decode()]
    assert len(bodies) == 2 and "%22" in bodies[0] and "%22" not in bodies[1]
    assert d["title"] == "三体 Ⅲ 死神永生 专著 典藏版 刘慈欣著"
    validate_book_detail(d)


def test_get_holdings_available_on_shelf(monkeypatch):
    _router(monkeypatch, view_resp=_DETAIL)
    hs = dalian.get_holdings(_ID_SANTI, only_available=False)
    assert len(hs) == 1
    h = hs[0]
    assert h["library"] == "普兰店分馆"
    assert h["call_number"] == "I247.55/9275-PT"
    assert h["location"] == "普成人外借"
    assert h["status"] == "在架上"
    assert h["available"] is True
    assert h["due_date"] == ""  # 匿名视图无应还日期
    validate_holdings(hs)
    # 在架上 → only_available=True 也返回
    assert len(dalian.get_holdings(_ID_SANTI, only_available=True)) == 1


def test_get_holdings_located_conservative(monkeypatch):
    _router(monkeypatch, view_resp=_LOCATED)
    hs = dalian.get_holdings(_ID_TENGELI, only_available=False)
    assert len(hs) == 1
    h = hs[0]
    assert h["library"] == "长海分馆"
    assert h["call_number"] == "J3-CHS/3040"
    assert h["location"] == "长海少儿库"
    # 「馆藏于」无明确在架词 → 保守不可借、status 原值照登
    assert h["status"] == "馆藏于"
    assert h["available"] is False
    assert h["due_date"] == ""
    validate_holdings(hs)
    # 不可借 → only_available=True 恒空（数据边界，非故障）
    assert dalian.get_holdings(_ID_TENGELI, only_available=True) == []


def test_get_holdings_item_id_empty_no_return_date_call(monkeypatch):
    # 大连索书号级、无单册条码 → item_id 恒空，绝不触发 get_return_date
    _router(monkeypatch, view_resp=_LOCATED)
    monkeypatch.setattr(dalian._client, "get_return_date",
                        lambda *a, **k: pytest.fail("不应调用 get_return_date"), raising=False)
    hs = dalian.get_holdings(_ID_TENGELI, only_available=False)
    assert all(h["due_date"] == "" for h in hs)


def test_detail_session_rebuild_then_raises(monkeypatch):
    # 检索 POST 恒退回入口页 → _detail_attempt 两次 None → 抛错，4 次请求
    calls = _seq(monkeypatch, [_ENTRY, _ENTRY, _ENTRY, _ENTRY])
    with pytest.raises(RuntimeError, match="大连图书馆"):
        dalian.get_book_detail(_ID_SANTI)
    assert len(calls) == 4


def test_bad_book_id_raises_without_network(monkeypatch):
    monkeypatch.setattr(dalian, "_open", lambda *a, **k: pytest.fail("不应触网"))
    with pytest.raises(RuntimeError, match="book_id"):
        dalian.get_book_detail("badid")


def test_missing_title_raises_without_network(monkeypatch):
    monkeypatch.setattr(dalian, "_open", lambda *a, **k: pytest.fail("不应触网"))
    with pytest.raises(RuntimeError, match="题名"):
        dalian.get_book_detail("3305715:")
