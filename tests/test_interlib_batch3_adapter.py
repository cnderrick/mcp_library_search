"""第三批 Interlib 城市适配器测试：config（含 solr/api_detail quirk）与契约缝。

12 个新城市（HTML 检索 10 ＋ Solr 检索 2）已注册进 _ADAPTERS，输出结构由
tests/test_adapter_contract.py 自动校验；本文件钉各城 config，并用契约缝注入
自断言 record_id→book_id 的非空转换。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import (
    chuxiong, dehong, deqing, huangshi, lincang, nujiang, qiandongnan, qiannan,
    qujing, xishuangbanna, zunyi, honghe,
)
from mcp_library_search.interlib import InterlibConfig

CITIES = {
    "huangshi": dict(name="黄石市图书馆", base="http://61.184.117.12:8081", solr=False),
    "zunyi": dict(name="遵义市图书馆", base="http://opac.zylib.cn:82", solr=False),
    "qiandongnan": dict(name="黔东南州图书馆", base="http://111.124.33.40:8088", solr=False),
    "qiannan": dict(name="黔南州图书馆", base="http://114.135.66.82:8082", solr=False),
    "qujing": dict(name="曲靖市图书馆", base="http://www.qjlib.com.cn:8088", solr=False),
    "lincang": dict(name="临沧市图书馆", base="http://106.58.172.142:8081", solr=False),
    "chuxiong": dict(name="楚雄州图书馆", base="http://220.165.139.19:8082", solr=False),
    "honghe": dict(name="红河州图书馆", base="http://182.246.32.25:83", solr=False),
    "dehong": dict(name="德宏州图书馆", base="http://36.140.104.72:8086", solr=False),
    "nujiang": dict(name="怒江州图书馆", base="http://106.58.214.4:8082", solr=False),
    "deqing": dict(name="德清县图书馆", base="http://opac.dqlib.com.cn", solr=True),
    "xishuangbanna": dict(name="西双版纳州图书馆", base="http://106.58.209.101:8080", solr=True),
}

MODULES = {
    "chuxiong": chuxiong,
    "dehong": dehong,
    "deqing": deqing,
    "honghe": honghe,
    "huangshi": huangshi,
    "lincang": lincang,
    "nujiang": nujiang,
    "qiandongnan": qiandongnan,
    "qiannan": qiannan,
    "qujing": qujing,
    "xishuangbanna": xishuangbanna,
    "zunyi": zunyi,
}


@pytest.mark.parametrize("city", sorted(CITIES))
def test_config(city):
    meta = CITIES[city]
    mod = MODULES[city]
    assert mod._CONFIG.city == city
    assert mod._CONFIG.name_cn == meta["name"]
    assert mod._CONFIG.base_url == meta["base"]
    assert mod._CONFIG.api_detail is True
    assert mod._CONFIG.solr_search is meta["solr"]
    assert mod._CONFIG == InterlibConfig(
        city=city, name_cn=meta["name"], base_url=meta["base"],
        api_detail=True, solr_search=meta["solr"])


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
