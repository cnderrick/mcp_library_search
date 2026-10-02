"""汇文 uopac 家族 HTTP 层：每 host 节流、可选 securitycam cookie、网络类错误重试一次。

测试的 monkeypatch 注入点就是这个 `get(url, cfg)`（同 aleph 家族 `client.get` 的
用法）；适配器与家族原语一律经它取数，别绕过。
"""
from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request

from . import parser

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_last_request: dict[str, float] = {}   # host → 上次请求时刻（各 host 独立计时）


def _throttle(url, cfg, now=None):
    """按 host 节流：同一 host 两次请求间隔不小于 cfg.throttle 秒。"""
    host = urllib.parse.urlsplit(url).netloc
    now = time.monotonic() if now is None else now
    wait = cfg.throttle - (now - _last_request.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last_request[host] = time.monotonic()


def is_challenge(text):
    """是否是 securitycam 反爬壳页（扬州站的 JS 挑战）。

    壳页特征：内联 slowAES 解密脚本 + 写 securitycam cookie + 跳回
    `?securitycam=1`。正常业务页绝不含 slowAES。
    """
    return "slowAES" in text and "securitycam" in text


def get(url, cfg, timeout=None):
    """GET 一个 uopac 页面，返回 utf-8 文本。

    带 cfg.securitycam 时附 `securitycam` cookie（扬州站全路径要求）；无 cookie
    或 cookie 失效时源站返回 JS 挑战壳页——此处**不自动重算**，直接抛含馆名的
    RuntimeError：常量轮换是响铃事件，不能静默退化成空结果。

    网络类错误（URLError/OSError，如金陵源偶然的 chunked 传输中途停顿）默认
    重试一次，每次重试照常节流；HTTP 状态错误是确定性的，不重试。
    """
    headers = {"User-Agent": _UA}
    if cfg.securitycam:
        headers["Cookie"] = f"securitycam={cfg.securitycam}"
    req = urllib.request.Request(url, headers=headers)
    timeout = cfg.timeout if timeout is None else timeout

    last = None
    for _ in range(2):
        _throttle(url, cfg)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{cfg.name_cn}请求失败：{e}") from e
        except (urllib.error.URLError, OSError) as e:
            last = e
            continue
        if is_challenge(text):
            raise RuntimeError(
                f"{cfg.name_cn}：站点返回 securitycam 反爬壳页——cookie 常量可能已被"
                f"轮换，需重算后更新适配器（步骤见 tests/fixtures/yangzhou/NOTES.md）")
        return text
    raise RuntimeError(f"{cfg.name_cn}请求失败：{last}") from last
