"""杭州双源 ISBN 归并与复合 book_id：跨源同 ISBN 合并、脏 ISBN 提取、
裸 id 兼容路由、成员拆分路由、total 口径、单源失败容错、聚合排序
（用例形态照 test_tianjin_merge.py）。单测不打真网：两源取数函数全部 monkeypatch。
"""
import pytest

from mcp_library_search.adapters import hangzhou


def _b(source, rid, isbn="", title="三体"):
    return hangzhou._Book(record_id=f"{source}:{rid}", title=title, author="刘慈欣",
                          publisher="重庆出版社", publish_year="2008",
                          availability_summary="", isbn=isbn)


# ---- ISBN 归并与复合 id ----

def test_merge_same_isbn_composite_id():
    merged = hangzhou._merge_books(
        {"HZ": [_b("HZ", "2006220724", "9787536692930")],
         "ZJ": [_b("ZJ", "11000002313805", "978-7-5366-9293-0")]})
    assert len(merged) == 1
    assert merged[0].record_id == "HZ:2006220724+ZJ:11000002313805"  # HZ 优先
    # 主记录字段取优先级最高成员的原值
    assert merged[0].title == "三体"
    assert merged[0].isbn == "9787536692930"


def test_merge_zj_only_no_composite():
    merged = hangzhou._merge_books({"ZJ": [_b("ZJ", "B", "9787536692930")]})
    assert len(merged) == 1
    assert merged[0].record_id == "ZJ:B"


def test_merge_dirty_zj_isbn_still_merges():
    # 浙图 identifierIsbn 实抓带脏后缀（tests/fixtures/zjlib/NOTES.md）：提取后仍归并
    merged = hangzhou._merge_books(
        {"HZ": [_b("HZ", "A", "9784152098702")],
         "ZJ": [_b("ZJ", "B", "9784152098702 :")]})
    assert len(merged) == 1
    assert merged[0].record_id == "HZ:A+ZJ:B"


def test_norm_isbn_extraction_and_boundaries():
    assert hangzhou._norm_isbn("978-7-5366-9293-0") == "9787536692930"
    assert hangzhou._norm_isbn("7-117-00998-5") == "7117009985"      # 10 位老 ISBN
    assert hangzhou._norm_isbn("9784152098702 :") == "9784152098702"  # 脏后缀提取
    # 长数字串不得被误切出片段（数字边界断言）
    assert hangzhou._norm_isbn("12345678901234") == ""
    assert hangzhou._norm_isbn("") == ""
    assert hangzhou._norm_isbn("123") == ""


def test_merge_keeps_distinct_isbn_and_no_isbn():
    merged = hangzhou._merge_books(
        {"HZ": [_b("HZ", "A", "9787536692930"), _b("HZ", "D", "")],
         "ZJ": [_b("ZJ", "C", "9787020002207")]})
    assert len(merged) == 3
    ids = {m.record_id for m in merged}
    assert "HZ:A" in ids and "HZ:D" in ids and "ZJ:C" in ids


def test_merge_invalid_isbn_treated_as_no_isbn():
    # 非 ISBN 形态的脏值不参与归并，各自成条
    merged = hangzhou._merge_books(
        {"HZ": [_b("HZ", "A", "123"), _b("HZ", "B", "123")]})
    assert len(merged) == 2


def test_merge_same_isbn_within_source_keeps_first():
    # 源内同 ISBN 多条（多卷/重印）保留首条——浙图实抓「三体世界观」三部曲同 ISBN
    merged = hangzhou._merge_books(
        {"ZJ": [_b("ZJ", "A", "9787534094712", title="三体世界观．时代与文化"),
                _b("ZJ", "B", "9787534094712", title="三体世界观．科幻概念")]})
    assert len(merged) == 1
    assert merged[0].record_id == "ZJ:A"


# ---- book_id 拆分路由与裸 id 兼容 ----

def test_split_composite_routes_members():
    assert hangzhou._split_book_id("HZ:A+ZJ:B") == [("HZ", "A"), ("ZJ", "B")]
    assert hangzhou._split_book_id("ZJ:B+HZ:A") == [("HZ", "A"), ("ZJ", "B")]
    assert hangzhou._split_book_id("ZJ:B") == [("ZJ", "B")]
    assert hangzhou._split_book_id("HZ:A") == [("HZ", "A")]


def test_split_bare_numeric_routes_to_hz():
    # 兼容垫片：0.3.0 已上线的裸数字 book_id 必须继续可用
    assert hangzhou._split_book_id("2007002340") == [("HZ", "2007002340")]
    # 复合 id 里混入裸数字成员同样按 HZ 路由（垫片对成员一致生效）
    assert hangzhou._split_book_id("ZJ:B+1") == [("HZ", "1"), ("ZJ", "B")]


