"""陕西批量接入城市适配器测试：config 正确 + 委托家族 + 契约缝。

覆盖 7 个新城市：西安/咸阳/宝鸡/安康（Interlib）、汉中（LibStar）、
陕西省图书馆/榆林（新版 UILAS）。已注册进 _ADAPTERS，结构由
tests/test_adapter_contract.py 自动校验；本文件钉各城 config 与家族委派。
"""
from types import SimpleNamespace
from unittest.mock import Mock

from mcp_library_search.adapters import base
from mcp_library_search.adapters.cn import (
    ankang, baoji, hanzhong, shaanxi, xian, xianyang, yulin,
)
from mcp_library_search.interlib import InterlibConfig
from mcp_library_search.libstar import LibStarConfig
from mcp_library_search.uilas_rest import UilasRestConfig


def test_interlib_configs():
    assert xian._CONFIG == InterlibConfig(
        city="xian", name_cn="西安市图书馆", base_url="https://opac.xalib.org.cn",
        ctx="/opac3", pro2018=True, api_detail=True)
    assert xianyang._CONFIG == InterlibConfig(
        city="xianyang", name_cn="咸阳市图书馆", base_url="http://61.185.20.96:8082",
        api_detail=True)
    assert baoji._CONFIG == InterlibConfig(
        city="baoji", name_cn="宝鸡市图书馆", base_url="http://1.82.133.119:8082",
        api_detail=True)
    assert ankang._CONFIG == InterlibConfig(
        city="ankang", name_cn="安康市图书馆", base_url="http://219.145.206.134:8082",
        pro2018=True, api_detail=True)


def test_hanzhong_config():
    assert hanzhong._CONFIG == LibStarConfig(
        city="hanzhong", name_cn="汉中市图书馆",
        base_url="https://findhanzhong.libsp.cn", groupcode="100121")


def test_uilas_rest_configs():
    assert shaanxi._CONFIG == UilasRestConfig(
        city="shaanxi", name_cn="陕西省图书馆",
        base_url="https://uilas.sxlib.org.cn", referer="https://uilas.sxlib.org.cn/")
    assert yulin._CONFIG == UilasRestConfig(
        city="yulin", name_cn="榆林市图书馆",
        base_url="https://www.yulinlib.org.cn", referer="https://www.yulinlib.org.cn/opac/")


def test_interlib_delegation(monkeypatch):
    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        return {"total_results": 1, "page": 1, "total_pages": 1, "has_next": False,
                "books": [{"book_id": "1", "title": "三体", "author": "刘",
                           "publisher": "P", "publish_year": "2022",
                           "availability_summary": ""}]}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake)
    page = xian.search_books("三体")
    assert page["books"][0]["book_id"] == "1"
    assert seen["cfg"] is xian._CONFIG
    base.validate_search_page(page)


def test_libstar_delegation(monkeypatch):
    monkeypatch.setattr("mcp_library_search.libstar.search_books",
                        lambda cfg, kw, page=1, limit=20: {
                            "total_results": 1, "page": 1, "total_pages": 1,
                            "has_next": False,
                            "books": [{"book_id": "187591", "title": "三体",
                                       "author": "刘慈欣 著", "publisher": "重庆出版社",
                                       "publish_year": "2010", "availability_summary": "纸本1，可借1"}]})
    page = hanzhong.search_books("三体")
    assert page["books"][0]["book_id"] == "187591"
    base.validate_search_page(page)


def test_uilas_rest_delegation(monkeypatch):
    monkeypatch.setattr("mcp_library_search.uilas_rest.search_books",
                        lambda cfg, kw, page=1, limit=20: {
                            "total_results": 1, "page": 1, "total_pages": 1,
                            "has_next": False,
                            "books": [{"book_id": "8099896", "title": "三体漫画",
                                       "author": "刘慈欣", "publisher": "浙江文艺出版社",
                                       "publish_year": "2025", "availability_summary": "纸本3，可借3"}]})
    page = shaanxi.search_books("三体")
    assert page["books"][0]["book_id"] == "8099896"
    base.validate_search_page(page)


def _patch_client(monkeypatch, mod, **return_values):
    client = Mock()
    for attr, value in return_values.items():
        getattr(client, attr).return_value = value
    monkeypatch.setattr(mod, "_client", client)
    return client


def _book(**kw):
    defaults = dict(
        record_id="1", title="三体", author="刘慈欣", publisher="重庆出版社",
        publish_year="2022", availability_summary="有馆藏", isbn="9787536692930",
        call_number="I247.55", summary="简介……",
    )
    return SimpleNamespace(**{**defaults, **kw})


def test_contract_seam_for_new_cities(monkeypatch):
    """镜像 tests/test_adapter_contract.py 的注入形态，确保非空 books 转换正确。"""
    for mod in (xian, xianyang, baoji, ankang, hanzhong, shaanxi, yulin):
        result = SimpleNamespace(
            success=True, error="",
            statistics={"total_results": 2, "page": 1, "total_pages": 1, "has_next": False},
            books=[_book(), _book(record_id="2", title="三体Ⅱ")],
        )
        _patch_client(monkeypatch, mod, search=result)
        page = mod.search_books("三体")
        assert page["books"][0]["book_id"] == "1", mod.__name__
        assert page["books"][1]["book_id"] == "2", mod.__name__
        base.validate_search_page(page)
