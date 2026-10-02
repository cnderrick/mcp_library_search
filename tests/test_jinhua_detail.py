"""金华适配器详情与馆藏：书目字段、附注提要、两表馆藏、入藏/借出状态与数据边界。

fixture 结论（NOTES.md）：详情页标记「书目详细信息」；馆藏内联在 div#BookHolding
（CADAL 的两个 table.table 在其之前，锚点切片天然排除）；状态词表仅
「入藏（可借）/借出」，词表外保守不可借；借出无应还日期列 → due_date 恒空，不猜。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters import jinhua

_FIXTURES = Path(__file__).parent / "fixtures" / "jinhua"
_DETAIL = (_FIXTURES / "detail.html").read_text(encoding="utf-8")
_DETAIL_LOAN = (_FIXTURES / "detail_loan.html").read_text(encoding="utf-8")
_SEARCH = (_FIXTURES / "search.html").read_text(encoding="utf-8")


def _mock_open(monkeypatch, pages):
    calls = []
    seq = iter(pages)

    def spy(req, timeout=30):
        calls.append((req.full_url, req.data))
        return next(seq)

    monkeypatch.setattr(jinhua, "_open", spy)
    return calls


def test_get_book_detail_fields(monkeypatch):
    calls = _mock_open(monkeypatch, [_DETAIL])
    d = jinhua.get_book_detail("125479764")
    assert "NTRdrBookRetrInfo.do?recno=125479764&libid=" in calls[0][0]
    assert calls[0][1] is None  # 详情走 GET，匿名无会话
    assert d["book_id"] == "125479764"
    # 详情页标题短于列表页，原值照登不对齐（NOTES.md）
    assert d["title"] == "石经考"
    assert d["author"] == "顾炎武,翁方纲,孙星衍撰；顾炎武,翁方纲,孙星衍撰；顾炎武,翁方纲,孙星衍撰；"
    assert d["publisher"] == "商务印书馆[发行者]"
    # 出版日期「民国二十五年十二月[1936.12]」提取公历年
    assert d["publish_year"] == "1936"
    # ISBN 原值「书号不详」照登
    assert d["isbn"] == "书号不详"
    assert d["call_number"] == "Z121.6"
    # 简介＝内联「附注提要」原值（与调研「简介恒空」不符，见 NOTES.md 出入清单）
    assert d["summary"] == ("石经考一卷,据借月仙房汇钞本影印 汉石经残字考一卷,"
                            "据知不足斋丛书本影印 魏三体石经遗字考一卷,据平津馆丛书本影印")


def test_get_book_detail_modern_fields(monkeypatch):
    _mock_open(monkeypatch, [_DETAIL_LOAN])
    d = jinhua.get_book_detail("126174120")
    assert d["title"] == "三体：图像小说"
    assert d["author"] == "刘慈欣原著；吴青松，三体宇宙编绘；"
    assert d["publisher"] == "译林出版社"
    assert d["publish_year"] == "2025"
    assert d["isbn"] == "978-7-5753-0280-7"
    assert d["call_number"] == "I247.5"
    assert d["summary"] == "Three-body problem"


def test_get_holdings_single_available_copy(monkeypatch):
    _mock_open(monkeypatch, [_DETAIL])
    hs = jinhua.get_holdings("125479764", only_available=False)
    assert len(hs) == 1
    h = hs[0]
    assert h["library"] == "金华市图书馆"
    assert h["location"] == "民国古书"
    assert h["call_number"] == "Z121.6/7191"
    assert h["status"] == "入藏" and h["available"] is True
    assert h["due_date"] == ""


def test_get_holdings_two_tables_two_states(monkeypatch):
    # 有借出复本的书：BookHolding 内两张表（馆藏信息＋已外借馆藏），合并且可借排前
    _mock_open(monkeypatch, [_DETAIL_LOAN])
    hs = jinhua.get_holdings("126174120", only_available=False)
    assert len(hs) == 2
    assert hs[0]["status"] == "入藏" and hs[0]["available"] is True
    assert hs[0]["location"] == "江南街道悦读吧"
    assert hs[1]["status"] == "借出" and hs[1]["available"] is False
    assert hs[1]["location"] == "市馆外借部"
    assert all(h["library"] == "金华市图书馆" for h in hs)
    assert all(h["call_number"] == "I247.5/0287" for h in hs)
    # 数据边界：借出单册无应还日期列，due_date 恒空，不猜
    assert all(h["due_date"] == "" for h in hs)


def test_get_holdings_only_available_filters(monkeypatch):
    _mock_open(monkeypatch, [_DETAIL_LOAN])
    hs = jinhua.get_holdings("126174120")  # 默认 only_available=True
    assert len(hs) == 1
    assert hs[0]["status"] == "入藏"


def test_get_holdings_single_request(monkeypatch):
    # 内联解析：一次详情页请求即得馆藏，不走备用 GetholdingShow.do、不建会话
    calls = _mock_open(monkeypatch, [_DETAIL_LOAN])
    jinhua.get_holdings("126174120", only_available=False)
    assert len(calls) == 1


def test_non_detail_page_raises(monkeypatch):
    # 检索结果页无「书目详细信息」标记 → 详情获取失败报错
    _mock_open(monkeypatch, [_SEARCH])
    with pytest.raises(RuntimeError, match="金华市图书馆"):
        jinhua.get_book_detail("125479764")


def test_bad_book_id_raises(monkeypatch):
    # book_id 必须是裸 recno（纯数字），带前缀/非数字直接报错
    with pytest.raises(RuntimeError, match="book_id"):
        jinhua.get_book_detail("i_biblios:125479764")
    with pytest.raises(RuntimeError, match="book_id"):
        jinhua.get_holdings("abc")
