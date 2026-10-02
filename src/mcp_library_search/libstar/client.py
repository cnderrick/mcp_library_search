"""图星 LibStar Find 家族 HTTP 层：Referer／groupcode 必需头、节流、JSON 信封。

家族所有城市的检索/详情/馆藏请求都走这一个入口。两个必需头是本产品线的
接入关键（见 tests/fixtures/wuxi/NOTES.md 与 xuzhou/NOTES.md）：

- `Referer`：只校验存在（任意值即可）。缺失时**所有内容类端点**返回
  `errCode:9999`「系统访问中断」——措辞指向服务端宕机，实为反爬兜底；
- `groupcode`：租户号（≠ 任意馆的 libCode）。缺失不报错，HTTP 200 但
  `numFound` 恒 0（静默空结果）。

两者在 `request()` 统一注入，调用点无从遗漏。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import LibStarConfig

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

_THROTTLE = 1.0  # 秒/host 保守间隔（各站未观测到限频，留余量；单测 monkeypatch 关闭）
_last_request = 0.0


def throttle():
    """最小间隔限速：距上次请求不足 _THROTTLE 秒时睡足差值。"""
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def request(config: LibStarConfig, path: str, payload: dict | None = None,
            params: dict | None = None, timeout: int = 20) -> dict:
    """请求 {base_url}{path} 并返回解析后的 JSON 信封。

    `Referer` 与 `groupcode` 两个必需头在此统一注入。网络层失败包装成含
    中文馆名的 RuntimeError；响应非 JSON（被拦截页替换）也点名上抛。
    """
    url = config.base_url + path
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {
        "Referer": config.base_url + "/",
        "groupcode": config.groupcode,
        "User-Agent": _UA,
        "Accept": "application/json, text/plain, */*",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json;charset=UTF-8"
    req = urllib.request.Request(url, data=data, headers=headers)
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
