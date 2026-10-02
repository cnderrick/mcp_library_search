"""天津 ISBN 归并与复合 book_id：跨源同 ISBN 合并、无 ISBN 并列、成员拆分路由。"""
from pathlib import Path

from mcp_library_search.adapters import tianjin

_FIX = Path(__file__).parent / "fixtures" / "tianjin"


def _b(source, rid, isbn="", title="三体"):
    return tianjin._Book(record_id=f"{source}:{rid}", title=title, author="刘慈欣",
                         publisher="重庆出版社", publish_year="2022",
                         availability_summary="", isbn=isbn)


def test_merge_same_isbn_composite_id():
    merged = tianjin._merge_books(
        {"TJL01": [_b("TJL01", "A", "9787536692930")],
         "TJC01": [_b("TJC01", "B", "978-7-5366-9293-0")],
         "ZXYH": [_b("ZXYH", "C", "9787536692930")]})
    assert len(merged) == 1
    assert merged[0].record_id == "TJL01:A+TJC01:B+ZXYH:C"  # 主馆优先
    # 主记录字段取优先级最高的成员
    assert merged[0].title == "三体"


def test_merge_priority_without_tjl01():
    merged = tianjin._merge_books(
        {"TJC01": [_b("TJC01", "B", "9787536692930")],
         "ZXYH": [_b("ZXYH", "C", "9787536692930")]})
    assert len(merged) == 1
    assert merged[0].record_id == "TJC01:B+ZXYH:C"


def test_merge_keeps_distinct_isbn_and_no_isbn():
    merged = tianjin._merge_books(
        {"TJL01": [_b("TJL01", "A", "9787536692930"), _b("TJL01", "D", "")],
         "ZXYH": [_b("ZXYH", "C", "9787020002207")]})
    assert len(merged) == 3
    ids = {m.record_id for m in merged}
    assert "TJL01:A" in ids and "TJL01:D" in ids and "ZXYH:C" in ids


def test_merge_invalid_isbn_treated_as_no_isbn():
    # 非 ISBN 形态的脏值不参与归并，各自成条
    merged = tianjin._merge_books(
        {"TJL01": [_b("TJL01", "A", "123"), _b("TJL01", "B", "123")]})
    assert len(merged) == 2


def test_split_composite_routes_members():
    assert tianjin._split_book_id("TJL01:A+TJC01:B") == [("TJL01", "A"), ("TJC01", "B")]
    assert tianjin._split_book_id("ZXYH:C+TJL01:A") == [("TJL01", "A"), ("ZXYH", "C")]
    assert tianjin._split_book_id("TJC01:B") == [("TJC01", "B")]


def test_split_bad_book_id_raises():
    try:
        tianjin._split_book_id("002892667")
        raise AssertionError("无源前缀应报错")
    except RuntimeError as e:
        assert "book_id" in str(e)


def test_get_holdings_composite_aggregates(monkeypatch):
    seen = []
    item_html = (_FIX / "item_tjl01.html").read_text(encoding="utf-8")

    def fake_open(req, timeout=20):
        seen.append(req.full_url)
        return item_html

    def fake_il(cfg, book_id, only_available=True):
        seen.append(f"il:{book_id}")
        return [{"library": "中新友好图书馆", "location": "3F 3区",
                 "call_number": "I247.55/107", "status": "借出",
                 "available": False, "due_date": "2024-09-15"}]

    monkeypatch.setattr(tianjin, "_open", fake_open)
    monkeypatch.setattr(tianjin, "il_holdings", fake_il)
    hs = tianjin._Client().get_holdings("TJL01:002892667+ZXYH:217795")
    assert "il:217795" in seen
    assert any("doc_library=TJL01" in u for u in seen if isinstance(u, str))
    # ALEPH 3 册（在架，可借）+ ZXYH 1 条（借出）→ 可借在前
    assert len(hs) == 4
    assert hs[0].is_available() is True
    assert hs[-1].library == "中新友好图书馆"
