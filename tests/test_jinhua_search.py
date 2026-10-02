"""金华适配器检索：POST 表单口径、ISBN 路由、双重编码翻页、空结果页、非结果页报错。

mock 点为模块级 `_open(req, timeout)`：req 是 urllib Request，
测试里按顺序返回 fixture 文本并记录 (full_url, data)。
fixture 结论见 tests/fixtures/jinhua/NOTES.md。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters import jinhua

_FIXTURES = Path(__file__).parent / "fixtures" / "jinhua"
_SEARCH = (_FIXTURES / "search.html").read_text(encoding="utf-8")
_SEARCH_P2 = (_FIXTURES / "search_p2.html").read_text(encoding="utf-8")
_SEARCH_ISBN = (_FIXTURES / "search_isbn.html").read_text(encoding="utf-8")
_SEARCH_EMPTY = (_FIXTURES / "search_empty.html").read_text(encoding="utf-8")


def _mock_open(monkeypatch, pages):
    """按顺序返回 pages；记录 (full_url, data)。"""
    calls = []
    seq = iter(pages)

    def spy(req, timeout=30):
        calls.append((req.full_url, req.data))
        return next(seq)

    monkeypatch.setattr(jinhua, "_open", spy)
    return calls


def test_search_posts_form_defaults(monkeypatch):
    calls = _mock_open(monkeypatch, [_SEARCH])
    page = jinhua.search_books("三体")
    url, data = calls[0]
    assert url.endswith("/ILASOPAC/NTRdrBookRetr.do")
    assert data is not None  # 首页检索走 POST
    body = data.decode()
    assert "searchType=text" in body  # 任意词路由
    assert "searchKey=%E4%B8%89%E4%BD%93" in body
    assert "searchWay=searchWayPrv" in body
    assert "pageNum=20" in body
    assert "matchType=pubyear" in body and "matchSort=desc" in body


def test_search_parses_stats_and_entries(monkeypatch):
    _mock_open(monkeypatch, [_SEARCH])
    page = jinhua.search_books("三体")
    assert page["total_results"] == 665  # 「共有 [665]条记录」
    assert page["page"] == 1
    assert page["total_pages"] == 34  # 「页码: 1/34」
    assert page["has_next"] is True
    assert len(page["books"]) == 20  # 每页 20 条，无重复渲染
    b0 = page["books"][0]
    assert b0["book_id"] == "125479764"  # 裸 recno
    assert b0["title"] == "石经考．汉石经残字考．魏三体石经遗字考"
    assert b0["author"] == "顾炎武,翁方纲,孙星衍撰；顾炎武,翁方纲,孙星衍撰；顾炎武,翁方纲,孙星衍撰；"
    assert b0["publisher"] == "商务印书馆[发行者]"
    # 出版时间「民国二十」无公历年，不做换算猜测
    assert b0["publish_year"] == ""
    # 列表页无状态词
    assert b0["availability_summary"] == ""
    b1 = page["books"][1]
    assert b1["book_id"] == "126657271"
    assert b1["title"] == "我的三体漫画．第一辑．2"
    assert b1["publish_year"] == "2026"


def test_search_limit_passes_pagenum(monkeypatch):
    calls = _mock_open(monkeypatch, [_SEARCH])
    jinhua.search_books("三体", limit=10)
    assert "pageNum=10" in calls[0][1].decode()


def test_isbn_keyword_routes_isbnsrh(monkeypatch):
    calls = _mock_open(monkeypatch, [_SEARCH_ISBN])
    page = jinhua.search_books("978-7-5728-2658-0")
    assert "searchType=isbnsrh" in calls[0][1].decode()
    assert page["total_results"] == 1
    assert page["books"][0]["book_id"] == "126657271"
    assert page["books"][0]["title"] == "我的三体漫画．第一辑．2"
    assert page["has_next"] is False


def test_isbn_compact_form_also_routes(monkeypatch):
    calls = _mock_open(monkeypatch, [_SEARCH_ISBN])
    jinhua.search_books("9787572826580")
    assert "searchType=isbnsrh" in calls[0][1].decode()


def test_page_two_get_with_double_encoded_key(monkeypatch):
    calls = _mock_open(monkeypatch, [_SEARCH_P2])
    page = jinhua.search_books("三体", page=2)
    url, data = calls[0]
    assert data is None  # 翻页走 GET
    assert "nCurrentpage=2" in url
    # 页内翻页链接原样：SearchKey 双重 URL 编码（NOTES.md）
    assert "SearchKey=%25E4%25B8%2589%25E4%25BD%2593" in url
    assert "SearchType=text" in url and "PageNum=20" in url
    assert page["page"] == 2
    assert page["total_pages"] == 34
    assert page["has_next"] is True
    assert page["books"][0]["book_id"] == "126378368"  # 与首页无重叠
    assert page["books"][0]["title"] == "不要回答.红岸"


def test_empty_result_page(monkeypatch):
    _mock_open(monkeypatch, [_SEARCH_EMPTY])
    page = jinhua.search_books("zzz不存在关键词qqq9527")
    assert page["books"] == []
    assert page["total_results"] == 0  # 空结果页锚点是「共有 []条记录」（括号空）
    assert page["total_pages"] == 1  # 「页码: 1/」无总页数
    assert page["has_next"] is False


def test_non_result_page_raises(monkeypatch):
    # 总数锚点整体缺失 ＝ 不是结果页（如被打回首页），报错而不是当空结果
    _mock_open(monkeypatch, ["<html><title>UILAS 知识检索平台</title></html>"])
    with pytest.raises(RuntimeError, match="金华市图书馆"):
        jinhua.search_books("三体")
