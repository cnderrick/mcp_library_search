"""天津 ALEPH 检索解析：brief 列表、ISB 单命中完整记录页、同会话 short-jump 翻页。

mock 点为模块级 `_open(req, timeout)`；fixture 结论见 tests/fixtures/tianjin/NOTES.md。
"""
from pathlib import Path

from mcp_library_search.adapters import tianjin

_FIX = Path(__file__).parent / "fixtures" / "tianjin"


def _load(name):
    return (_FIX / name).read_text(encoding="utf-8")


def _mock_open(monkeypatch, by_url=None, default=None):
    """by_url: [(子串, fixture 名)] 按序匹配；default 兜底。返回记录的 URL 列表。"""
    urls = []

    def spy(req, timeout=20):
        url = req.full_url
        urls.append(url)
        if by_url:
            for frag, name in by_url:
                if frag in url:
                    return _load(name)
        return _load(default)

    monkeypatch.setattr(tianjin, "_open", spy)
    return urls


def test_parse_brief_list_tjl01(monkeypatch):
    urls = _mock_open(monkeypatch, default="find_tjl01.html")
    r = tianjin._Client().search("三体")
    assert r.statistics["total_results"] > 0
    b0 = r.books[0]
    assert b0.record_id.startswith("TJL01:")
    assert b0.title
    assert urls and "find-b" in urls[0] and "local_base=TJL01" in urls[0]


def test_brief_entry_fields(monkeypatch):
    _mock_open(monkeypatch, default="find_tjl01.html")
    r = tianjin._Client().search("三体")
    b0 = r.books[0]
    # fixture 首条：DOC-NUMBER 002892667，ISBN 978-7-5730-2384-1
    assert b0.record_id == "TJL01:002892667"
    assert b0.isbn == "978-7-5730-2384-1"
    assert b0.publisher == "海南出版社"
    assert b0.publish_year == "2025"
    assert "宇宙是巧合吗" in b0.title
    # 每页固定 10 条，重复 publish section 需去重
    tj = [b for b in r.books if b.record_id.startswith("TJL01:")]
    assert len(tj) == 10
    assert len({b.record_id for b in tj}) == 10


def test_isbn_keyword_uses_isb_index(monkeypatch):
    urls = _mock_open(monkeypatch, default="find_tjc01.html")
    tianjin._Client().search("9787221179975")
    assert "find_code=ISB" in urls[0]


def test_isbn_single_hit_full_record_page(monkeypatch):
    # ISB 单命中直接返回完整记录页（非 brief 列表），也要解析成 1 条
    _mock_open(monkeypatch, default="find_tjl01_isbn.html")
    r = tianjin._Client().search("9787536692930")
    tj = [b for b in r.books if b.record_id.startswith("TJL01:")]
    assert len(tj) == 1
    assert tj[0].record_id == "TJL01:000856840"
    assert tj[0].title == "三体"
    assert tj[0].isbn == "978-7-5366-9293-0"
    assert tj[0].call_number == "I247.55/235"
    assert r.statistics["total_results"] >= 1


def test_page_two_uses_session_short_jump(monkeypatch):
    urls = _mock_open(monkeypatch, by_url=[
        ("short-jump", "find_tjl01_p2.html"),
        ("local_base=TJC01", "find_tjc01.html"),
    ], default="find_tjl01.html")
    r = tianjin._Client().search("三体", page=2)
    # jump=(page-1)*10+1=11，且必须用页内会话 URL（F/VV... 前缀）
    jumps = [u for u in urls if "short-jump" in u]
    assert jumps and "jump=11" in jumps[0]
    assert "/F/" in jumps[0]
    tj = [b for b in r.books if b.record_id.startswith("TJL01:")]
    assert tj[0].record_id == "TJL01:002916281"  # p2 首条与 p1 不同


def test_captcha_page_raises(monkeypatch):
    def spy(req, timeout=20):
        return "HTTP/1.1 401 Unauthorized\r\n\r\n请验证验证码"

    monkeypatch.setattr(tianjin, "_open", spy)
    try:
        tianjin._Client().search("三体")
        raise AssertionError("验证码页应抛 RuntimeError")
    except RuntimeError as e:
        assert "天津" in str(e)
