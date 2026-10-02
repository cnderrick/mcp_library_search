"""独立验收测试：2026-10-02 批量城市接入（QA 侧钉子，全离线不打真网）。

验收依据：docs/data-sources/cn.md 总览表＋AGENTS.md 铁律。本文件钉的是
「注册表 ↔ server.py 文案 ↔ data-sources 登记」三方一致性——任何一侧
单独增删城市或改口径而另两侧没跟上，这里直接红。行为级验收（tagTr 修复、
杭州裸 id 垫片、双源归并）已由 test_jiangyin_parser / test_wenzhou_compat /
test_hefei_parse / test_hangzhou_merge / test_hefei_merge 各自钉住，不在此重复；
南京「金陵＋南图」双源由 test_nanjing_dual_source.py 钉住，南图 ALEPH 侧的
家族兼容性证据在 test_nanjing_prov_recon.py。
"""
from pathlib import Path

from mcp_library_search import adapters, server

_DOCS = Path(__file__).resolve().parent.parent / "docs" / "data-sources" / "cn.md"

# 完整注册面：既有 6 城＋第一批 6 标识＋第二批 4 标识（成都/宁波/绍兴/大连）
# ＋青岛（2026-10-02 发现开放 Solr 检索通道后接入）
# ＋无锡（2026-10-02 修正误判后接入，无锡市新吴区图书馆单馆）
# ＋扬州（2026-10-02 定性 securitycam 为静态挑战后接入，汇文 uopac 家族）
# ＋苏州（2026-10-03 立项城市落地；后并入苏州工业园区馆为双源，图创 Interlib）
# ＋徐州（2026-10-03 立项城市落地，抽出图星 LibStar Find 家族）
# ＋淮安、盐城（2026-10-03 立项城市落地，LibStar 家族新增配置）
# ＋丽水（Interlib pro2018）、舟山（抽出 UILAS 家族，旧式 TLS quirk）
# ＋陕西批量：西安/咸阳/宝鸡/安康（Interlib，新增 ctx/api_detail quirk）、
#   汉中（LibStar 家族新增配置）、陕西省图书馆/榆林（抽出新版 UILAS REST 家族）
_EXPECTED = [
    "ankang", "baoji", "baotou", "changchun", "chaozhou", "chengdu",
    "chongqing", "dalian", "dezhou", "eerduosi", "fujian_prov", "guangzhou",
    "haikou", "hangzhou", "hanzhong", "hefei", "heilongjiang", "henan_prov",
    "heyuan", "huaian", "huhehaote", "hunan_prov", "jiangmen", "jiangyin",
    "jinan", "jingmen", "jinhua", "lanzhou", "lishui", "nanjing", "ningbo",
    "qingdao", "quanzhou", "shaanxi", "shanghai", "shaoxing", "shenzhen",
    "suzhou", "taizhou", "tangshan", "tianjin", "tongliao", "wenzhou",
    "wuhai", "wuxi", "xian", "xianyang", "xiaogan", "xuzhou", "yancheng",
    "yangjiang", "yangzhou", "yulin", "zhoukou", "zhoushan", "zhuzhou",
    "zibo",
]


def test_registry_has_exactly_fifty_seven_identifiers():
    # 注册表两级：地区取域名后缀，现有城市全在默认地区 cn（中国）下
    assert sorted(adapters._ADAPTERS) == ["cn"]
    assert sorted(adapters._ADAPTERS["cn"]) == _EXPECTED
    assert adapters._REGIONS == {"cn": "中国"}


def test_every_adapter_module_has_module_level_client():
    # AGENTS.md 铁律：契约测试的模块级 _client 是适配器形态的硬契约
    missing = [f"{region}/{city}"
               for region, by_city in adapters._ADAPTERS.items()
               for city, mod in by_city.items()
               if not hasattr(mod, "_client")]
    assert missing == []


def test_search_docstring_lists_every_registered_city():
    doc = server.search_books.__doc__
    absent = [city for city in _EXPECTED if city not in doc]
    assert absent == []


def test_search_docstring_data_boundaries_match_docs():
    # 与 data-sources/cn.md 各城小节口径一致（2026-10-02 验收基准）
    doc = server.search_books.__doc__
    assert "limit 不生效" in doc                 # 南京：每页固定 20 条
    assert "双源合并" in doc                      # 杭州／合肥
    assert "三源合并" in doc                      # 天津
    assert "保守按不可借展示" in doc               # 重庆：状态原值照登


def test_availability_docstring_due_date_boundaries():
    doc = server.find_book_availability.__doc__
    # 浙图（hangzhou 双源之一）与金华：借出无应还日期＝数据边界非故障
    assert "浙江图书馆源" in doc and "金华源" in doc
    assert "due_date 为空串属数据边界" in doc
    # 重庆保守口径（0.3.0 已上线文案）未被本批改动
    assert "only_available=True 恒为空" in doc


def test_detail_docstring_nanjing_call_number_boundary():
    doc = server.get_book_detail.__doc__
    # 南图源接入后（2026-10-02 双源）无索书号的只剩金陵源与宁波源
    assert "南京金陵源、宁波数据源详情页无索书号字段" in doc
    assert "call_number 为空串" in doc


def test_data_sources_registers_every_adapter():
    # 总览表以反引号标识登记每个已接入城市（AGENTS.md：新城市先在此登记）
    text = _DOCS.read_text(encoding="utf-8")
    absent = [city for city in _EXPECTED if f"`{city}`" not in text]
    assert absent == []