@pytest.mark.parametrize("bad", ["abc", "XX:1", "HZ:", "", "HZ:A+bad"])
def test_split_bad_book_id_raises(bad):
    with pytest.raises(RuntimeError) as ei:
        hangzhou._split_book_id(bad)
    assert "book_id" in str(ei.value)


# ---- 双源检索：合计口径与源级容错 ----

_HZ_PAGE = {"books": [{"book_id": "1", "title": "三体", "author": "刘慈欣",
                       "publisher": "重庆出版社", "publish_year": "2008",
                       "availability_summary": "", "isbn": "9787536692930"}],
            "total_results": 265, "total_pages": 27, "has_next": True}
_ZJ_PAGE = {"books": [{"book_id": "2", "title": "三体", "author": "刘慈欣著",
                       "publisher": "重庆出版社", "publish_year": "2008",
                       "availability_summary": "", "isbn": "978-7-5366-9293-0"}],
            "total_results": 1811, "total_pages": 182, "has_next": True}


def _patch_hz_search(monkeypatch, result=None, error=None):
    def fake(cfg, keyword, page=1, limit=20):
        if error:
            raise RuntimeError(error)
        return result

    monkeypatch.setattr("mcp_library_search.interlib.search_raw", fake)


def _patch_zj_search(monkeypatch, result=None, error=None):
    def fake(keyword, page=1, limit=20):
        if error:
            raise RuntimeError(error)
        return result

    monkeypatch.setattr("mcp_library_search.adapters._zjlib.search", fake)


def test_search_merges_and_sums_totals(monkeypatch):
    _patch_hz_search(monkeypatch, result=_HZ_PAGE)
    _patch_zj_search(monkeypatch, result=_ZJ_PAGE)
    r = hangzhou._Client().search("三体")
    assert r.statistics["total_results"] == 265 + 1811
    assert r.statistics["total_pages"] == 182  # 取存活源最大
    assert r.statistics["has_next"] is True
    assert len(r.books) == 1  # 同 ISBN 跨源归并为复合
    assert r.books[0].record_id == "HZ:1+ZJ:2"
    assert r.books[0].author == "刘慈欣"  # 主记录取 HZ 成员原值


def test_search_total_none_when_any_source_unknown(monkeypatch):
    # 任一存活源无总数 → 合计不可知，如实 None（天津口径）
    _patch_hz_search(monkeypatch, result=_HZ_PAGE)
    _patch_zj_search(monkeypatch, result=dict(_ZJ_PAGE, total_results=None))
    r = hangzhou._Client().search("三体")
    assert r.statistics["total_results"] is None


def test_search_hz_failure_degrades_to_zj(monkeypatch):
    _patch_hz_search(monkeypatch, error="杭州图书馆请求失败：HTTP 500")
    _patch_zj_search(monkeypatch, result=_ZJ_PAGE)
    r = hangzhou._Client().search("三体")
    assert r.statistics["total_results"] == 1811
    assert [b.record_id for b in r.books] == ["ZJ:2"]


def test_search_zj_failure_degrades_to_hz(monkeypatch):
    _patch_hz_search(monkeypatch, result=_HZ_PAGE)
    _patch_zj_search(monkeypatch, error="浙江图书馆请求失败：连接被重置")
    r = hangzhou._Client().search("三体")
    assert r.statistics["total_results"] == 265
    assert [b.record_id for b in r.books] == ["HZ:1"]


def test_search_both_sources_fail_raises_with_both_errors(monkeypatch):
    _patch_hz_search(monkeypatch, error="杭州图书馆请求失败：HTTP 500")
    _patch_zj_search(monkeypatch, error="浙江图书馆请求失败：连接被重置")
    with pytest.raises(RuntimeError) as ei:
        hangzhou._Client().search("三体")
    msg = str(ei.value)
    assert "双源检索均失败" in msg
    assert "杭州图书馆" in msg and "浙江图书馆" in msg  # 汇总两源报错


# ---- 馆藏聚合：成员路由、容错、排序 ----

def _hz_holding(library="杭州图书馆", available=True):
    return {"library": library, "location": "文献借阅中心", "call_number": "I247.5/1",
            "status": "在馆" if available else "借出", "available": available,
            "due_date": "" if available else "2026-10-20"}


def _zj_holding(library="之江馆区", available=True):
    return {"library": library, "location": "之江馆文学借阅区", "call_number": "I247.5/2",
            "status": "在馆" if available else "借出", "available": available,
            "due_date": ""}  # 数据边界：浙图访客视角恒无应还日期


