import json
from pathlib import Path

from mcp_library_search.adapters import shenzhen

_FIXTURES = Path(__file__).parent / "fixtures" / "shenzhen"
_DETAIL = json.loads((_FIXTURES / "detail.json").read_text(encoding="utf-8"))


def test_holdings_buckets_and_due_date(monkeypatch):
    monkeypatch.setattr(shenzhen, "_get", lambda path, params: _DETAIL)
    hs = shenzhen.get_holdings("bibliosm:123", only_available=False)
    assert hs
    for h in hs:
        assert set(h) == {"library", "location", "call_number", "status",
                          "available", "due_date"}
    by_avail = {h["available"] for h in hs}
    # fixture 里既有可借又有借出（Task 1 保证了 BorrowedBook 非空）
    assert True in by_avail and False in by_avail
    borrowed = [h for h in hs if not h["available"]]
    assert any(h["due_date"] for h in borrowed)  # 至少一条借出带应还日期


def test_holdings_available_only_and_sort(monkeypatch):
    monkeypatch.setattr(shenzhen, "_get", lambda path, params: _DETAIL)
    hs = shenzhen.get_holdings("bibliosm:123", only_available=True)
    assert hs and all(h["available"] for h in hs)
    assert [h["library"] for h in hs] == sorted(h["library"] for h in hs)


def test_holdings_parses_book_id_and_calls_detail_once(monkeypatch):
    calls = []
    def spy(path, params):
        calls.append((path, params))
        return _DETAIL
    monkeypatch.setattr(shenzhen, "_get", spy)
    shenzhen.get_holdings("bibliosm:123", only_available=False)
    assert len(calls) == 1
    # client_id 由 _get 内部注入（见 Task 2），get_holdings 不传它
    assert calls[0] == ("/api/opacservice/getBookDetail",
                        {"metaTable": "bibliosm", "metaId": "123",
                         "library": "all"})
