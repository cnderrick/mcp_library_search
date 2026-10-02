"""合肥双源解析测试：打 fixture，验证 tests/fixtures/hefei/NOTES.md 的字段侦察结论。

注入点：interlib.client.get（家族 HTTP 层），按 (cfg.city, path) 分发 fixture；
单测严禁打真网。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters.cn import hefei
from mcp_library_search.interlib import client as il_client

_FIX = Path(__file__).parent / "fixtures" / "hefei"

_AH_SEARCH = (_FIX / "ah" / "search_p1.html").read_text(encoding="utf-8")
_AH_DETAIL = (_FIX / "ah" / "detail.html").read_text(encoding="utf-8")
_AH_HOLDING = (_FIX / "ah" / "holding.json").read_text(encoding="utf-8")
_HF_SEARCH = (_FIX / "hf" / "search_p1.html").read_text(encoding="utf-8")
_HF_DETAIL = (_FIX / "hf" / "detail.html").read_text(encoding="utf-8")
_HF_HOLDING = (_FIX / "hf" / "holding.json").read_text(encoding="utf-8")

# 无「检索到 N 条」文本的空页（合成）：total_results=None 形态
_NO_TOTAL_PAGE = "<html><body></body></html>"


def _dispatch(mapping):
    """按 (cfg.city, path) 返回 fixture 文本的假 client.get，附带调用记录。"""
    calls = []

    def fake_get(cfg, path, params=None, timeout=20):
        calls.append((cfg.city, path, params))
        return mapping[(cfg.city, path)]

    return fake_get, calls


# ---- 搜索页 ----


def test_ah_search_parses(monkeypatch):
    fake, calls = _dispatch({("ah", "/opac/search"): _AH_SEARCH})
    monkeypatch.setattr(il_client, "get", fake)
    r = hefei._search_raw(hefei._AH, "三体")
    assert r["total_results"] == 208
    assert r["total_pages"] == 21
    assert r["has_next"] is True
    assert len(r["books"]) == 10
    b = r["books"][0]
    assert b["book_id"] == "1901234449"
    assert b["title"] == "三体：图像小说"
    assert b["author"] == "刘慈欣"
    assert b["isbn"] == "978-7-5753-0280-7"
    # AH 走家族默认上下文 /opac
    assert calls[0][1] == "/opac/search"
    assert calls[0][2]["q"] == "三体"


def test_hf_search_parses_with_lib2_context(monkeypatch):
    fake, calls = _dispatch({("hf", "/lib2/search"): _HF_SEARCH})
    monkeypatch.setattr(il_client, "get", fake)
    r = hefei._search_raw(hefei._HF, "三体")
    assert r["total_results"] == 143
    assert r["total_pages"] == 15
    assert r["has_next"] is True
    assert len(r["books"]) == 10
    b = r["books"][0]
    assert b["book_id"] == "1001460005"
    assert b["title"] == "三体"
    assert b["isbn"] == "978-7-5366-9293-0"
    # HF 上下文路径是 /lib2（NOTES.md 侦察结论，/opac 探测为 nginx 500）
    assert calls[0][1] == "/lib2/search"


def test_search_isbn_hyphen_retry(monkeypatch):
    # 家族同款口径：带连字符 ISBN 首搜为空 → 去连字符重试一次
    responses = [_NO_TOTAL_PAGE, _AH_SEARCH]
    seen_q = []

    def fake_get(cfg, path, params=None, timeout=20):
        seen_q.append(params["q"])
        return responses.pop(0)

    monkeypatch.setattr(il_client, "get", fake_get)
    r = hefei._search_raw(hefei._AH, "978-7-5366-9293-0")
    assert seen_q == ["978-7-5366-9293-0", "9787536692930"]
    assert r["books"]


# ---- 详情页 ----


def test_ah_detail_author_not_clobbered_by_tag_row(monkeypatch):
    # tagTr 行（读者标签）的裸标签单元格曾让家族解析器用残留标签「主要责任者」
    # 把 author 覆盖成「没有标签」；家族已修复（标签一对一消费），本测试是
    # AH 布局上的回归钉子（NOTES.md「tagTr 坑」）。
    fake, _ = _dispatch({("ah", "/opac/book/1901181704"): _AH_DETAIL})
    monkeypatch.setattr(il_client, "get", fake)
    d = hefei._detail_for(hefei._AH, "1901181704")
    assert d["title"] == "三体"
    assert d["author"] == "刘慈欣"
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2008"
    assert d["isbn"] == "978-7-5366-9293-0"
    assert d["call_number"] == "I247.55"
    assert d["summary"] == ""  # 页面无「内容提要」行，原值如实


def test_hf_detail_parses(monkeypatch):
    fake, calls = _dispatch({("hf", "/lib2/book/1001460005"): _HF_DETAIL})
    monkeypatch.setattr(il_client, "get", fake)
    d = hefei._detail_for(hefei._HF, "1001460005")
    assert d["title"] == "三体"
    assert d["author"] == "刘慈欣"
    assert d["isbn"] == "978-7-5366-9293-0"
    # call_number 维持家族口径取「中图分类法」；HF 页内另有真实「索书号」行不特调
    assert d["call_number"] == "I247.55"
    assert calls[0][1] == "/lib2/book/1001460005"


def test_detail_not_found_raises(monkeypatch):
    fake, _ = _dispatch({("ah", "/opac/book/0"): "<html><body></body></html>"})
    monkeypatch.setattr(il_client, "get", fake)
    with pytest.raises(RuntimeError, match="未找到"):
        hefei._detail_for(hefei._AH, "0")


# ---- 馆藏 JSON ----


def test_ah_holdings_parse(monkeypatch):
    fake, calls = _dispatch({("ah", "/opac/api/holding/1901181704"): _AH_HOLDING})
    monkeypatch.setattr(il_client, "get", fake)
    hs = hefei._holdings_for(hefei._AH, "1901181704")
    assert len(hs) == 19
    avail = [h for h in hs if h.available]
    unavail = [h for h in hs if not h.available]
    assert len(avail) == 10 and len(unavail) == 9
    assert all(h.status == "在馆" for h in avail)
    assert all(h.status == "借出" for h in unavail)
    # 借出册应还日期全部归一成功（loanWorkMap epoch 毫秒 → YYYY-MM-DD）
    assert all(h.due_date for h in unavail)
    assert any(h.due_date == "2026-10-10" for h in unavail)
    assert {h.library for h in hs} == {"安徽省馆"}
    assert all(h.call_number for h in hs)
    assert calls[0][1] == "/opac/api/holding/1901181704"


def test_hf_holdings_parse(monkeypatch):
    fake, calls = _dispatch({("hf", "/lib2/api/holding/1001460005"): _HF_HOLDING})
    monkeypatch.setattr(il_client, "get", fake)
    hs = hefei._holdings_for(hefei._HF, "1001460005")
    assert len(hs) == 21
    assert sum(1 for h in hs if h.available) == 2
    # libcodeMap 翻译生效：馆码 HST → 合肥少儿图书馆（本书馆藏全在该馆）
    assert {h.library for h in hs} == {"合肥少儿图书馆"}
    assert all(h.status for h in hs)
    assert all(h.due_date for h in hs if not h.available)
    assert calls[0][1] == "/lib2/api/holding/1001460005"
