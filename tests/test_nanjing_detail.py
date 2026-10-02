"""南京(金陵 uopac 联合目录)适配器详情与馆藏:字段解析、多馆 tab 展开、保守语义。

fixture 结论(NOTES.md):详情页 dl.booklist 字段;每持有馆一个 loca_XX tab,
span#data 是相对 URL,经 /uopac/s/ajax_holding.action 服务端代理成员馆
libsys_view.php,匿名无会话可取(裸请求逐字节同带会话)。状态词表:「可借」→
available=True;「借出-应还日期：X」→ False+due_date;词表外保守 False 原值照登。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters import nanjing
from mcp_library_search.adapters.base import validate_book_detail, validate_holdings

_FIXTURES = Path(__file__).parent / "fixtures" / "nanjing"
_DETAIL_JL = (_FIXTURES / "uopac_detail_jl.html").read_text(encoding="utf-8")
_DETAIL_JL_BARE = (_FIXTURES / "uopac_detail_jl_bare.html").read_text(encoding="utf-8")
_DETAIL_JN = (_FIXTURES / "uopac_detail_santi.html").read_text(encoding="utf-8")
_HOLDING_JL = (_FIXTURES / "uopac_holding_jl.html").read_text(encoding="utf-8")
_HOLDING_JN = (_FIXTURES / "uopac_holding_jn.html").read_text(encoding="utf-8")
_SEARCH_PAGE = (_FIXTURES / "uopac_search.html").read_text(encoding="utf-8")
_LOGIN = (_FIXTURES / "home.html").read_text(encoding="utf-8")

# 合成馆藏表:词表外状态与坏日期形态的保守处理(形状照实抓表格)
_SYNTH_TABLE = """
<table class="table-line">
<tr align="center" bgcolor="#F5F8F9"><td><strong>索书号</strong></td><td><strong>条码号</strong></td><td><strong>年卷期</strong></td><td><strong>校区</strong></td><td><strong>馆藏地</strong></td><td><strong>馆藏书刊状态</strong></td></tr>
<tr align="center" bgcolor="#FFFFFF">
<td width="10%" >I2/1</td><td width="15%" >001</td><td width="15%" ></td>
<td width="10%" >总馆</td><td width="20%" >借阅室</td>
<td width="20%" >借出-应还日期：待定</td></tr>
<tr align="center" bgcolor="#FFFFFF">
<td width="10%" >I2/2</td><td width="15%" >002</td><td width="15%" ></td>
<td width="10%" ></td><td width="20%" >阅览室</td>
<td width="20%" >阅览室内</td></tr>
<tr align="left" bgcolor="#FFFFFF"><td colspan="8" align="center">可借 / 馆藏 (0 / 2)</td></tr>
</table>
"""


def _mock_open(monkeypatch, pages):
    calls = []
    seq = iter(pages)

    def spy(req, timeout=90):
        calls.append(req.full_url)
        return next(seq)

    monkeypatch.setattr(nanjing, "_open", spy)
    return calls


def _mock_open_by_url(monkeypatch, holding_map):
    """按 URL 路由:detail.action → _DETAIL_JL;ajax_holding 按 lib= 码查表。"""
    calls = []

    def spy(req, timeout=90):
        calls.append(req.full_url)
        if "detail.action" in req.full_url:
            return _DETAIL_JL
        for code, resp in holding_map.items():
            if f"lib={code}&" in req.full_url or req.full_url.endswith(f"lib={code}"):
                return resp
        return ""

    monkeypatch.setattr(nanjing, "_open", spy)
    return calls


def test_get_book_detail_fields(monkeypatch):
    calls = _mock_open(monkeypatch, [_DETAIL_JL])
    d = nanjing.get_book_detail("3911408")
    assert calls[0] == "http://uopac.jllib.cn/uopac/s/detail.action?id=3911408"
    assert d["book_id"] == "3911408"
    assert d["title"] == "三体:典藏版"
    assert d["author"] == "刘慈欣著"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2016"
    assert d["isbn"] == "978-7-229-10060-5"
    # 详情页无索书号字段(中图法分类号不冒充索书号,照重庆先例)
    assert d["call_number"] == ""
    assert d["summary"].startswith("国内科学界发生巨大变故")
    validate_book_detail(d)


def test_bare_detail_jsessionid_form(monkeypatch):
    # 裸抓详情页:logo/表单 action 被 jsessionid 重写,但书目字段与 span#data
    # 干净(NOTES.md),解析结果应与带 Cookie 抓取完全一致
    _mock_open(monkeypatch, [_DETAIL_JL_BARE])
    d = nanjing.get_book_detail("3911408")
    assert d["title"] == "三体:典藏版"
    assert d["isbn"] == "978-7-229-10060-5"
    assert d["summary"].startswith("国内科学界发生巨大变故")
    # tab 也能照常展开(裸详情页 9 馆,仅 JL 有响应,其余空)
    _mock_open(monkeypatch, [_DETAIL_JL_BARE, _HOLDING_JL] + [""] * 8)
    hs = nanjing.get_holdings("3911408", only_available=False)
    assert len(hs) == 13
    assert all(h["library"] == "金陵图书馆" for h in hs)


def test_get_holdings_jl_multi_item(monkeypatch):
    # 9 馆 tab,仅 JL 有响应,其余回空串 → 只出金陵 13 册
    calls = _mock_open_by_url(monkeypatch, {"JL": _HOLDING_JL})
    hs = nanjing.get_holdings("3911408", only_available=False)
    # 1 次详情 + 9 次 ajax(每持有馆一次)
    assert sum(1 for u in calls if "detail.action" in u) == 1
    assert sum(1 for u in calls if "ajax_holding.action" in u) == 9
    assert len(hs) == 13
    assert all(h["library"] == "金陵图书馆" for h in hs)
    assert all(h["call_number"] == "I247.5/30762" for h in hs)
    # 校区+馆藏地拼 location
    assert {h["location"] for h in hs} >= {"金图分馆 地铁分馆·新街口",
                                           "金图总馆 图书借阅室",
                                           "金图总馆 阅·荐空间"}
    avail = [h for h in hs if h["available"]]
    assert len(avail) == 2
    assert all(h["status"] == "可借" and h["due_date"] == "" for h in avail)
    loaned = [h for h in hs if not h["available"]]
    assert len(loaned) == 11
    assert all(h["status"].startswith("借出-应还日期：") for h in loaned)
    assert all(len(h["due_date"]) == 10 for h in loaned)
    assert {h["due_date"] for h in loaned} >= {"2026-10-10", "2025-01-30", "2027-09-30"}
    # 可借排前
    assert [h["available"] for h in hs[:2]] == [True, True]
    validate_holdings(hs)


def test_get_holdings_jn_single_tab(monkeypatch):
    _mock_open(monkeypatch, [_DETAIL_JN, _HOLDING_JN])
    hs = nanjing.get_holdings("4308867", only_available=False)
    assert len(hs) == 24
    assert all(h["library"] == "江宁区图书馆" for h in hs)
    assert sum(1 for h in hs if h["available"]) == 22
    loaned = sorted((h for h in hs if not h["available"]),
                    key=lambda h: h["due_date"])
    assert [h["due_date"] for h in loaned] == ["2024-10-13", "2026-09-17"]


def test_only_available_default(monkeypatch):
    _mock_open_by_url(monkeypatch, {"JL": _HOLDING_JL})
    hs = nanjing.get_holdings("3911408")
    assert len(hs) == 2
    assert all(h["available"] and h["status"] == "可借" for h in hs)


def test_unknown_status_conservative(monkeypatch):
    # 词表外状态(阅览室内)与坏日期形态(应还日期：待定):一律 False,due_date 不猜
    _mock_open_by_url(monkeypatch, {"JL": _SYNTH_TABLE})
    hs = nanjing.get_holdings("3911408", only_available=False)
    assert len(hs) == 2
    by_status = {h["status"]: h for h in hs}
    assert by_status["借出-应还日期：待定"]["available"] is False
    assert by_status["借出-应还日期：待定"]["due_date"] == ""
    assert by_status["阅览室内"]["available"] is False
    assert by_status["阅览室内"]["due_date"] == ""
    assert by_status["阅览室内"]["location"] == "阅览室"


def test_tab_proxy_failure_tolerated(monkeypatch):
    # 某馆 ajax 响应不是馆藏表(如登录页外壳)→ 该馆 0 条,不抛错
    _mock_open_by_url(monkeypatch, {"JL": _LOGIN})
    assert nanjing.get_holdings("3911408", only_available=False) == []


def test_detail_without_booklist_raises(monkeypatch):
    # 响应无题名(非详情页)→ 未找到该书详情
    _mock_open(monkeypatch, [_SEARCH_PAGE])
    with pytest.raises(RuntimeError, match="金陵图书馆"):
        nanjing.get_book_detail("3911408")


def test_bad_book_id_raises(monkeypatch):
    calls = _mock_open(monkeypatch, [])
    with pytest.raises(RuntimeError, match="book_id"):
        nanjing.get_book_detail("abc")
    with pytest.raises(RuntimeError, match="book_id"):
        nanjing.get_holdings("12a:34")
    assert calls == []  # 非法 id 不发请求
