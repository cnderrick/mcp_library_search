import pytest

from mcp_library_search.adapters.cn import shenzhen


def test_get_sets_headers_and_parses_json(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["ua"] = req.get_header("User-agent")
        captured["ref"] = req.get_header("Referer")

        class Resp:
            def read(self):
                return b'{"data": {"numFound": 1}}'
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        return Resp()

    monkeypatch.setattr(shenzhen.urllib.request, "urlopen", fake_urlopen)
    body = shenzhen._get("/api/opacservice/getQueryResult", {"v_value": "三体"})
    assert body == {"data": {"numFound": 1}}
    assert "szlib.org.cn/api/opacservice/getQueryResult" in captured["url"]
    assert "client_id=t1" in captured["url"]
    assert captured["ua"] and "Mozilla" in captured["ua"]
    assert captured["ref"] == "https://www.szlib.org.cn/opac/"


def test_get_wraps_errors(monkeypatch):
    def boom(req, timeout=None):
        raise shenzhen.urllib.error.URLError("reset")
    monkeypatch.setattr(shenzhen.urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError, match="深圳图书馆请求失败"):
        shenzhen._get("/api/opacservice/getQueryResult", {})


def test_get_wraps_bad_json(monkeypatch):
    def bad(req, timeout=None):
        class Resp:
            def read(self):
                return b"<html>not json</html>"
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
        return Resp()
    monkeypatch.setattr(shenzhen.urllib.request, "urlopen", bad)
    with pytest.raises(RuntimeError, match="深圳图书馆请求失败"):
        shenzhen._get("/api/opacservice/getQueryResult", {})
