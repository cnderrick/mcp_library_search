"""天津 ALEPH 检索解析：brief 列表、ISB 单命中完整记录页、同会话 short-jump 翻页。

解析与 HTTP 已上收到 `aleph/` 家族模块；mock 点为家族 HTTP 入口
`aleph.client.get(url, config, timeout)`。fixture 结论见 tests/fixtures/tianjin/NOTES.md。
"""
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from mcp_library_search.adapters import tianjin
from mcp_library_search.aleph import CaptchaError
from mcp_library_search.aleph import client as aleph_client

_FIX = Path(__file__).parent / "fixtures" / "tianjin"


@pytest.fixture(autouse=True)
def _stub_zxyh(monkeypatch):
    """本文件只测 ALEPH 解析；ZXYH 源置空，避免真网。"""
    monkeypatch.setattr(tianjin, "il_search",
                        lambda cfg, keyword, page=1, limit=20: {
                            "books": [], "total_results": 0,
                            "total_pages": 1, "has_next": False})


def _load(name):
    return (_FIX / name).read_text(encoding="utf-8")


def _mock_get(monkeypatch, by_url=None, default=None, tjc01="find_tjc01.html"):
    """by_url: [(子串, fixture 名)] 按序匹配；default 兜底。返回记录的 URL 列表。

    tjc01 缺省路由到少儿馆自己的 fixture：两源 fixture 的 ISBN 无交集（NOTES.md），
    保证归并不会把单源断言变成复合 id。
    """
    urls = []

    def spy(url, config=None, timeout=20):
        urls.append(url)
        if by_url:
            for frag, name in by_url:
                if frag in url:
                    return _load(name)
        if tjc01 and "local_base=TJC01" in url:
            return _load(tjc01)
        return _load(default)

    monkeypatch.setattr(aleph_client, "get", spy)
    return urls


def test_parse_brief_list_tjl01(monkeypatch):
    urls = _mock_get(monkeypatch,default="find_tjl01.html")
    r = tianjin._Client().search("三体")
    assert r.statistics["total_results"] > 0
    b0 = r.books[0]
    assert b0.record_id.startswith("TJL01:")
    assert b0.title
    assert urls and "find-b" in urls[0] and "local_base=TJL01" in urls[0]


def test_brief_entry_fields(monkeypatch):
    _mock_get(monkeypatch,default="find_tjl01.html")
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
    urls = _mock_get(monkeypatch,default="find_tjc01.html")
    tianjin._Client().search("9787221179975")
    assert "find_code=ISB" in urls[0]


def test_isbn_single_hit_full_record_page(monkeypatch):
    # ISB 单命中直接返回完整记录页（非 brief 列表），也要解析成 1 条
    _mock_get(monkeypatch,default="find_tjl01_isbn.html")
    r = tianjin._Client().search("9787536692930")
    tj = [b for b in r.books if b.record_id.startswith("TJL01:")]
    assert len(tj) == 1
    assert tj[0].record_id == "TJL01:000856840"
    assert tj[0].title == "三体"
    assert tj[0].isbn == "978-7-5366-9293-0"
    assert tj[0].call_number == "I247.55/235"
    assert r.statistics["total_results"] >= 1


def test_page_two_uses_session_short_jump(monkeypatch):
    urls = _mock_get(monkeypatch,by_url=[
        ("short-jump", "find_tjl01_p2.html"),
        ("local_base=TJC01", "find_tjc01.html"),
    ], default="find_tjl01.html")
    r = tianjin._Client().search("三体", page=2)
    # jump=(page-1)*10+1=11，且必须用页内会话 URL（F/VV... 前缀）
    jumps = [u for u in urls if "short-jump" in u]
    assert jumps and "jump=11" in jumps[0]
    assert "/F/" in jumps[0]
    tj = [b for b in r.books if b.record_id.startswith("TJL01:")]
    # 两源的 jump URL 都命中 short-jump 分支返回同一 p2 fixture → 同 ISBN 归并成复合 id
    assert tj[0].record_id.startswith("TJL01:002916281")  # p2 首条与 p1 不同


def test_captcha_page_raises(monkeypatch):
    def spy(url, config=None, timeout=20):
        return "HTTP/1.1 401 Unauthorized\r\n\r\n请验证验证码"

    monkeypatch.setattr(aleph_client, "get", spy)
    try:
        tianjin._Client().search("三体")
        raise AssertionError("验证码页应抛 RuntimeError")
    except RuntimeError as e:
        assert "天津" in str(e)


class _Boom401:
    def open(self, req, timeout=20):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", None, None)


def test_http_401_raises_manual_unblock_hint(monkeypatch):
    # 401＝IP 被验证码墙封禁：错误必须给出「浏览器手动解封」的可操作提示
    monkeypatch.setattr(aleph_client, "_opener", _Boom401())
    with pytest.raises(RuntimeError) as ei:
        aleph_client.get("http://opacwh.tjl.tj.cn:8991/F?x=1", tianjin._SOURCES["TJL01"])
    msg = str(ei.value)
    assert "401" in msg and "解封" in msg and "天津" in msg


def test_search_401_punches_through_source_tolerance(monkeypatch):
    # 一个源 401，另一源健康：封禁信号仍要上抛提示，不静默降级成部分结果
    def spy(url, config=None, timeout=20):
        if "local_base=TJL01" in url:
            raise CaptchaError("天津图书馆：IP 被验证码墙封禁（HTTP 401），请手动解封")
        return _load("find_tjc01.html")

    monkeypatch.setattr(aleph_client, "get", spy)
    with pytest.raises(RuntimeError, match="解封"):
        tianjin._Client().search("三体")


def test_get_holdings_401_preserves_hint(monkeypatch):
    # 馆藏包装错误不得吞掉封禁提示（CaptchaError 原样穿透，不加馆名前缀包装）
    def spy(url, config=None, timeout=20):
        raise CaptchaError("天津图书馆：IP 被验证码墙封禁（HTTP 401），请手动解封")

    monkeypatch.setattr(aleph_client, "get", spy)
    with pytest.raises(RuntimeError, match="解封"):
        tianjin._Client().get_holdings("TJL01:002892667+ZXYH:217795")
