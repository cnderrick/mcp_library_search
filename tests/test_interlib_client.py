"""Interlib 家族 HTTP 层测试：URL 拼接、UA、超时、错误包装。"""
import pytest

from mcp_library_search.interlib import InterlibConfig
from mcp_library_search.interlib import client

_CFG = InterlibConfig(city="guangzhou", name_cn="广州图书馆", base_url="https://opac.gzlib.org.cn")


def test_get_builds_url_with_params(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["ua"] = req.get_header("User-agent")
        captured["timeout"] = timeout

        class Resp:
            def read(self):
                return "你好".encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        return Resp()

    monkeypatch.setattr(client.urllib.request, "urlopen", fake_urlopen)
    body = client.get(_CFG, "/opac/search", {"q": "活着", "page": 1})
    assert body == "你好"
    assert captured["url"].startswith("https://opac.gzlib.org.cn/opac/search?q=")
    assert "%E6%B4%BB%E7%9D%80" in captured["url"]  # 活着 被 URL 编码
    assert "page=1" in captured["url"]
    assert captured["ua"] and "Mozilla" in captured["ua"]
    assert captured["timeout"] == 20


def test_get_wraps_network_errors(monkeypatch):
    def boom(req, timeout=None):
        raise client.urllib.error.URLError("reset by peer")

    monkeypatch.setattr(client.urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError, match="广州图书馆请求失败"):
        client.get(_CFG, "/opac/search", {"q": "x"})


def test_get_wraps_http_errors(monkeypatch):
    def boom(req, timeout=None):
        raise client.urllib.error.HTTPError("u", 503, "Service Unavailable", None, None)

    monkeypatch.setattr(client.urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError, match="广州图书馆请求失败"):
        client.get(_CFG, "/opac/book/1")
