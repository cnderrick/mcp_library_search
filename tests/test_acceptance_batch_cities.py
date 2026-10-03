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
# ＋来宾（2026-10-03 立项城市落地，图创 Interlib 默认模板＋api_detail）
# ＋第三批 12 城（2026-10-03 立项城市落地，均图创 Interlib＋api_detail；德清/
#   西双版纳 HTML 检索页被拦改走内嵌 Solr）
# ＋第四批 5 城（2026-10-03 立项城市落地）：太原/武汉/大庆（图创 Interlib，
#   太原走内嵌 Solr、大庆上下文为根路径）、枣庄（新版 UILAS REST）、
#   乐山（图创 Interlib pro2018，省图联合目录 f_curlibcode=LS，验证码墙抛
#   CaptchaError 不破解，同天津 ALEPH 口径）
# ＋郑州（2026-10-03 用户提供可访问入口；SirsiDynix Enterprise/VSE，本仓库首见
#   新家族，抽出 sirsi_ent/ 共享模块）
# ＋第五批 9 城（2026-10-03 立项城市落地，均图创 Interlib＋api_detail）：铜陵
#   （默认模板变体：检索页著者/出版社锚点无 link class，家族加文本标签兜底）、
#   安庆、茂名、东营、烟台、潍坊、中山（pro2018）、普宁（solr_search）、
#   揭阳（检索页「opac验证」＋内嵌 Solr 403 bot detected，captcha=True 抛 CaptchaError）
# ＋第六批 10 城（2026-10-03 立项城市落地，均图创 Interlib 默认模板＋api_detail）：
#   泰安/日照/临沂/聊城/石家庄/忻州/四平/齐齐哈尔/牡丹江/三明；同批晋中/莆田
#   域名落 198.20.0.x 停放段，改判不通、不接入
# ＋第七批 10 城（2026-10-03 立项城市落地，均图创 Interlib＋api_detail）：
#   宁德/十堰/鄂州/荆州/黄冈/恩施/湘潭/岳阳/张家界（HTML 检索页直连）；
#   湖北省图书馆 hubei_prov（检索页「opac验证」＋内嵌 Solr 被 bot 检测拦，
#   captcha=True 抛 CaptchaError，详情/馆藏匿名可通，同乐山/揭阳口径）；
#   同批龙岩（opac.lytsg.com→198.20.0.182 停放段）改判不通、开封为老版 GLIS
#   （jdjsjg.jsp，无 /opac/search、无 /opac/api/*）非家族模板，均不接入
# ＋第八批 7 城（2026-10-03 立项城市落地）：安顺/毕节/六盘水/桂林/呼伦贝尔/福州
#   （图创 Interlib 默认模板＋api_detail，福州为福州地区图书馆联合检索平台）；
#   三亚（实抓为图创 tcc-opac，复用 tccopac/ 家族）；同批梧州（198.20.2.213 停放段）、
#   攀枝花（候选 OPAC host 8180 不可达、官网无书目接口）、长沙（整站 WAF 403）改判不通、不接入
# ＋第九批 4 城（2026-10-03 立项城市落地，均老版 UILAS HTML OPAC，复用 uilas/ 家族）：
#   芜湖/六安/通化/贵阳（贵阳应用上下文为根路径）；同批南昌（uopac.nclib.net→
#   198.20.3.17 停放段、HTTP 零字节超时）改判不通、不接入
_EXPECTED = [
    "ankang", "anqing", "anshun", "baoji", "baotou", "bijie", "changchun", "chaozhou",
    "chengdu", "chongqing", "chuxiong", "dalian", "daqing", "dehong",
    "deqing", "dezhou", "dongying", "eerduosi", "enshi", "ezhou",
    "fujian_prov", "fuzhou", "guangzhou", "guilin", "guiyang",
    "haikou", "hangzhou", "hanzhong", "hefei", "heilongjiang", "henan_prov",
    "heyuan", "honghe", "huaian", "huanggang", "huangshi", "hubei_prov",
    "huhehaote", "hulunbuir", "hunan_prov",
    "jiangmen", "jiangyin", "jieyang", "jinan", "jingmen", "jingzhou", "jinhua",
    "laibin", "lanzhou", "leshan", "liaocheng", "lijiang", "lincang",
    "linyi", "lishui", "liupanshui", "luan", "maoming", "mudanjiang", "nanjing", "ningbo", "ningde",
    "nujiang", "puning", "qiandongnan", "qiannan", "qingdao", "qiqihar",
    "quanzhou", "qujing", "rizhao", "sanming", "sanya", "shaanxi", "shanghai",
    "shaoxing", "shenzhen", "shijiazhuang", "shiyan", "siping", "suzhou", "taian",
    "taiyuan", "taizhou", "tangshan", "tianjin", "tonghua", "tongliao", "tongling",
    "weifang", "wenzhou", "wuhai", "wuhan", "wuhu", "wuxi", "xian", "xiangtan",
    "xianyang", "xiaogan", "xinzhou", "xishuangbanna", "xuzhou", "yancheng",
    "yangjiang", "yangzhou", "yantai", "yueyang", "yulin", "zaozhuang",
    "zhangjiajie", "zhengzhou",
    "zhongshan", "zhoukou", "zhoushan", "zhuzhou", "zibo", "zunyi",
]


def test_registry_has_exactly_expected_identifiers():
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
