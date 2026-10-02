"""UILAS（ILAS 系 HTML OPAC）家族 HTTP 层：节流、UA、可选旧式 TLS 兜底。

家族所有城市的页面请求都走这一个入口。匿名可通、无需 CookieJar。

**旧式 TLS quirk（舟山）**：部分 UILAS 站点（如舟山 `opac.zsodl.cn`）**只支持
静态 RSA 密钥交换**的 TLS 1.2 密码套件（`TLS_RSA_WITH_AES_256_GCM_SHA384` 等），
而 OpenSSL 3.5 的默认密码列表已停用静态 RSA kx，导致 `urlopen` 默认上下文直接
`SSLV3_ALERT_HANDSHAKE_FAILURE`。`UilasConfig.ssl_ciphers` 非空时，本层用
`ssl.create_default_context()` ＋ `set_ciphers()` 显式放行这些套件，按套件串缓存
opener。金华是纯 HTTP，不受影响。
"""
from __future__ import annotations

import ssl
import time
import urllib.error
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import UilasConfig

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_THROTTLE = 4.0  # 秒/host；天津 ILAS 家族经验的安全线（NOTES.md）
_last_request = 0.0
_openers: dict[str, urllib.request.OpenerDirector] = {}


def _opener_for(ciphers: str) -> urllib.request.OpenerDirector:
    """按密码套件串构建（并缓存）opener；空串走默认 opener。"""
    if not ciphers:
        return _openers.setdefault("", urllib.request.build_opener())
    if ciphers not in _openers:
        ctx = ssl.create_default_context()
        ctx.set_ciphers(ciphers)
        _openers[ciphers] = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ctx))
    return _openers[ciphers]


def open(config: UilasConfig, req: urllib.request.Request, timeout: int = 30) -> str:
    """HTTP 入口：4 秒节流，返回 UTF-8 文本。失败抛含馆名的 RuntimeError。"""
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    opener = _opener_for(getattr(config, "ssl_ciphers", ""))
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"{config.name_cn}请求失败：{e}") from e
