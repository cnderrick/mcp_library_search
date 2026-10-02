"""天津第三源（中新友好，interlib 租户）接入与单成员 holdings 路由。

il_search/il_holdings/il_detail 为模块级名字，测试直接 monkeypatch。
"""
from pathlib import Path

from mcp_library_search.adapters import tianjin

_FIX = Path(__file__).parent / "fixtures" / "tianjin"


def _load(name):
    return (_FIX / name).read_text(encoding="utf-8")


def _mock_aleph(monkeypatch, default="find_tjl01.html"):
    def spy(req, timeout=20):
        return _load(default)

    monkeypatch.setattr(tianjin, "_open", spy)


def _mock_zxyh_search(monkeypatch, result=None, error=None):
    seen = []

    def spy(cfg, keyword, page=1, limit=20):
        seen.append((cfg, keyword, page, limit))
        if error:
            raise error
        return result if result is not None else {
            "books": [{"book_id": "217795", "title": "三体", "author": "刘慈欣",
                       "publisher": "重庆出版社", "publish_year": "2008",
                       "availability_summary": "", "isbn": "978-7-5366-9293-0"}],
            "total_results": None, "total_pages": 3, "has_next": True,
        }

    monkeypatch.setattr(tianjin, "il_search", spy)
    return seen


def test_search_merges_zxyh_source(monkeypatch):
    _mock_aleph(monkeypatch)
    seen = _mock_zxyh_search(monkeypatch)
    r = tianjin._Client().search("三体")
    assert seen[0][0] == tianjin._ZXYH
    assert seen[0][1] == "三体"
    z = [b for b in r.books if b.record_id.startswith("ZXYH:")]
    assert len(z) == 1
    assert z[0].record_id == "ZXYH:217795"
    assert z[0].isbn == "978-7-5366-9293-0"
    assert z[0].title == "三体"
    # ALEPH 两源仍在
    assert any(b.record_id.startswith("TJL01:") for b in r.books)
    assert any(b.record_id.startswith("TJC01:") for b in r.books)


def test_total_results_none_when_any_source_lacks_total(monkeypatch):
    # ZXYH 检索页无「检索到 N 条」→ total_results=None；合计不可知时不编数
    _mock_aleph(monkeypatch)
    _mock_zxyh_search(monkeypatch)
    r = tianjin._Client().search("三体")
    assert r.statistics["total_results"] is None
    assert r.statistics["has_next"] is True


def test_zxyh_search_failure_tolerated(monkeypatch):
    _mock_aleph(monkeypatch)
    _mock_zxyh_search(monkeypatch, error=RuntimeError("中新友好图书馆请求失败：reset"))
    r = tianjin._Client().search("三体")
    assert any(b.record_id.startswith("TJL01:") for b in r.books)
    assert not any(b.record_id.startswith("ZXYH:") for b in r.books)
    # 仅两 ALEPH 源时合计可知（156+TJC01）
    assert isinstance(r.statistics["total_results"], int)


def test_get_holdings_zxyh_routes_to_interlib(monkeypatch):
    seen = []

    def spy(cfg, book_id, only_available=True):
        seen.append((cfg, book_id))
        return [{"library": "中新友好图书馆", "location": "3F 3区",
                 "call_number": "I247.55/107", "status": "借出",
                 "available": False, "due_date": "2024-09-15"}]

    monkeypatch.setattr(tianjin, "il_holdings", spy)
    hs = tianjin._Client().get_holdings("ZXYH:217795")
    assert seen == [(tianjin._ZXYH, "217795")]
    assert isinstance(hs[0], tianjin._Holding)
    assert hs[0].library == "中新友好图书馆"
    assert hs[0].is_available() is False
    assert hs[0].due_date == "2024-09-15"


def test_get_holdings_aleph_fetches_item_global(monkeypatch):
    urls = []

    def spy(req, timeout=20):
        urls.append(req.full_url)
        return _load("item_tjl01.html")

    monkeypatch.setattr(tianjin, "_open", spy)
    hs = tianjin._Client().get_holdings("TJL01:002892667")
    assert "func=item-global" in urls[0]
    assert "doc_library=TJL01" in urls[0] and "doc_number=002892667" in urls[0]
    assert len(hs) == 3
    assert all(h.library for h in hs)
