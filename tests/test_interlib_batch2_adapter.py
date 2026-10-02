"""第二批 Interlib 城市适配器测试：config（含 solr/api_detail quirk）与契约缝。

20 个新城市（HTML 检索 13 ＋ Solr 检索 7）已注册进 _ADAPTERS，输出结构由
tests/test_adapter_contract.py 自动校验；本文件钉各城 config，并用契约缝注入
自断言 record_id→book_id 的非空转换。
"""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import (
    baotou, changchun, chaozhou, dezhou, fujian_prov, haikou, heilongjiang, heyuan, huhehaote, hunan_prov, jingmen, quanzhou, tangshan, tongliao, wuhai, xiaogan, yangjiang, zhoukou, zhuzhou, zibo,
)
from mcp_library_search.interlib import InterlibConfig

CITIES = {
    "haikou": dict(name="海口市图书馆", base="http://221.11.163.25:5656", solr=False),
    "zhuzhou": dict(name="株洲市图书馆", base="http://218.75.211.12:8899", solr=False),
    "xiaogan": dict(name="孝感市图书馆", base="http://183.92.156.82:6061", solr=False),
    "jingmen": dict(name="荆门市图书馆", base="http://221.234.32.236:8081", solr=False),
    "hunan_prov": dict(name="湖南图书馆", base="https://opac.library.hn.cn", solr=False),
    "fujian_prov": dict(name="福建省图书馆", base="https://opac.fjlib.net", solr=False),
    "yangjiang": dict(name="阳江市图书馆", base="http://219.129.187.234:38082", solr=False),
    "zibo": dict(name="淄博市图书馆", base="http://zblib.org.cn:458", solr=False),
    "dezhou": dict(name="德州市图书馆", base="https://opac.dzelib.cn", solr=False),
    "zhoukou": dict(name="周口市图书馆", base="http://222.136.172.30:8079", solr=False),
    "quanzhou": dict(name="泉州市图书馆", base="http://218.66.169.78:85", solr=False),
    "tongliao": dict(name="通辽市图书馆", base="http://60.31.181.203:8088", solr=False),
    "heyuan": dict(name="河源市图书馆", base="https://interlib.hylib.cn:9443", solr=False),
    "heilongjiang": dict(name="黑龙江省图书馆", base="http://lib.hljlib.org.cn:2333", solr=True),
    "changchun": dict(name="长春市图书馆", base="http://221.8.55.75:8888", solr=True),
    "tangshan": dict(name="唐山市图书馆", base="https://opac.tslib.net:7085", solr=True),
    "baotou": dict(name="包头市图书馆", base="https://opac.btslib.cn:8088", solr=True),
    "wuhai": dict(name="乌海市图书馆", base="http://1.24.223.177:8085", solr=True),
    "huhehaote": dict(name="呼和浩特市图书馆", base="http://w.hhhtlib.org.cn:92", solr=True),
    "chaozhou": dict(name="潮州市图书馆", base="http://czlib.cn:8089", solr=True),
}

MODULES = {
    "baotou": baotou,
    "changchun": changchun,
    "chaozhou": chaozhou,
    "dezhou": dezhou,
    "fujian_prov": fujian_prov,
    "haikou": haikou,
    "heilongjiang": heilongjiang,
    "heyuan": heyuan,
    "huhehaote": huhehaote,
    "hunan_prov": hunan_prov,
    "jingmen": jingmen,
    "quanzhou": quanzhou,
    "tangshan": tangshan,
    "tongliao": tongliao,
    "wuhai": wuhai,
    "xiaogan": xiaogan,
    "yangjiang": yangjiang,
    "zhoukou": zhoukou,
    "zhuzhou": zhuzhou,
    "zibo": zibo,
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
