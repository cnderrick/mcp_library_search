"""乐山验证码墙测试：命中「opac验证」抛 CaptchaError，不破解（天津 ALEPH 口径）。

字段侦察结论见 tests/fixtures/leshan/NOTES.md。乐山借四川省图书馆联合目录按
`f_curlibcode=LS` 过滤；检索页是滑动验证码墙且无内嵌 Solr，故命中即抛错。
"""
from pathlib import Path

import pytest

from mcp_library_search.interlib import InterlibConfig, search_books
from mcp_library_search.interlib import client as _client

FIXTURES = Path(__file__).parent / "fixtures"
CAPTCHA = (FIXTURES / "leshan" / "search_captcha.html").read_text(encoding="utf-8")

_CFG = InterlibConfig(
    city="leshan", name_cn="乐山市图书馆", base_url="http://opac.sclib.cn:8088",
    pro2018=True, api_detail=True, f_curlibcode="LS", captcha=True)


def test_check_captcha_detects_wall():
    with pytest.raises(_client.CaptchaError, match="乐山市图书馆"):
        _client.check_captcha(CAPTCHA, _CFG)


def test_check_captcha_passes_normal_page():
    _client.check_captcha("<html><title>检索系统</title>正常页</html>", _CFG)


def test_search_raises_captcha(monkeypatch):
    monkeypatch.setattr(_client, "get", lambda cfg, path, params=None: CAPTCHA)
    with pytest.raises(_client.CaptchaError, match="opac验证"):
        search_books(_CFG, "三体")


def test_search_sends_f_curlibcode(monkeypatch):
    seen = {}

    def spy(cfg, path, params=None):
        seen["params"] = params
        return "<html></html>"

    monkeypatch.setattr(_client, "get", spy)
    search_books(_CFG, "三体")
    assert seen["params"]["f_curlibcode"] == "LS"


def test_search_omits_f_curlibcode_by_default(monkeypatch):
    seen = {}

    def spy(cfg, path, params=None):
        seen["params"] = params
        return "<html></html>"

    monkeypatch.setattr(_client, "get", spy)
    cfg = InterlibConfig(city="wuhan", name_cn="武汉图书馆",
                         base_url="https://opac.whlib.org.cn")
    search_books(cfg, "三体")
    assert "f_curlibcode" not in seen["params"]