def test_get_holdings_composite_aggregates(monkeypatch):
    seen = []

    def fake_hz(cfg, book_id, only_available=True):
        seen.append(f"hz:{book_id}")
        return [_hz_holding(available=False)]

    def fake_zj(rid):
        seen.append(f"zj:{rid}")
        return [_zj_holding(available=True), _zj_holding("曙光路馆区", available=False)]

    monkeypatch.setattr("mcp_library_search.interlib.get_holdings", fake_hz)
    monkeypatch.setattr("mcp_library_search.adapters._zjlib.get_holdings", fake_zj)
    hs = hangzhou._Client().get_holdings("HZ:2006220724+ZJ:11000002313805")
    assert seen == ["hz:2006220724", "zj:11000002313805"]
    assert len(hs) == 3
    # 可借在前、馆名升序
    assert hs[0].is_available() is True and hs[0].library == "之江馆区"
    rest = [h.library for h in hs[1:]]
    assert rest == sorted(["杭州图书馆", "曙光路馆区"])


def test_get_holdings_bare_id_routes_hz_only(monkeypatch):
    calls = []
    monkeypatch.setattr("mcp_library_search.interlib.get_holdings",
                        lambda cfg, book_id, only_available=True:
                        calls.append(book_id) or [_hz_holding()])
    monkeypatch.setattr("mcp_library_search.adapters._zjlib.get_holdings",
                        lambda rid: calls.append(f"zj:{rid}") or [])
    hs = hangzhou._Client().get_holdings("2007002340")
    assert calls == ["2007002340"]  # 裸 id 只路由 HZ，不触浙图源
    assert len(hs) == 1


def test_get_holdings_secondary_failure_degrades(monkeypatch):
    # 首成员 HZ 成功、附属 ZJ 失败 → 跳过，返回已查到部分（天津口径）
    monkeypatch.setattr("mcp_library_search.interlib.get_holdings",
                        lambda cfg, book_id, only_available=True: [_hz_holding()])

    def boom(rid):
        raise RuntimeError("浙江图书馆请求失败：连接被重置")

    monkeypatch.setattr("mcp_library_search.adapters._zjlib.get_holdings", boom)
    hs = hangzhou._Client().get_holdings("HZ:1+ZJ:2")
    assert len(hs) == 1 and hs[0].library == "杭州图书馆"


def test_get_holdings_primary_failure_raises(monkeypatch):
    def boom(cfg, book_id, only_available=True):
        raise RuntimeError("杭州图书馆请求失败：HTTP 500")

    monkeypatch.setattr("mcp_library_search.interlib.get_holdings", boom)
    monkeypatch.setattr("mcp_library_search.adapters._zjlib.get_holdings",
                        lambda rid: [_zj_holding()])
    with pytest.raises(RuntimeError):
        hangzhou._Client().get_holdings("HZ:1+ZJ:2")


# ---- 详情路由 ----

def test_get_book_detail_composite_takes_hz(monkeypatch):
    monkeypatch.setattr("mcp_library_search.interlib.get_book_detail",
                        lambda cfg, book_id: {"book_id": book_id, "title": "三体",
                                              "author": "刘慈欣", "publisher": "重庆出版社",
                                              "publish_year": "2008", "isbn": "9787536692930",
                                              "call_number": "I247.55", "summary": "hz 简介"})
    monkeypatch.setattr("mcp_library_search.adapters._zjlib.get_work_detail",
                        lambda rid: pytest.fail("复合 id 应路由优先级最高的 HZ 成员"))
    d = hangzhou._Client().get_book_detail("HZ:2006220724+ZJ:11000002313805")
    assert d.record_id == "HZ:2006220724+ZJ:11000002313805"  # 保留查询原样
    assert d.summary == "hz 简介"


def test_get_book_detail_zj_member(monkeypatch):
    monkeypatch.setattr("mcp_library_search.adapters._zjlib.get_work_detail",
                        lambda rid: {"work_id": "w", "title": "三体", "author": "刘慈欣著",
                                     "publisher": "重庆出版社", "publish_year": "2008",
                                     "isbn": "978-7-5366-9293-0", "call_number": "I247.55",
                                     "summary": "“地球往事”三部曲之一"})
    d = hangzhou._Client().get_book_detail("ZJ:11000002313805")
    assert d.author == "刘慈欣著"  # 责任方式后缀原值照登
    assert d.record_id == "ZJ:11000002313805"


def test_get_book_detail_zj_failure_raises(monkeypatch):
    def boom(rid):
        raise RuntimeError("浙江图书馆接口返回异常：code=500, desc=服务器繁忙，请稍后重试")

    monkeypatch.setattr("mcp_library_search.adapters._zjlib.get_work_detail", boom)
    with pytest.raises(RuntimeError) as ei:
        hangzhou._Client().get_book_detail("ZJ:99999999999999")
    assert "服务器繁忙" in str(ei.value)  # 站点 desc 原样穿透
