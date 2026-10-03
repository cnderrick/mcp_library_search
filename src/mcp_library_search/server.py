"""MCP server：城市图书馆馆藏查询——"这本书在哪些馆能借到"。

多城市架构，已接入：上海、广州、杭州（杭图＋浙图双源合并）、深圳、
天津（三源合并）、重庆、合肥（皖图＋合肥市图双源合并）、
南京（金陵图书馆＋12 区馆联合目录 ＋ 南京图书馆双源合并）、金华、江阴、温州、台州、
宁波（全市联合目录）、绍兴（全市联合目录）、成都（成都平原经济区联合目录）、
大连（地区联合目录）、青岛（全市联合目录）、无锡（新吴区图书馆）、
扬州（扬州市图书馆联盟联合目录）、苏州（苏州图书馆）、徐州（徐州市图书馆）、
淮安（淮安市图书馆）、盐城（盐城市图书馆）、丽水（丽水市公共图书馆联合目录）、
舟山（舟山市图书馆）、shaanxi（陕西省图书馆，省级馆馆址西安）、
xian（西安市图书馆，集群平台）、xianyang（咸阳，公共图书馆联盟）、
baoji（宝鸡，集群平台）、ankang（安康）、hanzhong（汉中，全市联合目录含洋县等县馆）、
yulin（榆林）、jinan（济南，tcc-opac 全市联合目录）、eerduosi（鄂尔多斯，tcc-opac）、
lijiang（丽江，全市联合目录含古城区/玉龙/宁蒗/华坪等分馆）。
第二批：海口、株洲、孝感、荆门、湖南图书馆（hunan_prov）、福建省图书馆（fujian_prov）、
阳江、淄博、德州、周口、泉州、通辽、河源、黑龙江省图书馆（heilongjiang）、长春、
唐山、包头、乌海、呼和浩特、潮州（以上图创 Interlib，其中唐山/包头/乌海/呼和浩特/
潮州/黑龙江/长春检索页有滑动验证码改走内嵌 Solr）、兰州（lanzhou）、江门（jiangmen，
新版 UILAS REST）、河南省图书馆（henan_prov，老版 UILAS）、
来宾（laibin）。第三批（均图创 Interlib）：黄石、遵义、黔东南州、黔南州、曲靖、
临沧、楚雄州、红河州、德宏州、怒江州、德清县、西双版纳州（德清/西双版纳检索走内嵌 Solr）、
太原（检索走内嵌 Solr）、武汉、大庆（上下文为根路径）、枣庄（新版 UILAS REST）、
乐山（借四川省图联合目录过滤，检索页为验证码墙、未过码抛 CaptchaError）、
郑州（SirsiDynix Enterprise 服务端渲染）。
tool 与具体城市解耦：先用 search_books 按关键字查到 book_id，
再用它调用 find_book_availability（哪些馆有）或 get_book_detail（完整介绍）。
"""
from importlib.metadata import PackageNotFoundError, version as _pkg_version

from fastmcp import FastMCP

from mcp_library_search import adapters
from mcp_library_search.adapters.base import BookDetail, Holding, SearchPage

try:
    _VERSION = _pkg_version("mcp_library_search")
except PackageNotFoundError:
    _VERSION = "0.0.0+local"  # 源码直跑（包未安装）时兜底

mcp = FastMCP("mcp-library-search", version=_VERSION)


