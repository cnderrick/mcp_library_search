"""南京双源：南图 ALEPH 源接入、跨源 ISBN 归并、复合 book_id 路由与容错。

南图侧 fixture 见 tests/fixtures/nanjing_prov/NOTES.md（ALEPH www_f_chi，家族解析
在 `aleph/`）；金陵侧见 tests/fixtures/nanjing/NOTES.md。
"""
from pathlib import Path

import pytest

from mcp_library_search.adapters import nanjing
from mcp_library_search.aleph import Book, CaptchaError
from mcp_library_search.aleph import client as aleph_client

_JL_FIX = Path(__file__).parent / "fixtures" / "nanjing"
_PROV_FIX = Path(__file__).parent / "fixtures" / "nanjing_prov"


def _jl(name):
    return (_JL_FIX / name).read_text(encoding="utf-8")


def _prov(name):
    return (_PROV_FIX / name).read_text(encoding="utf-8")


def _mock_jl(monkeypatch, text=None, error=None):
    """金陵源：mock 模块级 _open。"""
    def spy(req, timeout=90):
        if error:
            raise error
        return text

    monkeypatch.setattr(nanjing, "_open", spy)


def _mock_prov(monkeypatch, text=None, error=None):
    """南图源：mock 家族 HTTP 入口。"""
    def spy(url, config=None, timeout=20):
        if error:
            raise error
        return text

    monkeypatch.setattr(aleph_client, "get", spy)


def _b(source, rid, isbn="", title="三体", **kw):
    return Book(record_id=f"{source}:{rid}", title=title, isbn=isbn, **kw)


# ---------- book_id 形态与拆分 ----------

def test_split_bare_digit_routes_to_jl():
    # 兼容垫片：0.4.0 已上线的裸数字 id 必须继续可用
    assert nanjing._split_book_id("4386216") == [("JL", "4386216")]


def test_split_prefixed_and_composite():
    assert nanjing._split_book_id("JL:4386216") == [("JL", "4386216")]
    assert nanjing._split_book_id("NJL01:002912577") == [("NJL01", "002912577")]
    # 复合 id 按优先级 JL > NJL01 重排
    assert nanjing._split_book_id("NJL01:002912577+JL:4386216") == [
        ("JL", "4386216"), ("NJL01", "002912577")]
    # 同源多成员（联合目录里同一本书多条编目）原顺序保留
    assert nanjing._split_book_id("JL:1+JL:2+NJL01:9") == [
        ("JL", "1"), ("JL", "2"), ("NJL01", "9")]


def test_split_bad_book_id_raises():
    for bad in ("abc", "XX:1", "JL:", ""):
        with pytest.raises(RuntimeError, match="book_id"):
            nanjing._split_book_id(bad)


# ---------- 跨源归并 ----------

def test_merge_keeps_single_source_duplicates():
    """金陵联合目录同一本书多条编目：原地保留，不被天津口径吞掉。"""
    a, b = _b("JL", "1", "9787536692930", "三体 黑暗森林 2"), _b("JL", "2", "", "无 ISBN 书")
    c = _b("JL", "3", "9787536692930", "三体 II 黑暗森林")
    merged = nanjing._merge_books({"JL": [a, b, c]})
    assert [m.record_id for m in merged] == ["JL:1", "JL:2", "JL:3"]  # 顺序即原相关度顺序


def test_merge_across_sources_makes_composite_id():
    merged = nanjing._merge_books({
        "JL": [_b("JL", "1", "9787020002207"), _b("JL", "2", "9787536692930")],
        "NJL01": [_b("NJL01", "002892667", "978-7-5366-9293-0", "三体（南图编目）")],
    })
    # 带连字符的 978-7-5366-9293-0 与 9787536692930 归一后同键 → 跨源合成一条
    assert [m.record_id for m in merged] == ["JL:1", "JL:2+NJL01:002892667"]
    # 书目字段取优先级最高（同源内最靠前）成员原值
    assert merged[1].title == "三体"


def test_merge_no_isbn_stays_in_place():
    merged = nanjing._merge_books({
        "JL": [_b("JL", "1", "", "无 ISBN 甲"), _b("JL", "2", "9787536692930")],
        "NJL01": [_b("NJL01", "9", "9787536692930")],
    })
    assert [m.record_id for m in merged] == ["JL:1", "JL:2+NJL01:9"]


# ---------- 检索：双源合并与容错 ----------

def test_search_merges_both_sources(monkeypatch):
    _mock_jl(monkeypatch, _jl("uopac_result_santi.html"))
    _mock_prov(monkeypatch, _prov("findb_NJL01.html"))
    page = nanjing.search_books("三体")
    ids = [b["book_id"] for b in page["books"]]
    assert any(i.startswith("JL:") for i in ids)
    assert any(i.startswith("NJL01:") for i in ids)
    # 合计口径：两源都提供总数 → 相加（金陵 59 + 南图 3192）
    assert page["total_results"] == 59 + 3192


