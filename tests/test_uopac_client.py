"""uopac 家族 HTTP 层测试：securitycam cookie、壳页识别、节流与重试。

全部离线：monkeypatch `urllib.request.urlopen`，不打真实站点。
"""
import urllib.error

import pytest

from mcp_library_search.uopac import client
from mcp_library_search.uopac import UopacConfig

_CHALLENGE = ('<html><body><script src="/aes.min.js"></script><script>'
              'function toHex(){}var slowAES={};'
              'document.cookie="securitycam="+toHex(slowAES.decrypt(c,2,a,b));'
              'location.href="/uopac/s/search.action?securitycam=1";</script></body></html>')


class _Resp:
    def __init__(self, text):
        self._b = text.encode("utf-8")

    def read(self):
        return self._b

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture(autouse=True)
def _isolate_throttle():
    """每例重置节流状态，免得上例的 host 计时拖慢下例（家族层级是共享的）。"""
    client._last_request.clear()
    yield
    client._last_request.clear()


def _cfg(**kw):
    kw.setdefault("throttle", 0.0)     # 默认关节流，免得测试互相拖慢
    return UopacConfig(name_cn="测试馆", base_url="http://example.invalid", **kw)


def test_is_challenge_detects_shell_only():
    assert client.is_challenge(_CHALLENGE)
    # 正常业务页绝不含 slowAES
    assert not client.is_challenge('<div id="found">有 <font color="red">3</font> 项</div>')


def test_cookie_header_sent_only_when_configured(monkeypatch):
    seen = []

    def fake_urlopen(req, timeout=None):
        seen.append(req)
        return _Resp("ok")

    monkeypatch.setattr(client.urllib.request, "urlopen", fake_urlopen)
    client.get("http://example.invalid/uopac/s/search_result.action", _cfg())
    client.get("http://example.invalid/uopac/s/search_result.action",
               _cfg(securitycam="6322e5171be855cb6e0f4e8b640895e6"))
    assert seen[0].headers.get("Cookie") is None
    assert seen[1].headers.get("Cookie") == "securitycam=6322e5171be855cb6e0f4e8b640895e6"


def test_challenge_shell_raises_loudly(monkeypatch):
    # cookie 失效/常量轮换 → 必须响铃：不静默退化成空结果
    monkeypatch.setattr(client.urllib.request, "urlopen",
                        lambda req, timeout=None: _Resp(_CHALLENGE))
    with pytest.raises(RuntimeError) as ei:
        client.get("http://example.invalid/uopac/s/search_result.action", _cfg())
    msg = str(ei.value)
    assert "测试馆" in msg and "securitycam" in msg and "轮换" in msg


def test_network_error_retries_once(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req)
        if len(calls) == 1:
            raise urllib.error.URLError("connection reset")
        return _Resp("ok")

    monkeypatch.setattr(client.urllib.request, "urlopen", fake_urlopen)
    assert client.get("http://example.invalid/x", _cfg()) == "ok"
    assert len(calls) == 2


def test_network_error_exhausts_and_raises(monkeypatch):
    def fake_urlopen(req, timeout=None):
        raise urllib.error.URLError("connection reset")

    monkeypatch.setattr(client.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="测试馆请求失败"):
        client.get("http://example.invalid/x", _cfg())


def test_http_error_no_retry(monkeypatch):
    calls = []

    def fake_urlopen(req, timeout=None):
        calls.append(req)
        raise urllib.error.HTTPError(req.full_url, 503, "Service Unavailable", {}, None)

    monkeypatch.setattr(client.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(RuntimeError, match="503"):
        client.get("http://example.invalid/x", _cfg())
    assert len(calls) == 1        # HTTP 状态错误是确定性的，不重试


def test_throttle_is_per_host(monkeypatch):
    clock = {"t": 1000.0}
    slept = []
    monkeypatch.setattr(client.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(client.time, "sleep", slept.append)
    cfg = _cfg(throttle=4.0)

    client._throttle("http://a.invalid/uopac/s/x", cfg)
    assert slept == []                     # 首次无等待
    clock["t"] = 1001.0
    client._throttle("http://a.invalid/uopac/s/x", cfg)
    assert slept == [3.0]                  # 距上次 1 秒 → 补 3 秒
    slept.clear()
    clock["t"] = 1002.0
    client._throttle("http://b.invalid/uopac/s/x", cfg)
    assert slept == []                     # 另一 host 独立计时
