"""Interlib 家族 HTTP 层：UA 伪装、超时、URL 拼接、错误包装。

家族所有城市的页面与 JSON 接口请求都走这一个入口，
失败统一包装成含中文馆名的 RuntimeError，便于上层与 LLM 报错。
"""
from __future__ import annotations

import urllib.error
import urllib.parse
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import InterlibConfig

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


class CaptchaError(RuntimeError):
    """验证码墙：检索页被滑动验证码拦（「opac验证」），不自动破解，给出人工过码指引。"""


def check_captcha(text: str, config: InterlibConfig) -> None:
    """命中「opac验证」滑动验证码页即抛 CaptchaError（不重试、不破解）。

    与 ALEPH 家族（天津/南京）同一口径：验证码墙是全局信号，穿透源级容错
    直达调用方；静默返回空结果或自行破解都会误导。
    """
    if "opac验证" in text:
        raise CaptchaError(
            f"{config.name_cn}：检索命中验证码墙（opac验证），请在浏览器打开 "
            f"{config.base_url}{config.ctx}/index 手动过码后重试")


def get(config: InterlibConfig, path: str, params: dict | None = None, timeout: int = 20) -> str:
    """GET {base_url}{path}，params 经 URL 编码；返回 UTF-8 文本。

    网络层任何失败都包装成 RuntimeError，消息含中文馆名。
    """
    url = config.base_url + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        raise RuntimeError(f"{config.name_cn}请求失败：{e}") from e