@mcp.tool
def search_books(keyword: str, region: str = "cn", city: str = "shanghai", page: int = 1, limit: int = 20) -> SearchPage:
    """按关键字搜索城市图书馆的馆藏图书，返回分页列表。

    region 为地区标识（取域名后缀），默认 "cn"（中国）；已接入城市均在 cn 下。
    已接入城市：shanghai（上海，全市 900+ 网点，含地铁站 24 小时自助机）、
    guangzhou（广州）、hangzhou（杭州，杭州图书馆＋浙江图书馆双源合并，
    同一本书跨馆归并成一条结果）、shenzhen（深圳，167 馆统一平台）、
    tianjin（天津，主馆＋少儿馆＋中新友好三源合并，同一本书跨馆归并成一条结果）、
    chongqing（重庆，馆藏到单册级；源站无明确「可借」状态词，全部保守按不可借展示，状态原值照登）、
    hefei（合肥，安徽省图书馆＋合肥市图书馆双源合并，同一本书跨馆归并成一条结果）、
    nanjing（南京，金陵图书馆＋12 区馆联合目录 ＋ 南京图书馆双源合并，同一本书
    跨馆归并成一条结果，馆藏到单册级；两源每页条数固定——金陵 20 条、南图 10 条，
    limit 不生效；南图源有验证码墙，被封时按错误提示在浏览器过码解封）、
    jinhua（金华，馆藏到单册级）、jiangyin（江阴，含农家书屋等 24H 网点）、
    wenzhou（温州，全市总分馆体系）、taizhou（台州，全市通借网络含地铁站点）、
    ningbo（宁波，全市联合目录含慈溪/奉化等区县馆与城市书房，馆藏到单册级）、
    shaoxing（绍兴，全市联合目录含上虞等成员馆；联合层书目可能无本地单册，
    馆藏为空属数据边界）、chengdu（成都，成都平原经济区联合目录含德阳/眉山
    等市县馆，馆藏到单册级）、dalian（大连，地区联合目录，会话制检索；源站裸词为逐字
    AND 宽匹配、无相关度，已统一按短语检索下发）、
    qingdao（青岛，全市联合目录含区级馆与城市书房，馆藏到单册级；检索走站点
    内嵌 Solr 通道，结果只含有馆藏的书目，逐书目可借概况为空串属数据边界）、
    wuxi（无锡，无锡市新吴区图书馆单馆，馆藏下沉到街道分馆与社区服务点；
    市图书馆源预留未接入）、
    yangzhou（扬州，扬州市图书馆联盟联合目录，含邗江区馆等成员馆；与南京金陵源
    同属汇文 uopac 家族、页面同构，站点有 securitycam 反爬已按静态挑战处理）、
    suzhou（苏州，苏州图书馆＋苏州工业园区图书馆双源合并，同一本书跨馆归并成一条结果）、
    xuzhou（徐州，全市联合目录含鼓楼区馆等成员馆，馆藏到单册级）、
    huaian（淮安，全市联合目录含少儿馆、清江浦区馆等成员馆，馆藏到单册级）、
    yancheng（盐城，市图书馆单实例，馆藏到单册级）、
    lishui（丽水，全市联合目录含景宁/庆元/缙云等县馆与城市书房）、
    zhoushan（舟山，市图书馆，馆藏到单册级）、
    shaanxi（陕西省图书馆，新版 UILAS REST 平台，省级馆馆址西安）、
    xian（西安市图书馆，西安市公共图书馆集群平台，上下文 /opac3）、
    xianyang（咸阳，公共图书馆联盟）、baoji（宝鸡，集群平台）、
    ankang（安康，详情走 /api/book 接口）、
    hanzhong（汉中，全市联合目录含洋县等县馆）、
    yulin（榆林，新版 UILAS REST 平台）、
    haikou（海口）、zhuzhou（株洲）、xiaogan（孝感）、jingmen（荆门）、
    hunan_prov（湖南图书馆）、fujian_prov（福建省图书馆）、yangjiang（阳江）、
    zibo（淄博）、dezhou（德州）、zhoukou（周口）、quanzhou（泉州）、
    tongliao（通辽）、heyuan（河源）、heilongjiang（黑龙江省图书馆）、
    changchun（长春）、tangshan（唐山）、baotou（包头）、wuhai（乌海）、
    huhehaote（呼和浩特）、chaozhou（潮州）、laibin（来宾市图书馆）（以上图创 Interlib，馆藏到单册级）、
    第三批：huangshi（黄石）、zunyi（遵义）、qiandongnan（黔东南州）、qiannan（黔南州）、
    qujing（曲靖）、lincang（临沧）、chuxiong（楚雄州）、honghe（红河州）、dehong（德宏州）、
    nujiang（怒江州）、deqing（德清县）、xishuangbanna（西双版纳州）（以上图创 Interlib，
    馆藏到单册级；德清/西双版纳检索走内嵌 Solr）、
    第四批：taiyuan（太原市图书馆，检索走内嵌 Solr）、wuhan（武汉图书馆）、
    daqing（大庆市图书馆，应用上下文为根路径）、zaozhuang（枣庄市图书馆，新版 UILAS REST）、
    leshan（乐山市图书馆，借四川省图书馆联合目录按 f_curlibcode=LS 过滤；检索页为
    滑动验证码墙且无内嵌 Solr，未过码时抛 CaptchaError 不破解，同天津 ALEPH 口径）、
    zhengzhou（郑州图书馆，SirsiDynix Enterprise 服务端渲染；每页固定 12 条，limit
    不生效；检索列表 publisher/publish_year 为空串属数据边界）、
    lanzhou（兰州市图书馆）、jiangmen（江门市图书馆）（新版 UILAS REST 平台）、
    henan_prov（河南省图书馆，老版 UILAS HTML OPAC）、
    jinan（济南市图书馆）、eerduosi（鄂尔多斯市图书馆）（图创 tcc-opac 全市联合目录）、
    lijiang（丽江市图书馆，全市联合目录含古城区/玉龙/宁蒗/华坪等分馆），
    其他城市待接入。
    keyword 可以是书名、ISBN、作者名等。每条结果带 book_id，是后续查询的凭据。
    total_results 为 null 表示数据源不提供总数：用 page 继续翻页，
    直到 has_next 为 false 或 books 为空。

    参数：
        keyword：书名、ISBN、作者等检索词
        region：地区标识（域名后缀），默认 "cn"（中国）
        city：城市标识，默认 "shanghai"
        page：页码，默认 1
        limit：每页条数，默认 20
    """
    try:
        return adapters.search_books(region, city, keyword, page=page, limit=limit)
    except Exception as e:
        raise RuntimeError(f"搜索失败：{e}") from e


