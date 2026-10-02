"""新版 UILAS（ILAS REST 检索平台）家族 HTTP 层。

与老版 `uilas/`（HTML OPAC，`NTRdrBookRetr.do`）同宗不同代：新版是前后端分离的
REST 平台，前端 Vue，接口在 `/prod-api/*`（nginx 映射到后端 `/ILASOPAC/*`），
返回 JSON。**必需 `Referer` 头**——部分部署（榆林）只认与站点同路径的 Referer，
缺失或不匹配会回 `{"code":401,"msg":"…认证失败…"}`（即便接口本身匿名可通）。

各站响应信封 `{"msg","code","data"}`，`code==200` 为成功。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import UilasRestConfig

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_THROTTLE = 1.0
_last_request = 0.0


def throttle():
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def request(config: UilasRestConfig, path: str, params: dict | None = None,
            timeout: int = 30) -> dict:
    """请求 {base_url}{path} 并返回解析后的 JSON 信封。失败抛含馆名的 RuntimeError。"""
    url = config.base_url + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {
        "Referer": config.referer or (config.base_url + "/"),
        "User-Agent": _UA,
        "Accept": "application/json, text/plain, */*",
    }
    req = urllib.request.Request(url, headers=headers)
    throttle()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(
            f"{config.name_cn}：请求失败（{path}）：{getattr(e, 'reason', e)}") from e
    try:
        return json.loads(body)
    except ValueError as e:
        raise RuntimeError(
            f"{config.name_cn}：响应不是 JSON（可能被拦截或接口变更）：{body[:120]}") from e
