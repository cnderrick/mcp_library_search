"""图创 tcc-opac 家族 HTTP 层：节流、访客令牌、JSON POST。

端点（相对 `config.base_url` = `{host}/api/tcc-opac/{seg}`）：
- 令牌 `POST /system/user/getOpenApiAccessToken`（匿名 `{}` 即发，`data.token`，
  `expiresIn` 秒级字符串）→ 请求头 `ACCESS-TOKEN`；
- 业务 POST，`code==1003`（令牌失效）自动重取一次重试。

令牌按 `base_url` 独立缓存（同城多源/多城不串）。形态由宁波前端 JS 逆向并实抓
验证，见 tests/fixtures/ningbo/NOTES.md；family 成员行为一致。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import TccOpacConfig

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

_THROTTLE = 4.0   # 秒/请求，保守限速（令牌请求同样计入）
_TIMEOUT = 30
_TOKEN_LEEWAY = 60  # 令牌提前 60 秒视为过期

_last_request = 0.0
_token_cache: dict[str, tuple[str, float]] = {}  # base_url -> (token, exp_monotonic)


def open(config: TccOpacConfig, req: urllib.request.Request, timeout: int = _TIMEOUT) -> str:
    """HTTP 入口：4 秒节流，返回响应文本。失败抛含馆名的 RuntimeError。"""
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"{config.name_cn}请求失败：{e}") from e


def _headers(config: TccOpacConfig) -> dict:
    return {"User-Agent": _UA, "Referer": config.referer,
            "Content-Type": "application/json"}


def ensure_token(config: TccOpacConfig, force: bool = False) -> str:
    """访客令牌：匿名 POST 即发，按 base_url 缓存到 expiresIn（源站给字符串）。"""
    key = config.base_url
    token, exp = _token_cache.get(key, ("", 0.0))
    if not force and token and time.monotonic() < exp - _TOKEN_LEEWAY:
        return token
    url = config.base_url + "/system/user/getOpenApiAccessToken"
    req = urllib.request.Request(url, data=b"{}", headers=_headers(config), method="POST")
    text = open(config, req)
    try:
        resp = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"{config.name_cn}：令牌响应不是 JSON：{text[:120]}") from e
    data = resp.get("data") or {}
    tk = str(data.get("token") or "")
    if resp.get("code") != 200 or not tk:
        raise RuntimeError(
            f"{config.name_cn}：获取访客令牌失败（code={resp.get('code')}）："
            f"{resp.get('desc') or ''}")
    try:
        expiry = float(data.get("expiresIn") or 3600)
    except (TypeError, ValueError):
        expiry = 3600.0
    _token_cache[key] = (tk, time.monotonic() + expiry)
    return tk


def post(config: TccOpacConfig, path: str, payload: dict | None = None,
         params: dict | None = None) -> dict:
    """POST JSON 到 `config.base_url + path`，注入 ACCESS-TOKEN，1003 重取重试一次。

    `params` 拼查询串（getbyid 的 axios params 形态）；响应非 JSON 视为被拦截。
    """
    url = config.base_url + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(payload if payload is not None else {}).encode("utf-8")

    def once(tk: str) -> dict:
        headers = _headers(config)
        if tk:
            headers["ACCESS-TOKEN"] = tk
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        text = open(config, req)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(
                f"{config.name_cn}：响应不是 JSON（可能被拦截或接口变更）：{text[:120]}") from e

    resp = once(ensure_token(config))
    if isinstance(resp, dict) and resp.get("code") == 1003:
        resp = once(ensure_token(config, force=True))
    return resp
