"""ALEPH 家族 HTTP 层：UA、会话 CookieJar、每 host 节流、验证码墙识别。

封禁是**全局**信号（按 IP），必须穿透上层源级容错直达调用方——静默降级成
部分结果会误导。
"""
from __future__ import annotations

import time
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import AlephConfig

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
HEADERS = {"User-Agent": UA}


class CaptchaError(RuntimeError):
    """验证码墙：按 IP 的全局限速信号，必须穿透源级容错直达调用方，不静默降级。"""


class Throttle:
    """最小间隔限速器：距上次 wait() 不足 interval 时睡足差值。

    clock/sleep 可注入供单测；真网默认 time.monotonic/time.sleep。
    """

    def __init__(self, interval, clock=time.monotonic, sleep=time.sleep):
        self.interval = interval
        self._clock = clock
        self._sleep = sleep
        self._last = None

    def wait(self):
        now = self._clock()
        if self._last is not None:
            deficit = self.interval - (now - self._last)
            if deficit > 0:
                self._sleep(deficit)
                now = self._clock()
        self._last = now


# 每 host 一个限速器：多台 ALEPH 是不同服务器，各自计时互不拖累
_throttles = {}


def throttle_for(url, interval):
    host = urllib.parse.urlsplit(url).netloc
    th = _throttles.get(host)
    if th is None or th.interval != interval:
        th = _throttles[host] = Throttle(interval)
    return th


_jar = CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))


def check_captcha(text, config: "AlephConfig"):
    """验证码墙：立即抛错，不重试硬闯（按 IP 封，硬闯只会延长封禁）。"""
    if "验证码" in text:
        raise CaptchaError(
            f"{config.name_cn}：检索过于频繁触发验证码，请在浏览器逐个打开 "
            f"{config.unblock_urls} 输入验证码手动解封后重试")


def get(url, config: "AlephConfig", timeout: int = 20) -> str:
    """HTTP 入口：CookieJar 会话 + 每 host 节流，返回 UTF-8 文本。

    `url` 可以是 str 或 urllib.request.Request。
    HTTP 401＝IP 被验证码墙封禁：抛 CaptchaError 给出手动解封提示，不重试硬闯。
    """
    req = url if isinstance(url, urllib.request.Request) else \
        urllib.request.Request(url, headers=HEADERS)
    throttle_for(req.full_url, config.throttle).wait()
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise CaptchaError(
                f"{config.name_cn}：IP 被验证码墙封禁（HTTP 401），请在浏览器逐个打开 "
                f"{config.unblock_urls} 输入验证码手动解封后重试") from e
        raise RuntimeError(f"{config.name_cn}请求失败：{e}") from e
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"{config.name_cn}请求失败：{e}") from e
