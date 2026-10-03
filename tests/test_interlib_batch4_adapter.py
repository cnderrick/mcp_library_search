"""第四批城市适配器测试：config（含 solr/ctx/captcha quirk）与契约缝。

太原/武汉/大庆/乐山 4 城已注册进 _ADAPTERS，输出结构由
tests/test_adapter_contract.py 自动校验；本文件钉各城 config，并用契约缝注入
自断言 record_id→book_id 的非空转换。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import daqing, leshan, taiyuan, wuhan
from mcp_library_search.interlib import InterlibConfig

CITIES = {
    "taiyuan": dict(name="太原市图书馆", base="http://opac.tylib.org.cn"),
    "wuhan": dict(name="武汉图书馆", base="https://opac.whlib.org.cn"),
    "daqing": dict(name="大庆市图书馆", base="http://111.43.226.77:8091"),
    "leshan": dict(name="乐山市图书馆", base="http://opac.sclib.cn:8088"),
}

MODULES = {"taiyuan": taiyuan, "wuhan": wuhan, "daqing": daqing, "leshan": leshan}


@pytest.mark.parametrize("city", sorted(CITIES))
def test_config(city):
    meta = CITIES[city]
    mod = MODULES[city]
    assert mod._CONFIG.city == city
    assert mod._CONFIG.name_cn == meta["name"]
    assert mod._CONFIG.base_url == meta["base"]
    assert mod._CONFIG.api_detail is True


def test_config_quirks():
    assert taiyuan._CONFIG.solr_search is True and taiyuan._CONFIG.ctx == "/opac"
    assert wuhan._CONFIG.solr_search is False and wuhan._CONFIG.ctx == "/opac"
    # 大庆应用上下文是根路径
    assert daqing._CONFIG.ctx == ""
    # 乐山：pro2018 ＋ 省图过滤 ＋ 验证码墙
    assert leshan._CONFIG == InterlibConfig(
        city="leshan", name_cn="乐山市图书馆", base_url="http://opac.sclib.cn:8088",
        pro2018=True, api_detail=True, f_curlibcode="LS", captcha=True)


@pytest.mark.parametrize("city", sorted(CITIES))
def test_contract_seam(monkeypatch, city):
    mod = MODULES[city]
    client = Mock()
    result = SimpleNamespace(
        success=True, error="",
        statistics={"total_results": 1, "page": 1, "total_pages": 1, "has_next": False},
        books=[SimpleNamespace(record_id="rid-1", title="三体", author="刘慈欣",
                               publisher="重庆出版社", publish_year="2008",
                               availability_summary="", isbn="9787536692930",
                               call_number="I247.55", summary="...")])
    client.search.return_value = result
    monkeypatch.setattr(mod, "_client", client)
    page = mod.search_books("三体")
    assert page["books"][0]["book_id"] == "rid-1"
    base.validate_search_page(page)
