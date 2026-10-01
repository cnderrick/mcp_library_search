"""Interlib 家族 HTTP 层：UA 伪装、超时、URL 拼接、错误包装。

家族所有城市的页面与 JSON 接口请求都走这一个入口，
失败统一包装成含中文馆名的 RuntimeError，便于上层与 LLM 报错。
"""
import urllib.error
import urllib.parse
import urllib.request

from . import InterlibConfig

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


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
