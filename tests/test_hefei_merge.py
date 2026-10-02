"""合肥 ISBN 归并、复合 book_id 与源级容错：口径照天津（参考 test_tianjin_merge.py）。

合并/容错测试打两源 fixture 或合成失败，单测严禁打真网。
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


def _b(prefix, rid, isbn="", title="三体"):
    return hefei._Book(record_id=f"{prefix}:{rid}", title=title, author="刘慈欣",
                       publisher="重庆出版社", publish_year="2008",
                       availability_summary="", isbn=isbn)


def _dispatch(mapping):
    calls = []

    def fake_get(cfg, path, params=None, timeout=20):
        calls.append((cfg.city, path, params))
        return mapping[(cfg.city, path)]

    return fake_get, calls


# ---- ISBN 归并与复合 book_id ----


def test_merge_same_isbn_composite_id():
    merged = hefei._merge_books(
        {"AH": [_b("AH", "1901181704", "978-7-5366-9293-0")],
         "HF": [_b("HF", "1001460005", "9787536692930")]})
    assert len(merged) == 1
    assert merged[0].record_id == "AH:1901181704+HF:1001460005"  # 省馆优先
    # 书目字段取最高优先级成员原值
    assert merged[0].title == "三体"
    assert merged[0].author == "刘慈欣"


def test_merge_member_order_follows_priority_not_input_order():
    merged = hefei._merge_books(
        {"HF": [_b("HF", "1", "9787536692930")],
         "AH": [_b("AH", "2", "978-7-5366-9293-0")]})
    assert len(merged) == 1
    assert merged[0].record_id == "AH:2+HF:1"


def test_merge_dirty_isbn_and_no_isbn_stay_single():
    # 非 ISBN 形态脏值与无 ISBN 不参与归并，各自成条（含跨源同脏值也不合并）
    merged = hefei._merge_books(
        {"AH": [_b("AH", "A", "123"), _b("AH", "B", ""), _b("AH", "C", "9787536692930")],
         "HF": [_b("HF", "D", "123")]})
    assert len(merged) == 4
    assert {m.record_id for m in merged} == {"AH:A", "AH:B", "AH:C", "HF:D"}


def test_merge_source_internal_dup_keeps_first():
    # fixture 证据：AH 搜索页 978-7-5366-9293-0 出现两次（1901181704/1901137700）
    merged = hefei._merge_books(
        {"AH": [_b("AH", "1901181704", "978-7-5366-9293-0"),
                _b("AH", "1901137700", "978-7-5366-9293-0", title="三体（副本）")],
         "HF": [_b("HF", "1001460005", "978-7-5366-9293-0")]})
    assert len(merged) == 1
    assert merged[0].record_id == "AH:1901181704+HF:1001460005"


def test_split_book_id():
    assert hefei._split_book_id("AH:1+HF:2") == [("AH", "1"), ("HF", "2")]
    # 输入顺序无关，输出按优先级排序
    assert hefei._split_book_id("HF:2+AH:1") == [("AH", "1"), ("HF", "2")]
    assert hefei._split_book_id("HF:2") == [("HF", "2")]
    assert hefei._split_book_id("AH:1") == [("AH", "1")]


def test_split_bad_book_id_raises():
    with pytest.raises(RuntimeError, match="book_id"):
        hefei._split_book_id("1901181704")  # 无源前缀
    with pytest.raises(RuntimeError, match="book_id"):
        hefei._split_book_id("TJL01:1")  # 外城前缀不识别


# ---- _Client.search：双源合并、total 口径、源级容错 ----


def test_client_search_merges_fixtures(monkeypatch):
    fake, calls = _dispatch({("ah", "/opac/search"): _AH_SEARCH,
                             ("hf", "/lib2/search"): _HF_SEARCH})
    monkeypatch.setattr(il_client, "get", fake)
    r = hefei._Client().search("三体")
    assert r.success is True
    assert r.statistics["total_results"] == 208 + 143  # 存活源之和
    assert r.statistics["total_pages"] == 21           # 各源最大值
    assert r.statistics["has_next"] is True
    assert r.statistics["page"] == 1
    ids = {b.record_id for b in r.books}
    # 跨源同 ISBN → 复合 id（三体 fixture 有两组交集，AH 在前）
    assert "AH:1901181704+HF:1001460005" in ids        # 978-7-5366-9293-0
    assert "AH:1900823256+HF:1001515793" in ids        # 978-7-229-15100-3
    # 源内同 ISBN 重复保留首条：次条不再单独出现
    assert "AH:1901137700" not in ids
    assert "HF:1001613715" not in ids
    # AH 唯一 ISBN 8 + HF 唯一 ISBN 7 − 交集 2 ＝ 13 条
    assert len(r.books) == 13
    # 两源各打一次各自的上下文路径
    assert {(c[0], c[1]) for c in calls} == {("ah", "/opac/search"),
                                             ("hf", "/lib2/search")}


def test_client_search_total_none_when_source_lacks_total(monkeypatch):
    # 任一存活源无总数（页面缺「检索到 N 条」）→ 合计如实 None，不编造
    fake, _ = _dispatch({("ah", "/opac/search"): _AH_SEARCH,
                         ("hf", "/lib2/search"): "<html><body></body></html>"})
    monkeypatch.setattr(il_client, "get", fake)
    r = hefei._Client().search("三体")
    assert r.success is True
    assert r.statistics["total_results"] is None
    assert r.books and all(b.record_id.startswith("AH:") for b in r.books)


def test_client_search_survives_one_source_failure(monkeypatch):
    # 源级容错：HF 全挂仍返回 AH 结果（≥1 源存活即返回，数据原样）
    def fake_get(cfg, path, params=None, timeout=20):
        if cfg.city == "hf":
            raise RuntimeError("合肥市图书馆请求失败：timed out")
        return _AH_SEARCH

    monkeypatch.setattr(il_client, "get", fake_get)
    r = hefei._Client().search("三体")
    assert r.success is True
    assert r.statistics["total_results"] == 208  # 存活源之和
    assert r.books and all(b.record_id.startswith("AH:") for b in r.books)


def test_client_search_both_sources_fail_raises(monkeypatch):
    def fake_get(cfg, path, params=None, timeout=20):
        raise RuntimeError(f"{cfg.name_cn}请求失败：connection reset")

    monkeypatch.setattr(il_client, "get", fake_get)
    with pytest.raises(RuntimeError) as ei:
        hefei._Client().search("三体")
    msg = str(ei.value)
    # 汇总报错：城市名 + 两源各自错误
    assert "合肥" in msg
    assert "安徽省图书馆" in msg and "合肥市图书馆" in msg


# ---- _Client.get_holdings：成员路由聚合与容错 ----


def test_client_holdings_composite_aggregates_and_sorts(monkeypatch):
    fake, calls = _dispatch({
        ("ah", "/opac/api/holding/1901181704"): _AH_HOLDING,
        ("hf", "/lib2/api/holding/1001460005"): _HF_HOLDING,
    })
    monkeypatch.setattr(il_client, "get", fake)
    hs = hefei._Client().get_holdings("AH:1901181704+HF:1001460005")
    assert len(hs) == 19 + 21
    # 可借在前，同块内馆名升序
    flags = [h.available for h in hs]
    assert flags == sorted(flags, reverse=True)
    for block in (True, False):
        libs = [h.library for h in hs if h.available is block]
        assert libs == sorted(libs)
    # 按成员拆分路由：两源各自的馆藏端点都被打到
    assert {(c[0], c[1]) for c in calls} == {
        ("ah", "/opac/api/holding/1901181704"),
        ("hf", "/lib2/api/holding/1001460005"),
    }


def test_client_holdings_attached_source_failure_skipped(monkeypatch):
    # 附属源（HF）失败跳过，返回已查到部分
    def fake_get(cfg, path, params=None, timeout=20):
        if cfg.city == "hf":
            raise RuntimeError("合肥市图书馆请求失败：reset")
        return _AH_HOLDING

    monkeypatch.setattr(il_client, "get", fake_get)
    hs = hefei._Client().get_holdings("AH:1901181704+HF:1001460005")
    assert len(hs) == 19


def test_client_holdings_primary_source_failure_raises(monkeypatch):
    # 首成员（目标源 AH）失败如实报错，不静默降级
    def fake_get(cfg, path, params=None, timeout=20):
        if cfg.city == "ah":
            raise RuntimeError("安徽省图书馆请求失败：reset")
        return _HF_HOLDING

    monkeypatch.setattr(il_client, "get", fake_get)
    with pytest.raises(RuntimeError, match="安徽省图书馆"):
        hefei._Client().get_holdings("AH:1901181704+HF:1001460005")


# ---- _Client.get_book_detail：优先级成员路由 ----


def test_client_detail_composite_uses_priority_member(monkeypatch):
    fake, calls = _dispatch({
        ("ah", "/opac/book/1901181704"): _AH_DETAIL,
        ("hf", "/lib2/book/1001460005"): _HF_DETAIL,
    })
    monkeypatch.setattr(il_client, "get", fake)
    b = hefei._Client().get_book_detail("AH:1901181704+HF:1001460005")
    # 只查最高优先级成员（AH），record_id 保留查询原样
    assert [c[1] for c in calls] == ["/opac/book/1901181704"]
    assert b.record_id == "AH:1901181704+HF:1001460005"
    assert b.title == "三体"
    assert b.author == "刘慈欣"  # 家族 tagTr 修复生效，未被「没有标签」覆盖
    assert b.isbn == "978-7-5366-9293-0"
    assert b.call_number == "I247.55"


def test_client_detail_hf_member_routed(monkeypatch):
    fake, calls = _dispatch({("hf", "/lib2/book/1001460005"): _HF_DETAIL})
    monkeypatch.setattr(il_client, "get", fake)
    b = hefei._Client().get_book_detail("HF:1001460005")
    assert b.record_id == "HF:1001460005"
    assert b.author == "刘慈欣"
    assert calls[0][1] == "/lib2/book/1001460005"
