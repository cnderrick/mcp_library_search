"""interlib 家族 curlibcode quirk：多租户云托管馆（中新友好）需要按馆过滤。

默认空 = 穗杭行为（不带该参数）；非空时检索请求携带 curlibcode。
"""
from pathlib import Path

from mcp_library_search.interlib import InterlibConfig, search_books
from mcp_library_search.interlib import client as _client

_CFG = InterlibConfig(city="zxyh", name_cn="中新友好图书馆",
                      base_url="http://sm.interlib.cn:8104", curlibcode="STC001")
# 真实 client.get 返回 HTML 交由 parser 解析，stub 必须给可解析的空结果页
_EMPTY_HTML = (Path(__file__).parent / "fixtures" / "guangzhou"
               / "search_empty.html").read_text(encoding="utf-8")


def test_search_sends_curlibcode_when_configured(monkeypatch):
    seen = []

    def spy(cfg, path, params=None):
        seen.append(params)
        return _EMPTY_HTML

    monkeypatch.setattr(_client, "get", spy)
    search_books(_CFG, "三体")
    assert seen[0]["curlibcode"] == "STC001"


def test_search_omits_curlibcode_by_default(monkeypatch):
    seen = []
    cfg = InterlibConfig(city="guangzhou", name_cn="广州图书馆",
                         base_url="https://opac.gzlib.org.cn")

    def spy(cfg, path, params=None):
        seen.append(params)
        return _EMPTY_HTML

    monkeypatch.setattr(_client, "get", spy)
    search_books(cfg, "三体")
    assert "curlibcode" not in seen[0]