@mcp.tool
def find_book_availability(book_id: str, region: str = "cn", city: str = "shanghai", only_available: bool = True) -> list[Holding]:
    """查询指定图书在各分馆的馆藏与可借状态，可借的馆排前面。

    已借出的馆藏可能带 due_date（预计归还时间，YYYY-MM-DD），仅在
    only_available=False 时出现；数据源查不到时为空串。
    重庆源站无明确「可借」状态词：only_available=True 恒为空，请用 False
    查看状态原值（入藏/借出等）与应还日期，自行判断。
    浙江图书馆源（hangzhou 双源之一）与金华源的借出馆藏拿不到应还日期
    （due_date 为空串属数据边界，非故障）；杭州图书馆源正常带应还日期。
    扬州源（yangzhou）同样拿不到：源站只给裸「借出」，不含应还日期
    （due_date 为空串属数据边界，非故障）。
    无锡源（wuxi）的检索索引与馆藏端点会不一致：索引计有复本而馆藏端点返回空
    （如实返回空列表，馆藏端点为准），另有部分书目拿不到在架数导致可借概况为空串，
    均属数据边界。

    参数：
        book_id：search_books 返回的图书 ID，需与 search_books 使用同一 region 与 city
        region：地区标识（域名后缀），默认 "cn"（中国）
        city：城市标识，默认 "shanghai"
        only_available：True（默认）只返回当前可借的馆；False 返回全部馆藏
    """
    try:
        return adapters.get_holdings(region, city, book_id, only_available=only_available)
    except Exception as e:
        raise RuntimeError(f"查询馆藏失败：{e}") from e


@mcp.tool
def get_book_detail(book_id: str, region: str = "cn", city: str = "shanghai") -> BookDetail:
    """查询指定图书的完整介绍：书名、作者、出版社、出版年、ISBN、索书号、内容简介。

    上海数据源没有独立简介区块，内容简介取自书目"附注"字段，可能带有
    "新版本册内容："之类的原生前缀。
    南京金陵源、宁波数据源详情页无索书号字段，call_number 为空串（单册索书号在
    馆藏明细里）；南京图书馆源（nanjing 双源之一）有索书号字段，正常返回。
    扬州源（yangzhou）详情页同金陵源无索书号字段，call_number 为空串。
    宁波老书目出版项可能缺失，publisher/publish_year 为空串
    属数据边界。绍兴数据源详情页无「内容提要」标签行，summary 恒为空串
    （数据边界，非故障）。

    参数：
        book_id：search_books 返回的图书 ID，需与 search_books 使用同一 region 与 city
        region：地区标识（域名后缀），默认 "cn"（中国）
        city：城市标识，默认 "shanghai"
    """
    try:
        return adapters.get_book_detail(region, city, book_id)
    except Exception as e:
        raise RuntimeError(f"查询图书详情失败：{e}") from e


def main() -> None:
    """console script 入口：`uvx mcp_library_search` 即以此启动 stdio 服务。"""
    mcp.run()


if __name__ == "__main__":
    main()
