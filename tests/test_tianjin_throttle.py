"""ALEPH 家族限速器：注入时钟的 Throttle 与 client.get 的每 host 节流接线。

限速器已上收到 `aleph/client.py`（天津与南京图书馆共用），本文件跟着改指家族模块。
验证码抛错路径已由 test_aleph_client.py::test_captcha_page_raises 钉住
（响应含「验证码」→ RuntimeError 含馆名，不重试硬闯）。
"""
import pytest

from mcp_library_search.aleph import client


class _FakeTime:
    """假时钟：sleep 即推进，记录每次 sleep 时长。"""

    def __init__(self):
        self.now = 0.0
        self.slept = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def test_throttle_first_wait_never_sleeps():
    ft = _FakeTime()
    th = client.Throttle(4.0, clock=ft.clock, sleep=ft.sleep)
    th.wait()
    assert ft.slept == []


def test_throttle_sleeps_deficit():
    ft = _FakeTime()
    th = client.Throttle(4.0, clock=ft.clock, sleep=ft.sleep)
    th.wait()
    ft.now += 1.0          # 只过了 1 秒 → 差 3 秒
    th.wait()
    assert ft.slept == [pytest.approx(3.0)]


def test_throttle_no_sleep_when_interval_passed():
    ft = _FakeTime()
    th = client.Throttle(4.0, clock=ft.clock, sleep=ft.sleep)
    th.wait()
    ft.now += 10.0         # 超过间隔 → 不睡
    th.wait()
    assert ft.slept == []


def test_per_host_throttle_instances(monkeypatch):
    monkeypatch.setattr(client, "_throttles", {})
    a = client.throttle_for("http://opacwh.tjl.tj.cn:8991/F?x=1", 4.0)
    b = client.throttle_for("http://opacwh.tjl.tj.cn:8991/F?x=2", 4.0)
    c = client.throttle_for("http://opacse.tjl.tj.cn:8991/F?x=1", 4.0)
    assert a is b          # 同 host 复用同一限速器
    assert a is not c      # 主馆与少儿馆是不同 host，各自计时

