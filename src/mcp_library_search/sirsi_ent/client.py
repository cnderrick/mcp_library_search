"""SirsiDynix Enterprise/VSE 家族 HTTP 层。

成员暂为郑州图书馆（`adapters/cn/zhengzhou.py`）。站点是 SirsiDynix Enterprise
（Portfolio 4.3，Tapestry 5.3.3 服务端渲染），非 JSON API 系——检索结果与详情
都是 HTML，馆藏分两部分：详情页内联的单册表（资料类型/条形码/排架号）+ 懒加载
的可用性 JSON（`loadavailability` 端点）。

**会话制**：`Enterprise` 用 `JSESSIONID` 串起检索→详情→可用性；本模块持一个
模块级 CookieJar，首次访问自动预热（GET 首页拿 cookie）。**`loadavailability`
必须带 `X-Requested-With: XMLHttpRequest`**，否则 Tapestry 回「未预料错误」页。

节流 1 秒/host，失败统一包装成含中文馆名的 RuntimeError。
"""
from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import SirsiEntConfig

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_THROTTLE = 1.0
_last_request = 0.0

_jar = CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_warmed: set[str] = set()


def _throttle():
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _fetch(url: str, ajax: bool = False, timeout: int = 40) -> str:
    headers = {"User-Agent": _UA}
    if ajax:
        headers["X-Requested-With"] = "XMLHttpRequest"
    req = urllib.request.Request(url, headers=headers)
    _throttle()
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        raise RuntimeError(f"请求失败：{e}") from e


def warm(config: SirsiEntConfig) -> None:
    """首次访问站点首页，拿 JSESSIONID（每 host 一次）。"""
    if config.base_url in _warmed:
        return
    _warmed.add(config.base_url)
    _fetch(config.base_url + config.ctx + "/", timeout=40)


def get(config: SirsiEntConfig, path: str, params: dict | None = None,
        ajax: bool = False, timeout: int = 40) -> str:
    """GET {base_url}{path}；params 经 URL 编码。返回 UTF-8 文本。

    网络层失败包装成含中文馆名的 RuntimeError。
    """
    warm(config)
    url = config.base_url + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        return _fetch(url, ajax=ajax, timeout=timeout)
    except RuntimeError as e:
        raise RuntimeError(f"{config.name_cn}：{e}") from e