def test_search_tolerates_prov_failure(monkeypatch):
    _mock_jl(monkeypatch, _jl("uopac_result_santi.html"))
    _mock_prov(monkeypatch, error=RuntimeError("南京图书馆请求失败：HTTP Error 503"))
    page = nanjing.search_books("三体")
    assert all(b["book_id"].startswith("JL:") for b in page["books"])
    assert page["total_results"] == 59          # 存活源合计仍可知


def test_search_tolerates_jl_failure(monkeypatch):
    _mock_jl(monkeypatch, error=RuntimeError("金陵图书馆请求失败：HTTP Error 503"))
    _mock_prov(monkeypatch, _prov("findb_NJL01.html"))
    page = nanjing.search_books("红楼梦")
    assert all(b["book_id"].startswith("NJL01:") for b in page["books"])


def test_search_both_sources_fail_raises(monkeypatch):
    _mock_jl(monkeypatch, error=RuntimeError("金陵图书馆请求失败：HTTP Error 503"))
    _mock_prov(monkeypatch, error=RuntimeError("南京图书馆请求失败：HTTP Error 503"))
    with pytest.raises(RuntimeError, match="金陵图书馆"):
        nanjing.search_books("三体")


def test_search_captcha_punches_through_source_tolerance(monkeypatch):
    """南图验证码墙（HTTP 401）是全局信号：即使金陵源健康也要上抛提示。"""
    _mock_jl(monkeypatch, _jl("uopac_result_santi.html"))
    _mock_prov(monkeypatch, error=CaptchaError(
        "南京图书馆：IP 被验证码墙封禁（HTTP 401），请在浏览器逐个打开 "
        "https://opac.jslib.org.cn/F/（南京图书馆） 输入验证码手动解封后重试"))
    with pytest.raises(RuntimeError, match="解封"):
        nanjing.search_books("三体")


# ---------- 详情与馆藏路由 ----------

def test_detail_composite_takes_first_member(monkeypatch):
    calls = []

    def spy(req, timeout=90):
        calls.append(req.full_url)
        return _jl("uopac_detail_jl.html")

    monkeypatch.setattr(nanjing, "_open", spy)
    _mock_prov(monkeypatch, error=AssertionError("取首个成员（JL），不该打南图"))
    d = nanjing.get_book_detail("JL:4308867+NJL01:002912577")
    assert d["book_id"] == "JL:4308867+NJL01:002912577"   # 原样回传
    assert "/uopac/s/detail.action?id=4308867" in calls[0]


def test_detail_prov_member_routes_aleph(monkeypatch):
    calls = []

    def spy(url, config=None, timeout=20):
        calls.append((url, config))
        return _prov("detail_full.html")

    monkeypatch.setattr(aleph_client, "get", spy)
    d = nanjing.get_book_detail("NJL01:002912577")
    url, cfg = calls[0]
    assert "find_code=SYS" in url and "request=002912577" in url
    assert cfg is nanjing._PROV
    assert d["title"] == "蔡元培论红楼梦"
    assert d["isbn"] == "978-7-100-24958-4"


def test_holdings_composite_aggregates_both_sources(monkeypatch):
    seen = []

    def jl_spy(req, timeout=90):
        seen.append(req.full_url)
        if "detail.action" in req.full_url:
            return _jl("uopac_detail_jl.html")
        return _jl("uopac_holding_jl.html")

    def prov_spy(url, config=None, timeout=20):
        seen.append(url)
        return _prov("holdings_MCBKL.html")

    monkeypatch.setattr(nanjing, "_open", jl_spy)
    monkeypatch.setattr(aleph_client, "get", prov_spy)
    hs = nanjing.get_holdings("JL:4308867+NJL01:002912577", only_available=False)
    assert any("uopac" in u for u in seen)
    assert any("item-global" in u and "doc_number=002912577" in u for u in seen)
    assert any(h["library"] == "中文图书借阅" for h in hs)      # 南图成员馆


def test_holdings_prov_url_carries_empty_params(monkeypatch):
    """南图 item-global 的 year/volume/sub_library 可留空但不能省略（否则错误页）。"""
    urls = []
    monkeypatch.setattr(nanjing, "_open",
                        lambda req, timeout=90: _jl("uopac_detail_jl.html"))

    def spy(url, config=None, timeout=20):
        urls.append(url)
        return _prov("holdings_MCBKL.html")

    monkeypatch.setattr(aleph_client, "get", spy)
    nanjing.get_holdings("NJL01:002912577", only_available=False)
    assert urls and urls[0].endswith("&year=&volume=&sub_library=")
