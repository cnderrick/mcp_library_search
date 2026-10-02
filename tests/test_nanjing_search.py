"""南京适配器检索：JL 源(金陵 uopac 联合目录)的 meta 路由、ISBN 通配、解析与分页。

mock 点为 uopac 家族 HTTP 入口 `client.get(url, cfg)`：测试按顺序返回 fixture
文本并记录 url（金陵无会话、全 GET，无 POST body）。
南图 ALEPH 源由 `_stub_prov` 置为失败——本文件只测金陵侧,源级容错会吞掉它。
fixture 结论以 tests/fixtures/nanjing/NOTES.md 为准。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters import nanjing
from mcp_library_search.adapters.base import validate_search_page
from mcp_library_search.aleph import client as aleph_client
from mcp_library_search.uopac import UopacConfig
from mcp_library_search.uopac import client as uopac_client

_FIXTURES = Path(__file__).parent / "fixtures" / "nanjing"
_RESULT = (_FIXTURES / "uopac_result_santi.html").read_text(encoding="utf-8")
_RESULT_BARE = (_FIXTURES / "uopac_result_santi_bare.html").read_text(encoding="utf-8")
_RESULT_P2 = (_FIXTURES / "uopac_result_santi_p2.html").read_text(encoding="utf-8")
_RESULT_JL = (_FIXTURES / "uopac_result_santi_jl.html").read_text(encoding="utf-8")
_RESULT_EMPTY = (_FIXTURES / "uopac_result_empty.html").read_text(encoding="utf-8")
_RESULT_ISBN = (_FIXTURES / "uopac_result_isbn_wildcard.html").read_text(encoding="utf-8")
_LOGIN = (_FIXTURES / "home.html").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _stub_prov(monkeypatch):
    """南图 ALEPH 源置为失败：单源断言不被第二源污染，且绝不真网。"""
    def boom(url, config=None, timeout=20):
        raise RuntimeError("南京图书馆请求失败：stub")

    monkeypatch.setattr(aleph_client, "get", boom)


def _mock_open(monkeypatch, pages):
    """按顺序返回 pages;记录 url 列表。"""
    calls = []
    seq = iter(pages)

    def spy(url, cfg):
        calls.append(url)
        return next(seq)

    monkeypatch.setattr(uopac_client, "get", spy)
    return calls


def test_search_parses_list_and_stats(monkeypatch):
    calls = _mock_open(monkeypatch, [_RESULT])
    page = nanjing.search_books("三体")
    # URL 形态:search_result.action + meta=20(任意)+ page=1
    assert "/uopac/s/search_result.action?" in calls[0]
    assert "meta=20" in calls[0]
    assert "q=%E4%B8%89%E4%BD%93" in calls[0]
    assert "page=1" in calls[0]
    # 真实总数与分页(源站给总数,与重庆不同)
    assert page["total_results"] == 59
    assert page["page"] == 1
    assert page["total_pages"] == 3
    assert page["has_next"] is True
    assert len(page["books"]) == 20
    # 首条:元信息行「汪家訸编著 / 科学出版社  /  / 1961」,ISBN 段为空
    b0 = page["books"][0]
    assert b0["book_id"] == "JL:4386216"
    assert b0["title"] == "三体问题"
    assert b0["author"] == "汪家訸编著"
    assert b0["publisher"] == "科学出版社"
    assert b0["publish_year"] == "1961"
    assert b0["availability_summary"] == "所在馆：金陵图书馆"
    # 委托转换后的结构对齐 base.py(含非空 books 的 book_id 映射)
    validate_search_page(page)
    assert set(b0) == {"book_id", "title", "author", "publisher",
                       "publish_year", "availability_summary"}
    assert all(isinstance(b["book_id"], str) and b["book_id"] for b in page["books"])


def test_entry_publisher_and_year_variants(monkeypatch):
    # 第 4 条《三体》:「刘慈欣著 / 重庆出版社  / 9787229100605 / 2015.6」
    _mock_open(monkeypatch, [_RESULT])
    page = nanjing.search_books("三体")
    b3 = page["books"][3]
    assert b3["book_id"] == "JL:4308867"
    assert b3["title"] == "三体"
    assert b3["author"] == "刘慈欣著"
    assert b3["publisher"] == "重庆出版社"
    assert b3["publish_year"] == "2015"  # 「2015.6」取 4 位年份
    assert b3["availability_summary"] == "所在馆：江宁区图书馆"


def test_isbn_keyword_uses_wildcard_meta14(monkeypatch):
    # ISBN 索引按存储原样前缀匹配且各馆存储形态不一 → 数字间插 * 通配(NOTES.md)
    calls = _mock_open(monkeypatch, [_RESULT_ISBN])
    page = nanjing.search_books("9787229100605")
    assert "meta=14" in calls[0]
    assert "q=9%2A7%2A8%2A7%2A2%2A2%2A9%2A1%2A0%2A0%2A6%2A0%2A5" in calls[0]
    assert page["total_results"] == 2
    ids = {b["book_id"] for b in page["books"]}
    assert ids == {"JL:3911408", "JL:4308867"}
    titles = {b["title"] for b in page["books"]}
    assert titles == {"三体 典藏版", "三体"}


def test_hyphenated_isbn_normalized_to_same_wildcard(monkeypatch):
    calls = _mock_open(monkeypatch, [_RESULT_ISBN])
    nanjing.search_books("978-7-229-10060-5")
    assert "meta=14" in calls[0]
    assert "q=9%2A7%2A8%2A7%2A2%2A2%2A9%2A1%2A0%2A0%2A6%2A0%2A5" in calls[0]


def test_page_two_param_and_parse(monkeypatch):
    calls = _mock_open(monkeypatch, [_RESULT_P2])
    page = nanjing.search_books("三体", page=2)
    assert "page=2" in calls[0]
    assert page["page"] == 2
    assert page["total_pages"] == 3
    assert page["has_next"] is True
    assert page["books"][0]["book_id"] == "JL:3369405"
    # 「俞建华等 /   /  / 19870901」:出版年为 YYYYMMDD 形态,取 4 位年
    assert page["books"][0]["publish_year"] == "1987"
    assert page["books"][0]["publisher"] == ""


def test_empty_result(monkeypatch):
    _mock_open(monkeypatch, [_RESULT_EMPTY])
    page = nanjing.search_books("9787229100605")
    assert page["total_results"] == 0
    assert page["books"] == []
    # 空结果页无 num 分页区 → 回退 ceil(0/20)=0
    assert page["total_pages"] == 0
    assert page["has_next"] is False
    validate_search_page(page)


def test_multi_library_availability_summary(monkeypatch):
    # JL 分面 fixture:《三体X·观想之宙 典藏版》栖霞区图书馆+金陵图书馆两馆持有
    _mock_open(monkeypatch, [_RESULT_JL])
    page = nanjing.search_books("三体")
    assert page["total_results"] == 23
    assert page["total_pages"] == 2
    entry = next(b for b in page["books"] if b["book_id"] == "JL:5079421")
    assert entry["title"] == "三体X·观想之宙 典藏版"
    assert entry["availability_summary"] == "所在馆：栖霞区图书馆、金陵图书馆"


def test_bare_response_jsessionid_urls(monkeypatch):
    # 裸抓取形态:条目链接被 Tomcat 重写为 detail.action;jsessionid=…?id=
    # (NOTES.md「jsessionid URL 重写」;首版正则在真网冒烟栽在这里)
    assert "jsessionid" in _RESULT_BARE
    _mock_open(monkeypatch, [_RESULT_BARE])
    page = nanjing.search_books("三体")
    assert page["total_results"] == 59
    assert len(page["books"]) == 20
    assert page["books"][0]["book_id"] == "JL:4386216"
    assert page["books"][0]["title"] == "三体问题"
    assert page["books"][0]["availability_summary"] == "所在馆：金陵图书馆"
    validate_search_page(page)


def test_non_result_page_raises(monkeypatch):
    # 响应不是结果页(如登录页外壳)→ 抛含馆名的 RuntimeError,不静默当空结果
    _mock_open(monkeypatch, [_LOGIN])
    with pytest.raises(RuntimeError, match="金陵图书馆"):
        nanjing.search_books("三体")


def test_module_shape(monkeypatch):
    # 独立实现范式:模块级 _client(契约形态硬要求,别破坏);
    # 金陵侧解析已家族化——委托 uopac 家族,由该家族的无状态 HTTP 入口取数
    assert hasattr(nanjing, "_client")
    for meth in ("search", "get_holdings", "get_book_detail"):
        assert callable(getattr(nanjing._client, meth))
    assert isinstance(nanjing._JL, UopacConfig)
    assert nanjing._JL.securitycam == ""   # 金陵匿名全通,不带 cookie
