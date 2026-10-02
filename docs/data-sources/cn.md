# 中国数据源清单（cn）

> 本文是 data-sources 总目录下的中国分卷；总目录与各国家分卷的关系见 [README.md](README.md)。

各城市图书馆的线上入口、系统技术组件与接入要点。**新增城市先在总览表登记一行**，接入要点写进对应的「接入系统」章；一个系统对多座城的，城市差异收在该章的城市表里。

> 引用约定：本文与 `tests/fixtures/*/NOTES.md` 中出现的 `docs/team/research/*.md` 调研笔记为**本地存档**（`.git/info/exclude` 排除，不随仓库分发）；各笔记的关键结论均已照实摘录进本文对应条目与 NOTES.md，外部读者无需原文即可理解全部登记依据。

> 地区维度：MCP 的 `region` 参数取域名后缀（ccTLD），默认 `cn`（中国）。本表所录站点均为 `.cn` 域名，故全部归在 `cn` 地区；将来接入其他后缀的站点时，先在该地区下登记城市，再按家族或独立实现接入。

## 总览

同一省份的城市排在一起，省份列只在该省首行填写（视觉上等同于合并单元格），新增城市时接在本省行之后。同一城市的多座馆（省馆＋市馆等）接在该城行之后，城市列只在该城首行填写，具体馆名随入口地址注明。表序分三段：直辖市在前、省居中、自治区殿后。

总览含两批补入的未接入城市：一批自《全国公共图书馆OPAC查询地址清单》照登（城市与馆名原样），另一批按**地级行政区名册**补全（地级市＋自治州＋地区＋盟；只登城市名，入口缺失）。两批的标识、技术组件、适配层均留空待侦察。部分条目存在清单本身的张冠李戴（同一域名被安到多座城市），未作改写，以实测结果为准。

状态列标识：✅ 接入＝全链路实网跑通；⚠️ 部分接入＝链路有环节待修；⛔ 不通＝站点侧拦截、不可达，或实测已被域名停放/无关站点占用；🚧 攻关＝已侦察、待攻克；📋 计划＝可接入、待立项；🔍 待核验＝首页实测可达、OPAC 未侦察；❓ 缺失＝名册内城市尚无任何登记（入口缺失）。

| 省份 | 城市 | 标识 | 状态 | 线上图书馆入口 | 技术组件 | 适配层位置 |
|---|---|---|---|---|---|---|
| 上海市（直辖市） | 上海 | `shanghai` | ✅ 接入 | https://vufind.library.sh.cn | VuFind（上海中心图书馆"一卡通"总分馆体系，900+ 网点） | `vendor/shanghai_library/` + `adapters/cn/shanghai.py` |
| 北京市（直辖市） | 北京 | — | ⛔ 不通 | https://primo.clcn.net.cn/ （首都图书馆） | Ex Libris Primo classic（整域名网宿 WAF：HTTP 200＋33KB JS 验证页，覆盖 80/443/1701 三端口与三类 API；主站与 bplisn.net.cn 均无独立检索后端，表单全部外链 Primo） | 🔜 搁置：WAF 拦截程序化访问、无替代入口 |
|  |  | — | 🚧 攻关 | http://opac.nlc.cn/F/ （国家图书馆） | Ex Libris ALEPH 5.20（与天津同款家族；检索码 NLC01/NLC09；仅 HTTP，HTTPS 不通） | 🔍 待定：首页可达，但同 IP 连续请求触发 empty reply、需冷却 ≥20 秒，find-m 结果页未走通；需 ≥30 秒/请求的冷启动全流程稳定性验证，通过可照天津 ALEPH 经验接入 |
| 天津市（直辖市） | 天津 | `tianjin` | ✅ 接入 | http://opacwh.tjl.tj.cn:8991/F （主馆） | Ex Libris ALEPH 20.1 www_f_chi | `adapters/cn/tianjin.py`（三源合并） |
|  |  |  | ✅ 接入 | http://opacse.tjl.tj.cn:8991/F （少儿馆） | 同款 ALEPH（独立 host 独立 base） |  |
|  |  |  | ✅ 接入 | http://sm.interlib.cn:8104 （中新友好） | 图创 Interlib（租户 STC001） |  |
| 重庆市（直辖市） | 重庆 | `chongqing` | ✅ 接入 | http://222.177.237.197:8080/InDigLib/frontV2/SearchIndex!simple.action?opacType=local | InDigLib 集群数字图书馆（Struts2+Solr） | `adapters/cn/chongqing.py`（独立实现） |
| 安徽省 | 合肥 | `hefei` | ✅ 接入 | https://opac.ahlib.com/opac/index （安徽省图书馆） | 图创 Interlib（已确认，与穗杭完全同模板） | `interlib/` 家族 + `adapters/cn/hefei.py`（双源合并：皖图 `AH:` ＋ 市图 `HF:`，天津口径） |
|  |  |  | ✅ 接入 | https://opac.hflib.org.cn/lib2/ （合肥市图书馆） | 图创 Interlib（已确认，同模板；应用上下文是 `/lib2` 非 `/opac`，`/opac/*` 返回 nginx 500） |  |
|  | 芜湖 | — | ⛔ 不通 | http://www.whlib.net （芜湖市图书馆） | — | — |
|  | 蚌埠 | — | ⛔ 不通 | http://www.bblib.net （蚌埠市图书馆） | — | — |
|  | 淮南 | — | ⛔ 不通 | http://www.hnlib.net （淮南市图书馆） | — | — |
|  | 马鞍山 | — | ⛔ 不通 | http://www.maslib.net （马鞍山市图书馆） | — | — |
|  | 淮北 | — | ⛔ 不通 | http://www.hblib.net （淮北市图书馆） | — | — |
|  | 铜陵 | — | ⛔ 不通 | http://www.tllib.net （铜陵市图书馆） | — | — |
|  | 安庆 | — | ⛔ 不通 | http://www.aqlib.net （安庆市图书馆） | — | — |
|  | 黄山 | — | ⛔ 不通 | http://www.hslib.net （黄山市图书馆） | — | — |
|  | 滁州 | — | ⛔ 不通 | http://www.czlib.net （滁州市图书馆） | — | — |
|  | 阜阳 | — | ⛔ 不通 | http://www.fylib.net （阜阳市图书馆） | — | — |
|  | 宿州 | — | ⛔ 不通 | http://www.szlib.net （宿州市图书馆） | — | — |
|  | 六安 | — | ⛔ 不通 | http://www.lalib.net （六安市图书馆） | — | — |
|  | 亳州 | — | ⛔ 不通 | http://www.bzlib.net （亳州市图书馆） | — | — |
|  | 池州 | — | ⛔ 不通 | http://www.czlib.net （池州市图书馆） | — | — |
|  | 宣城 | — | ⛔ 不通 | http://www.xclib.net （宣城市图书馆） | — | — |
| 广东省 | 广州 | `guangzhou` | ✅ 接入 | https://opac.gzlib.org.cn | 图创 Interlib | `interlib/` 家族 + `adapters/cn/guangzhou.py` |
|  | 深圳 | `shenzhen` | ✅ 接入 | https://www.szlib.org.cn/opac/ | 图书馆之城自研 JSON API（后端 ILAS，167 馆统一平台） | `adapters/cn/shenzhen.py`（独立实现） |
|  | 韶关 | — | ⛔ 不通 | http://www.sglib.net （韶关市图书馆） | — | — |
|  | 珠海 | — | ⛔ 不通 | http://www.zhlib.net （珠海市图书馆） | — | — |
|  | 汕头 | — | ⛔ 不通 | http://www.stlib.net （汕头市图书馆） | — | — |
|  | 佛山 | — | ⛔ 不通 | http://www.fslib.net （佛山市图书馆） | — | — |
|  | 江门 | — | 🔍 待核验 | http://www.jmlib.net （江门市图书馆） | — | — |
|  | 湛江 | — | ⛔ 不通 | http://www.zjlib.net （湛江市图书馆） | — | — |
|  | 茂名 | — | ⛔ 不通 | http://www.mmlib.net （茂名市图书馆） | — | — |
|  | 肇庆 | — | ⛔ 不通 | http://www.zqlib.net （肇庆市图书馆） | — | — |
|  | 惠州 | — | ⛔ 不通 | http://www.hzlib.net （惠州市图书馆） | — | — |
|  | 梅州 | — | ⛔ 不通 | http://www.mzlib.net （梅州市图书馆） | — | — |
|  | 汕尾 | — | ⛔ 不通 | http://www.swlib.net （汕尾市图书馆） | — | — |
|  | 河源 | — | ⛔ 不通 | http://www.hylib.net （河源市图书馆） | — | — |
|  | 阳江 | — | 🔍 待核验 | http://www.yjlib.net （阳江市图书馆） | — | — |
|  | 清远 | — | ⛔ 不通 | http://www.qylib.net （清远市图书馆） | — | — |
|  | 东莞 | — | ⛔ 不通 | http://www.dglib.net （东莞图书馆） | — | — |
|  | 中山 | — | ⛔ 不通 | http://www.zslib.net （中山市图书馆） | — | — |
|  | 潮州 | — | ⛔ 不通 | http://www.czlib.net （潮州市图书馆） | — | — |
|  | 揭阳 | — | ⛔ 不通 | http://www.jylib.net （揭阳市图书馆） | — | — |
|  | 云浮 | — | ⛔ 不通 | http://www.yflib.net （云浮市图书馆） | — | — |
| 江苏省 | 南京 | `nanjing` | ✅ 接入 | http://uopac.jllib.cn/uopac/s/search.action （金陵图书馆联合目录，金陵运营，覆盖金陵＋12 区馆） | 汇文 uopac 区域联合 OPAC（Struts2；金陵自研 PHP OPAC `opac.jllib.cn/opac/*` 整体登录墙不可用，勿当入口） | `uopac/` 家族 + `adapters/cn/nanjing.py`（双源合并：金陵 `JL:` ＋ 南图 `NJL01:`，天津口径；金陵源解析走 uopac 家族、与扬州共用，原生数字 book_id 现带 `JL:` 前缀、裸数字走兼容垫片；源站偶发 chunked 停顿，已按 NOTES 口径重试一次） |
|  |  |  | ✅ 接入 | https://opac.jslib.org.cn/F/ （南京图书馆/江苏省图） | Ex Libris ALEPH `u20_1 / www_f_chi`（外层 openresty 全局验证码墙；**按 host 独立封禁**，解南图不解天津） | `aleph/` 家族原语 ＋ `adapters/cn/nanjing.py`（南图源，`item_global_all_params=True`）；2026-10-02 全链路实网跑通，库代码表·两处坑与家族兼容性证据见 `tests/fixtures/nanjing_prov/NOTES.md` |
|  | 扬州 | `yangzhou` | ✅ 接入 | http://ytlmopac.cn:8080/uopac/s/search.action （扬州市图书馆联盟联合目录，含邗江区馆等成员馆） | 汇文 Libsys/uopac（Struts2，与金陵同系统；全路径 securitycam 静态挑战） | `uopac/` 家族 + `adapters/cn/yangzhou.py`；壳页 key/IV/密文为硬编码常量、cookie 恒定（解出值见 NOTES），故直接带常量 cookie，无需 JS 引擎；常量轮换由家族 HTTP 层认出壳页抛错，不静默空结果 |
|  | 江阴 | `jiangyin` | ✅ 接入 | http://libopac.jylib.cn:9090/opac/index | 图创 Interlib（已确认，与广州同模板、零 quirk，自建单租户） | `interlib/` 家族 + `adapters/cn/jiangyin.py` |
|  | 无锡 | `wuxi` | ✅ 接入 | http://wxxqlsp.xw.i-wnd.cn:8013/#/home （新吴区图书馆，单馆） | 图星 LibStar Find v3.2023.12（北京图星/超星系，JSON API） | `libstar/` 家族 + `adapters/cn/wuxi.py`；市图书馆源按天津口径预留（源码 `WXST`，未接入）。**两处必需请求头缺一不可：`Referer`（任意值即可，缺失时全部内容端点回 `errCode:9999`「系统访问中断」，极易误判为服务端故障）与 `groupcode: 800507`（缺失则 HTTP 200 但静默 0 结果）** |
|  |  | — | ⛔ 不通 | http://222.191.248.124:8088/opac/book_cart.php （无锡市图书馆旧 OPAC） | — | 2026-10-03 实测 8088 端口空响应、同 IP 80 端口仅 Tomcat 默认 404；官网 www.wxlib.cn 仍指向该 8088 旧 OPAC，暂无可用检索入口，市图源 `WXST` 继续搁置 |
|  | 苏州 | `suzhou` | ✅ 接入 | https://reader.szlib.com/opac/index （苏州图书馆，页标题「检索系统」，全市集群目录） | 图创 Interlib（已确认：页内自报图创／interlib、`/opac/media/*`、`bookrecno`；2026-10-03 实抓「三体」232 条、24 页） | `interlib/` 家族 + `adapters/cn/suzhou.py`（默认模板零 quirk，不需要 `curlibcode`） |
|  |  | — | 🔍 待核验 | http://opac.sdll.cn:8088/opac （苏州工业园区图书馆） | — | — |
|  | 徐州 | `xuzhou` | ✅ 接入 | https://findxz.libsp.com （徐州市图书馆，同名多分馆含鼓楼区馆等） | 图星 LibStar Find（与无锡新吴同款，JSON API） | `libstar/` 家族 + `adapters/cn/xuzhou.py`；`groupCode=3203001001`（与主馆 libCode 同）。检索须带 `Referer`＋`groupcode` 头，缺 `groupcode` 静默 0 结果；实抓「三体」407 条 |
|  | 常州 | — | ⛔ 不通 | http://www.czlib.net （常州市图书馆） | — | 2026-10-03 实测域名解析到 198.20.x.x 域名停放段、TCP 空响应，非馆方站点；近似域名 czlib.cn＝潮州市图书馆，亦非本市，未找到可用检索入口 |
|  | 南通 | — | ⛔ 不通 | https://www.ntlib.org.cn （南通市图书馆） | — | 2026-10-03 实测 `www.ntlib.org.cn`（58.221.24.12）TLS 握手直接 EOF，裸 `ntlib.org.cn` 302 指回 www 形成循环；原登记 `www.ntlib.net` 落在 198.20.x.x 域名停放段，均无可用检索入口 |
|  | 连云港 | — | 🔍 待核验 | https://4366ha.mh.chaoxing.com/entry/page/ck/peking_library （连云港市图书馆，超星智慧门户） | 超星智慧门户（wisweb／chaoxing 系） | 用户所给入口 `…/entry/global/offline` 实测显示「系统升级中」；门户页本身 HTTP 200，底层书目检索入口未侦察 |
|  | 淮安 | `huaian` | ✅ 接入 | https://findhastsg.pub.chaoxing.com （淮安市图书馆，含少儿馆、清江浦区馆等） | 图星 LibStar Find（与无锡新吴同款，JSON API） | `libstar/` 家族 + `adapters/cn/huaian.py`；`groupCode=100382`。检索须带 `Referer`＋`groupcode` 头；实抓「三体」3110 条 |
|  | 盐城 | — | 📋 计划 | https://findyctsg.libsp.com （盐城市图书馆） | 图星 LibStar Find（与无锡新吴同款，JSON API） | `adapters/cn/wuxi.py` 协议可复用；`groupCode=100026`。检索须带 `groupcode` 头；待立项 |
|  | 镇江 | — | ⛔ 不通 | http://www.zjlib.net （镇江市图书馆） | — | — |
|  | 泰州 | — | ⛔ 不通 | http://www.tzlib.com （泰州市图书馆） | — | 2026-10-03 实测域名解析到 198.20.x.x 域名停放段、TCP 空响应；原登记 www.tzlib.net 实为「滕州图书馆」（山东），tzlib.cn 实为「台州市图书馆」（浙江），均非本市，未找到可用检索入口 |
|  | 宿迁 | — | 🔍 待核验 | https://sqstsg.mh.chaoxing.com （宿迁市图书馆，超星智慧门户） | 超星智慧门户（wisweb／chaoxing 系） | 门户页 HTTP 200，底层书目检索入口未侦察 |
| 辽宁省 | 大连 | `dalian` | ✅ 接入 | 超星入口 http://www.dl.superlib.net/ （搁置）；**在用入口** http://ykt.dl-library.net.cn/ （大连地区网上联合目录） | SirsiDynix iLink（`/uhtbin/cgisirsi/`，本仓库首见新家族，与成都不同家族不共享模块）；原超星入口 IP 白名单硬墙 | `adapters/cn/dalian.py`（独立实现；ps token＋会话 cookie 每请求变、全程同 cookie jar，类重庆会话流程；节流 ≥4 秒/host）。**检索语义**：裸词是逐字 AND 宽匹配、无相关度排序（所有字段「三体」实测 27944 条），**ASCII 双引号才是短语检索**（「"三体"」132 条）——适配器一律按短语下发，0 命中或源站拒答（含罗马数字等索引不收字符回 Error 页）时退回裸词；详情靠题名候选梯度重检索定位（短语截断题名起，命中多于首页时逐页翻找，VIEW 用全局序号）。2026-10-02 实网验收：检索、详情、馆藏全链路跑通 |
|  | 沈阳 | — | ⛔ 不通 | http://www.lnlib.com （辽宁省图书馆） | — | — |
|  |  | — | ⛔ 不通 | http://www.sylib.net/sylib/index （沈阳市图书馆） | — | — |
|  | 鞍山 | — | ⛔ 不通 | http://www.aslib.net （鞍山市图书馆） | — | — |
|  | 抚顺 | — | ⛔ 不通 | http://www.fslib.net （抚顺市图书馆） | — | — |
|  | 本溪 | — | ⛔ 不通 | http://www.bxlib.net （本溪市图书馆） | — | — |
|  | 丹东 | — | ⛔ 不通 | http://www.ddlib.net （丹东市图书馆） | — | — |
|  | 锦州 | — | ⛔ 不通 | http://www.jzlib.net （锦州市图书馆） | — | — |
|  | 营口 | — | ⛔ 不通 | http://www.yklib.net （营口市图书馆） | — | — |
|  | 阜新 | — | ⛔ 不通 | http://www.fxlib.net （阜新市图书馆） | — | — |
|  | 辽阳 | — | ⛔ 不通 | http://www.lylib.net （辽阳市图书馆） | — | — |
|  | 盘锦 | — | ⛔ 不通 | http://www.pjlib.net （盘锦市图书馆） | — | — |
|  | 铁岭 | — | ⛔ 不通 | http://www.tllib.net （铁岭市图书馆） | — | — |
|  | 朝阳 | — | ⛔ 不通 | http://www.cylib.net （朝阳市图书馆） | — | — |
|  | 葫芦岛 | — | ⛔ 不通 | http://www.hldlib.net （葫芦岛市图书馆） | — | — |
| 山东省 | 青岛 | `qingdao` | ✅ 接入 | http://124.129.202.157/opac/index | 图创 Interlib（站点自报「青岛市公共图书馆联合目录」，26 馆联合含区级馆与城市书房，主馆馆码 QT） | `interlib/` 家族 ＋ `adapters/cn/qingdao.py`（检索走站点内嵌 Solr 后端 `/opac/api/search`，`wt=json`＋`q`/`rows`/`page`，主站 HTML 检索页 `/opac/search` 仍被滑动验证码常态拦截；自带 ≥2 秒节流）；数据边界：Solr 默认只回有馆藏的书目、逐书目可借概况为空串 |
|  | 济南 | — | ⛔ 不通 | http://www.sdlib.com （山东省图书馆） | — | — |
|  |  | — | 🔍 待核验 | http://www.jnlib.net.cn （济南市图书馆） | — | — |
|  | 淄博 | — | ⛔ 不通 | http://www.zblib.net （淄博市图书馆） | — | — |
|  | 枣庄 | — | 🔍 待核验 | http://www.zzlib.net （枣庄市图书馆） | — | — |
|  | 东营 | — | ⛔ 不通 | http://www.dylib.net （东营市图书馆） | — | — |
|  | 烟台 | — | ⛔ 不通 | http://www.ytlib.net （烟台市图书馆） | — | — |
|  | 潍坊 | — | ⛔ 不通 | http://www.wflib.net （潍坊市图书馆） | — | — |
|  | 济宁 | — | ⛔ 不通 | http://www.jnlib.net （济宁市图书馆） | — | — |
|  | 泰安 | — | ⛔ 不通 | http://www.talib.net （泰安市图书馆） | — | — |
|  | 威海 | — | ⛔ 不通 | http://www.whlib.net （威海市图书馆） | — | — |
|  | 日照 | — | ⛔ 不通 | http://www.rzlib.net （日照市图书馆） | — | — |
|  | 临沂 | — | ⛔ 不通 | http://www.lylib.net （临沂市图书馆） | — | — |
|  | 德州 | — | ⛔ 不通 | http://www.dzlib.net （德州市图书馆） | — | — |
|  | 聊城 | — | ⛔ 不通 | http://www.lclib.net （聊城市图书馆） | — | — |
|  | 滨州 | — | ⛔ 不通 | http://www.bzlib.net （滨州市图书馆） | — | — |
|  | 菏泽 | — | ⛔ 不通 | http://www.hzlib.net （菏泽市图书馆） | — | — |
| 四川省 | 成都 | `chengdu` | ✅ 接入 | https://opac.cdclib.cn/opac/index （成都市公共图书馆联合书目检索；原超星入口 books.gdlink.net.cn IP 白名单硬墙仍搁置） | 图创 Interlib（已确认，pro2018 模板代 simple 皮肤；meta keywords 自报图创 interlib） | `interlib/` 家族 ＋ `adapters/cn/chengdu.py`（`pro2018=True` 启用家族 pro2018 解析；自带 ≥2 秒节流） |
|  | 自贡 | — | ❓ 缺失 | — | — | — |
|  | 攀枝花 | — | ❓ 缺失 | — | — | — |
|  | 泸州 | — | ❓ 缺失 | — | — | — |
|  | 德阳 | — | ❓ 缺失 | — | — | — |
|  | 绵阳 | — | ❓ 缺失 | — | — | — |
|  | 广元 | — | ❓ 缺失 | — | — | — |
|  | 遂宁 | — | ❓ 缺失 | — | — | — |
|  | 内江 | — | ❓ 缺失 | — | — | — |
|  | 乐山 | — | ❓ 缺失 | — | — | — |
|  | 南充 | — | ❓ 缺失 | — | — | — |
|  | 眉山 | — | ❓ 缺失 | — | — | — |
|  | 宜宾 | — | ❓ 缺失 | — | — | — |
|  | 广安 | — | ❓ 缺失 | — | — | — |
|  | 达州 | — | ❓ 缺失 | — | — | — |
|  | 雅安 | — | ❓ 缺失 | — | — | — |
|  | 巴中 | — | ❓ 缺失 | — | — | — |
|  | 资阳 | — | ❓ 缺失 | — | — | — |
|  | 阿坝 | — | ❓ 缺失 | — | — | — |
|  | 甘孜 | — | ❓ 缺失 | — | — | — |
|  | 凉山 | — | ❓ 缺失 | — | — | — |
| 浙江省 | 杭州 | `hangzhou` | ✅ 接入 | https://my1.zjhzlib.cn （杭州图书馆） | 图创 Interlib（与广州同模板） | `interlib/` 家族 ＋ `adapters/cn/hangzhou.py`（双源合并，杭图 `HZ:`） |
|  |  |  | ✅ 接入 | https://www.zjlib.cn/ （浙江图书馆，BFF 网关 `/bff-api/`） | 自研微服务（已确认；Nuxt 3＋Java/Spring＋ES，纯 JSON、无需鉴权；省级馆，6 馆区） | `adapters/cn/_zjlib.py`（浙图 `ZJ:`，天津模式并入 `hangzhou`） |
|  | 宁波 | `ningbo` | ✅ 接入 | https://opac.nblib.cn/999 | 图创 tcc-opac（已确认；Java/Spring＋Vue2 SPA，纯 JSON＋JWT 访客令牌，与 Interlib 不同产品线，不可复用家族） | `adapters/cn/ningbo.py`（独立实现；真实检索端点为 `POST /search/` 尾斜杠形态——`bookSearch` 是开放平台端点、参数形态不同且长期「系统异常」，勿混用；检索须传 `hasholding=1`＝只看有馆藏，`0` 是聚合条目所在的空壳子集）；数据边界：馆藏一页 500 册封顶 |
|  | 温州 | `wenzhou` | ✅ 接入 | https://opac3.wzlib.cn/opac/index | 图创 Interlib（已确认，与广州同模板；站点为温州市图书馆，全市总分馆 91 馆） | `interlib/` 家族 + `adapters/cn/wenzhou.py` |
|  | 绍兴 | `shaoxing` | ✅ 接入 | https://opac.sxlib.com/opac/index | 图创 Interlib（已确认，pro2018 模板代；「绍兴市公共图书馆联合目录」，主馆绍兴图书馆） | `interlib/` 家族 ＋ `adapters/cn/shaoxing.py`（`pro2018=True`＋`pro2018_cite_author=True` 启用家族解析与引文块责任者兜底） |
|  | 台州 | `taizhou` | ✅ 接入 | https://opac.tzlib.cn:8182/opac/index | 图创 Interlib（已确认，pro2018 新版模板变体；台州市图书馆，浙江地级市馆，含 S1 线地铁站等全市通借网点） | `interlib/` 家族 ＋ `adapters/cn/taizhou.py`（`pro2018=True` 启用家族 pro2018 解析） |
|  | 金华 | `jinhua` | ✅ 接入 | http://202.101.180.43/ILASOPAC/Index?target=0 | UILAS 知识检索平台（ILAS 系 HTML OPAC，Tomcat/JSP，与深圳的自研 JSON API 封装不同，不可复用） | `adapters/cn/jinhua.py`（独立实现，HTML 解析，匿名全链路）；数据边界：借出无应还日期、裸 IP 仅 HTTP（443 证书过期）、详情页最大 870KB |
|  | 湖州 | — | ⛔ 不通 | http://www.hzlib.net （湖州市图书馆） | — | — |
|  | 嘉兴 | — | ⛔ 不通 | http://www.jxlib.net （嘉兴市图书馆） | — | — |
|  | 舟山 | — | ⛔ 不通 | http://www.zslib.net （舟山市图书馆） | — | — |
|  | 衢州 | — | ⛔ 不通 | http://www.qzlib.net （衢州市图书馆） | — | — |
|  | 丽水 | — | ⛔ 不通 | http://www.lslib.net （丽水市图书馆） | — | — |
| 河北省 | 石家庄 | — | ⛔ 不通 | http://www.helib.net （河北省图书馆） | — | — |
|  |  | — | ⛔ 不通 | http://www.sjzlib.cn （石家庄市图书馆） | — | — |
|  | 唐山 | — | 🔍 待核验 | http://www.tslib.net （唐山市图书馆） | — | — |
|  | 秦皇岛 | — | ⛔ 不通 | http://www.qhdlib.com （秦皇岛市图书馆） | — | — |
|  | 保定 | — | ⛔ 不通 | http://www.bdlib.net （保定市图书馆） | — | — |
|  | 邯郸 | — | ⛔ 不通 | http://www.hdlib.net （邯郸市图书馆） | — | — |
|  | 张家口 | — | ⛔ 不通 | http://www.zjklib.com （张家口市图书馆） | — | — |
|  | 承德 | — | ⛔ 不通 | http://www.cdlib.net （承德市图书馆） | — | — |
|  | 沧州 | — | ⛔ 不通 | http://www.czlib.net （沧州市图书馆） | — | — |
|  | 廊坊 | — | ⛔ 不通 | http://www.lflib.net （廊坊市图书馆） | — | — |
|  | 衡水 | — | ⛔ 不通 | http://www.hslib.net （衡水市图书馆） | — | — |
|  | 邢台 | — | ⛔ 不通 | http://www.xtlib.net （邢台市图书馆） | — | — |
| 山西省 | 太原 | — | 🔍 待核验 | https://lib.sx.cn （山西省图书馆） | — | — |
|  |  | — | ⛔ 不通 | https://www.tylib.org （太原市图书馆） | — | — |
|  | 大同 | — | ⛔ 不通 | http://www.dtlib.net （大同市图书馆） | — | — |
|  | 长治 | — | ⛔ 不通 | http://www.czlib.net （长治市图书馆） | — | — |
|  | 晋城 | — | ⛔ 不通 | http://www.jclib.net （晋城市图书馆） | — | — |
|  | 吕梁 | — | ⛔ 不通 | http://www.lllib.net （吕梁市图书馆） | — | — |
|  | 忻州 | — | ⛔ 不通 | http://www.xzlib.net （忻州市图书馆） | — | — |
|  | 朔州 | — | ⛔ 不通 | http://www.szlib.net （朔州市图书馆） | — | — |
|  | 阳泉 | — | ⛔ 不通 | http://www.yqlib.net （阳泉市图书馆） | — | — |
|  | 晋中 | — | ⛔ 不通 | http://www.jzlib.net （晋中市图书馆） | — | — |
|  | 运城 | — | ⛔ 不通 | http://www.yclib.net （运城市图书馆） | — | — |
|  | 临汾 | — | ⛔ 不通 | http://www.lflib.net （临汾市图书馆） | — | — |
| 吉林省 | 长春 | — | ⛔ 不通 | https://www.jllib.com （吉林省图书馆） | — | — |
|  |  | — | 🔍 待核验 | http://www.ccelib.cn （长春市图书馆） | — | — |
|  | 吉林 | — | ⛔ 不通 | http://www.jllib.net （吉林市图书馆） | — | — |
|  | 四平 | — | ⛔ 不通 | http://www.splib.net （四平市图书馆） | — | — |
|  | 辽源 | — | ⛔ 不通 | http://www.lylib.net （辽源市图书馆） | — | — |
|  | 通化 | — | ⛔ 不通 | http://www.thlib.net （通化市图书馆） | — | — |
|  | 白山 | — | ⛔ 不通 | http://www.bslib.net （白山市图书馆） | — | — |
|  | 松原 | — | ⛔ 不通 | http://www.sylib.net （松原市图书馆） | — | — |
|  | 白城 | — | ⛔ 不通 | http://www.bclib.net （白城市图书馆） | — | — |
|  | 延边 | — | ❓ 缺失 | — | — | — |
| 黑龙江省 | 哈尔滨 | — | 🔍 待核验 | http://www.hljlib.org.cn （黑龙江省图书馆） | — | — |
|  | 齐齐哈尔 | — | ⛔ 不通 | http://www.qqhrlib.net （齐齐哈尔市图书馆） | — | — |
|  | 鸡西 | — | ⛔ 不通 | http://www.jxlib.net （鸡西市图书馆） | — | — |
|  | 鹤岗 | — | ⛔ 不通 | http://www.hglib.net （鹤岗市图书馆） | — | — |
|  | 双鸭山 | — | ⛔ 不通 | http://www.syslib.net （双鸭山市图书馆） | — | — |
|  | 大庆 | — | 🔍 待核验 | http://www.dqlib.net （大庆市图书馆） | — | — |
|  | 伊春 | — | ⛔ 不通 | http://www.yclib.net （伊春市图书馆） | — | — |
|  | 佳木斯 | — | ⛔ 不通 | http://www.jmslib.net （佳木斯市图书馆） | — | — |
|  | 七台河 | — | ⛔ 不通 | http://www.qthlib.net （七台河市图书馆） | — | — |
|  | 牡丹江 | — | ⛔ 不通 | http://www.mdjlib.net （牡丹江市图书馆） | — | — |
|  | 黑河 | — | ⛔ 不通 | http://www.hhlib.net （黑河市图书馆） | — | — |
|  | 绥化 | — | ⛔ 不通 | http://www.shlib.net （绥化市图书馆） | — | — |
|  | 大兴安岭 | — | ⛔ 不通 | http://www.dxallib.net （大兴安岭地区图书馆） | — | — |
| 福建省 | 福州 | — | 🔍 待核验 | http://www.fjlib.net （福建省图书馆） | — | — |
|  |  | — | 🔍 待核验 | https://www.fzlib.org （福州市图书馆） | — | — |
|  | 厦门 | — | ⛔ 不通 | https://www.xmlib.net （厦门市图书馆） | — | — |
|  | 莆田 | — | ⛔ 不通 | http://www.ptlib.net （莆田市图书馆） | — | — |
|  | 三明 | — | ⛔ 不通 | http://www.smlib.net （三明市图书馆） | — | — |
|  | 泉州 | — | ⛔ 不通 | http://www.qzlib.net （泉州市图书馆） | — | — |
|  | 漳州 | — | 🔍 待核验 | http://www.zzlib.net （漳州市图书馆） | — | — |
|  | 南平 | — | ⛔ 不通 | http://www.nplib.net （南平市图书馆） | — | — |
|  | 龙岩 | — | ⛔ 不通 | http://www.lylib.net （龙岩市图书馆） | — | — |
|  | 宁德 | — | ⛔ 不通 | http://www.ndlib.net （宁德市图书馆） | — | — |
| 江西省 | 南昌 | — | ⛔ 不通 | https://www.jxlibrary.net （江西省图书馆） | — | — |
|  |  | — | ⛔ 不通 | http://www.nclib.net （南昌市图书馆） | — | — |
|  | 萍乡 | — | ⛔ 不通 | http://www.pxlib.net （萍乡市图书馆） | — | — |
|  | 九江 | — | ⛔ 不通 | http://www.jjlib.net （九江市图书馆） | — | — |
|  | 新余 | — | ⛔ 不通 | http://www.xylib.net （新余市图书馆） | — | — |
|  | 鹰潭 | — | ⛔ 不通 | http://www.ytlib.net （鹰潭市图书馆） | — | — |
|  | 赣州 | — | ⛔ 不通 | http://www.gzlib.net （赣州市图书馆） | — | — |
|  | 吉安 | — | ⛔ 不通 | http://www.jalib.net （吉安市图书馆） | — | — |
|  | 宜春 | — | ⛔ 不通 | http://www.yclib.net （宜春市图书馆） | — | — |
|  | 抚州 | — | ⛔ 不通 | http://www.fzlib.net （抚州市图书馆） | — | — |
|  | 上饶 | — | ⛔ 不通 | http://www.srlib.net （上饶市图书馆） | — | — |
|  | 景德镇 | — | ❓ 缺失 | — | — | — |
| 河南省 | 郑州 | — | 🔍 待核验 | https://www.henanlib.com （河南省图书馆） | — | — |
|  |  | — | 🔍 待核验 | https://www.zzlib.org.cn （郑州图书馆） | — | — |
|  | 开封 | — | ⛔ 不通 | http://www.kflib.net （开封市图书馆） | — | — |
|  | 洛阳 | — | ⛔ 不通 | http://www.lylib.net （洛阳市图书馆） | — | — |
|  | 平顶山 | — | ⛔ 不通 | http://www.pdslib.net （平顶山市图书馆） | — | — |
|  | 安阳 | — | ⛔ 不通 | http://www.aylib.net （安阳市图书馆） | — | — |
|  | 鹤壁 | — | ⛔ 不通 | http://www.hblib.net （鹤壁市图书馆） | — | — |
|  | 新乡 | — | ⛔ 不通 | http://www.xxlib.net （新乡市图书馆） | — | — |
|  | 焦作 | — | ⛔ 不通 | http://www.jzlib.net （焦作市图书馆） | — | — |
|  | 濮阳 | — | ⛔ 不通 | http://www.pylib.net （濮阳市图书馆） | — | — |
|  | 许昌 | — | ⛔ 不通 | http://www.xclib.net （许昌市图书馆） | — | — |
|  | 漯河 | — | ⛔ 不通 | http://www.lhlib.net （漯河市图书馆） | — | — |
|  | 三门峡 | — | ⛔ 不通 | http://www.smxlib.net （三门峡市图书馆） | — | — |
|  | 南阳 | — | ⛔ 不通 | http://www.nylib.net （南阳市图书馆） | — | — |
|  | 商丘 | — | ⛔ 不通 | http://www.sqlib.net （商丘市图书馆） | — | — |
|  | 信阳 | — | ⛔ 不通 | http://www.xylib.net （信阳市图书馆） | — | — |
|  | 周口 | — | ⛔ 不通 | http://www.zklib.net （周口市图书馆） | — | — |
|  | 驻马店 | — | ⛔ 不通 | http://www.zmdlib.net （驻马店市图书馆） | — | — |
| 湖北省 | 武汉 | — | 🔍 待核验 | https://www.library.hb.cn （湖北省图书馆） | — | — |
|  |  | — | ⛔ 不通 | http://www.whlib.org.cn （武汉图书馆） | — | — |
|  | 十堰 | — | ⛔ 不通 | http://www.sylib.net （十堰市图书馆） | — | — |
|  | 襄阳 | — | ⛔ 不通 | http://www.xylib.net （襄阳市图书馆） | — | — |
|  | 鄂州 | — | ⛔ 不通 | http://www.ezlib.net （鄂州市图书馆） | — | — |
|  | 荆门 | — | 🔍 待核验 | http://www.jmlib.net （荆门市图书馆） | — | — |
|  | 孝感 | — | 🔍 待核验 | http://www.xglib.net （孝感市图书馆） | — | — |
|  | 荆州 | — | ⛔ 不通 | http://www.jzlib.net （荆州市图书馆） | — | — |
|  | 黄冈 | — | ⛔ 不通 | http://www.hhlib.net （黄冈市图书馆） | — | — |
|  | 咸宁 | — | ⛔ 不通 | http://www.xnlib.net （咸宁市图书馆） | — | — |
|  | 随州 | — | ⛔ 不通 | http://www.szlib.net （随州市图书馆） | — | — |
|  | 恩施 | — | ⛔ 不通 | http://www.eslib.net （恩施州图书馆） | — | — |
|  | 黄石 | — | ❓ 缺失 | — | — | — |
|  | 宜昌 | — | ❓ 缺失 | — | — | — |
| 湖南省 | 长沙 | — | 🔍 待核验 | http://www.library.hn.cn （湖南图书馆） | — | — |
|  |  | — | 🔍 待核验 | https://opac.changshalib.cn （长沙图书馆） | — | — |
|  | 株洲 | — | 🔍 待核验 | http://www.zzlib.net （株洲市图书馆） | — | — |
|  | 湘潭 | — | ⛔ 不通 | http://www.xtlib.net （湘潭市图书馆） | — | — |
|  | 衡阳 | — | ⛔ 不通 | http://www.hylib.net （衡阳市图书馆） | — | — |
|  | 邵阳 | — | ⛔ 不通 | http://www.sylib.net （邵阳市图书馆） | — | — |
|  | 岳阳 | — | ⛔ 不通 | http://www.yylib.net （岳阳市图书馆） | — | — |
|  | 常德 | — | ⛔ 不通 | http://www.cdlib.net （常德市图书馆） | — | — |
|  | 张家界 | — | ⛔ 不通 | http://www.zjjlib.net （张家界市图书馆） | — | — |
|  | 益阳 | — | ⛔ 不通 | http://www.yylib.net （益阳市图书馆） | — | — |
|  | 郴州 | — | ⛔ 不通 | http://www.czlib.net （郴州市图书馆） | — | — |
|  | 永州 | — | ⛔ 不通 | http://www.yzlib.net （永州市图书馆） | — | — |
|  | 怀化 | — | ⛔ 不通 | http://www.hhlib.net （怀化市图书馆） | — | — |
|  | 娄底 | — | ⛔ 不通 | http://www.ldlib.net （娄底市图书馆） | — | — |
|  | 湘西 | — | ⛔ 不通 | http://www.xxlib.net （湘西州图书馆） | — | — |
| 海南省 | 海口 | — | ⛔ 不通 | http://www.hilib.com （海南省图书馆） | — | — |
|  |  | — | 🔍 待核验 | http://www.haikoulib.cn （海口图书馆） | — | — |
|  | 三亚 | — | ❓ 缺失 | — | — | — |
|  | 三沙 | — | ❓ 缺失 | — | — | — |
|  | 儋州 | — | ❓ 缺失 | — | — | — |
| 贵州省 | 贵阳 | — | 🔍 待核验 | http://www.gzlib.com.cn （贵州省图书馆） | — | — |
|  |  | — | 🔍 待核验 | http://www.gylib.org.cn （贵阳市图书馆） | — | — |
|  | 六盘水 | — | ❓ 缺失 | — | — | — |
|  | 遵义 | — | ❓ 缺失 | — | — | — |
|  | 安顺 | — | ❓ 缺失 | — | — | — |
|  | 毕节 | — | ❓ 缺失 | — | — | — |
|  | 铜仁 | — | ❓ 缺失 | — | — | — |
|  | 黔西南 | — | ❓ 缺失 | — | — | — |
|  | 黔东南 | — | ❓ 缺失 | — | — | — |
|  | 黔南 | — | ❓ 缺失 | — | — | — |
| 云南省 | 昆明 | — | 🔍 待核验 | http://www.ynlib.cn （云南省图书馆） | — | — |
|  |  | — | 🔍 待核验 | http://www.kmlib.yn.cn （昆明市图书馆） | — | — |
|  | 曲靖 | — | ❓ 缺失 | — | — | — |
|  | 玉溪 | — | ❓ 缺失 | — | — | — |
|  | 保山 | — | ❓ 缺失 | — | — | — |
|  | 昭通 | — | ❓ 缺失 | — | — | — |
|  | 丽江 | — | ❓ 缺失 | — | — | — |
|  | 普洱 | — | ❓ 缺失 | — | — | — |
|  | 临沧 | — | ❓ 缺失 | — | — | — |
|  | 楚雄 | — | ❓ 缺失 | — | — | — |
|  | 红河 | — | ❓ 缺失 | — | — | — |
|  | 文山 | — | ❓ 缺失 | — | — | — |
|  | 西双版纳 | — | ❓ 缺失 | — | — | — |
|  | 大理 | — | ❓ 缺失 | — | — | — |
|  | 德宏 | — | ❓ 缺失 | — | — | — |
|  | 怒江 | — | ❓ 缺失 | — | — | — |
|  | 迪庆 | — | ❓ 缺失 | — | — | — |
| 陕西省 | 西安 | — | 🔍 待核验 | https://uilas.sxlib.org.cn （陕西省图书馆） | — | — |
|  |  | — | 🔍 待核验 | http://www.xalib.org.cn （西安图书馆） | — | — |
|  | 铜川 | — | ❓ 缺失 | — | — | — |
|  | 宝鸡 | — | ❓ 缺失 | — | — | — |
|  | 咸阳 | — | ❓ 缺失 | — | — | — |
|  | 渭南 | — | ❓ 缺失 | — | — | — |
|  | 延安 | — | ❓ 缺失 | — | — | — |
|  | 汉中 | — | ❓ 缺失 | — | — | — |
|  | 榆林 | — | ❓ 缺失 | — | — | — |
|  | 安康 | — | ❓ 缺失 | — | — | — |
|  | 商洛 | — | ❓ 缺失 | — | — | — |
| 甘肃省 | 兰州 | — | 🔍 待核验 | https://www.gslib.com.cn （甘肃省图书馆） | — | — |
|  |  | — | 🔍 待核验 | http://www.lzlib.com.cn （兰州市图书馆） | — | — |
|  | 嘉峪关 | — | ❓ 缺失 | — | — | — |
|  | 金昌 | — | ❓ 缺失 | — | — | — |
|  | 白银 | — | ❓ 缺失 | — | — | — |
|  | 天水 | — | ❓ 缺失 | — | — | — |
|  | 武威 | — | ❓ 缺失 | — | — | — |
|  | 张掖 | — | ❓ 缺失 | — | — | — |
|  | 平凉 | — | ❓ 缺失 | — | — | — |
|  | 酒泉 | — | ❓ 缺失 | — | — | — |
|  | 庆阳 | — | ❓ 缺失 | — | — | — |
|  | 定西 | — | ❓ 缺失 | — | — | — |
|  | 陇南 | — | ❓ 缺失 | — | — | — |
|  | 临夏 | — | ❓ 缺失 | — | — | — |
|  | 甘南 | — | ❓ 缺失 | — | — | — |
| 青海省 | 西宁 | — | ⛔ 不通 | http://www.qhlib.org （青海省图书馆） | — | — |
|  |  | — | 🔍 待核验 | https://www.xnlib.cn （西宁市图书馆） | — | — |
|  | 海东 | — | ❓ 缺失 | — | — | — |
|  | 海北 | — | ❓ 缺失 | — | — | — |
|  | 黄南 | — | ❓ 缺失 | — | — | — |
|  | 海南州 | — | ❓ 缺失 | — | — | — |
|  | 果洛 | — | ❓ 缺失 | — | — | — |
|  | 玉树 | — | ❓ 缺失 | — | — | — |
|  | 海西 | — | ❓ 缺失 | — | — | — |
| 西藏自治区 | 拉萨 | — | ❓ 缺失 | — | — | — |
|  | 日喀则 | — | ❓ 缺失 | — | — | — |
|  | 昌都 | — | ❓ 缺失 | — | — | — |
|  | 林芝 | — | ❓ 缺失 | — | — | — |
|  | 山南 | — | ❓ 缺失 | — | — | — |
|  | 那曲 | — | ❓ 缺失 | — | — | — |
|  | 阿里 | — | ❓ 缺失 | — | — | — |
| 内蒙古自治区 | 呼和浩特 | — | ⛔ 不通 | http://www.nmglib.com （内蒙古图书馆） | — | — |
|  | 包头 | — | ⛔ 不通 | http://www.btlib.net （包头市图书馆） | — | — |
|  | 赤峰 | — | ⛔ 不通 | http://www.cflib.net （赤峰市图书馆） | — | — |
|  | 通辽 | — | ⛔ 不通 | http://www.tllib.net （通辽市图书馆） | — | — |
|  | 鄂尔多斯 | — | ⛔ 不通 | http://www.ordoslib.net （鄂尔多斯市图书馆） | — | — |
|  | 呼伦贝尔 | — | ⛔ 不通 | http://www.hlbrlib.net （呼伦贝尔市图书馆） | — | — |
|  | 巴彦淖尔 | — | ⛔ 不通 | http://www.bynrlib.net （巴彦淖尔市图书馆） | — | — |
|  | 乌兰察布 | — | 🔍 待核验 | http://www.wlcblib.net （乌兰察布市图书馆） | — | — |
|  | 乌海 | — | ❓ 缺失 | — | — | — |
|  | 兴安盟 | — | ❓ 缺失 | — | — | — |
|  | 锡林郭勒盟 | — | ❓ 缺失 | — | — | — |
|  | 阿拉善盟 | — | ❓ 缺失 | — | — | — |
| 广西壮族自治区 | 南宁 | — | 🔍 待核验 | http://www.gxlib.org.cn （广西壮族自治区图书馆） | — | — |
|  |  | — | 🔍 待核验 | https://www.nnlib.com （南宁市图书馆） | — | — |
|  | 桂林 | — | ⛔ 不通 | http://www.gll-gx.org.cn （广西壮族自治区桂林图书馆） | — | — |
|  | 柳州 | — | ⛔ 不通 | http://www.lzlib.net （柳州市图书馆） | — | — |
|  | 梧州 | — | ⛔ 不通 | http://www.wzlib.net （梧州市图书馆） | — | — |
|  | 北海 | — | ⛔ 不通 | http://www.bhlib.net （北海市图书馆） | — | — |
|  | 防城港 | — | ⛔ 不通 | http://www.fcglib.net （防城港市图书馆） | — | — |
|  | 钦州 | — | ⛔ 不通 | http://www.qzlib.net （钦州市图书馆） | — | — |
|  | 贵港 | — | ⛔ 不通 | http://www.gglib.net （贵港市图书馆） | — | — |
|  | 玉林 | — | ⛔ 不通 | http://www.yllib.net （玉林市图书馆） | — | — |
|  | 百色 | — | ⛔ 不通 | http://www.bslib.net （百色市图书馆） | — | — |
|  | 贺州 | — | ❓ 缺失 | — | — | — |
|  | 河池 | — | ❓ 缺失 | — | — | — |
|  | 来宾 | — | ❓ 缺失 | — | — | — |
|  | 崇左 | — | ❓ 缺失 | — | — | — |
| 宁夏回族自治区 | 银川 | — | 🔍 待核验 | http://www.nxlib.cn （宁夏图书馆） | — | — |
|  | 石嘴山 | — | ❓ 缺失 | — | — | — |
|  | 吴忠 | — | ❓ 缺失 | — | — | — |
|  | 固原 | — | ❓ 缺失 | — | — | — |
|  | 中卫 | — | ❓ 缺失 | — | — | — |
| 新疆维吾尔自治区 | 乌鲁木齐 | — | 🔍 待核验 | https://www.xjlib.org （新疆维吾尔自治区图书馆） | — | — |
|  | 克拉玛依 | — | ❓ 缺失 | — | — | — |
|  | 吐鲁番 | — | ❓ 缺失 | — | — | — |
|  | 哈密 | — | ❓ 缺失 | — | — | — |
|  | 昌吉 | — | ❓ 缺失 | — | — | — |
|  | 博尔塔拉 | — | ❓ 缺失 | — | — | — |
|  | 巴音郭楞 | — | ❓ 缺失 | — | — | — |
|  | 克孜勒苏 | — | ❓ 缺失 | — | — | — |
|  | 伊犁 | — | ❓ 缺失 | — | — | — |
|  | 阿克苏 | — | ❓ 缺失 | — | — | — |
|  | 喀什 | — | ❓ 缺失 | — | — | — |
|  | 和田 | — | ❓ 缺失 | — | — | — |
|  | 塔城 | — | ❓ 缺失 | — | — | — |
|  | 阿勒泰 | — | ❓ 缺失 | — | — | — |

## Interlib 家族（图创，多城共享模块）

`src/mcp_library_search/interlib/` 是一方共享代码：`client.py`（HTTP）、`parser.py`（搜索页/详情页 HTML + 馆藏 JSON）、`__init__.py`（三原语，对外签名冻结）。结构事实以广州 fixture 为基准（`tests/fixtures/guangzhou/NOTES.md`），杭州的结构兼容性钉在 `tests/test_hangzhou_compat.py`。以下行为各成员共享，写一次：

- 搜索页：每条结果是 `bookmeta` 容器（`bookrecno` 即 `book_id`），字段按 class 锚点提取（title-link/author-link/publisher-link）；总数"检索到: N 条结果"（带千分位逗号）；分页"共 N 页" + 「下一页」锚点存在与否。
- 详情页：书目在 `bookInfoTable` 两列表格（leftTD 标签 / rightTD 值）；**没有独立索书号字段**，`call_number` 取"中图分类法"值；简介取"内容提要"；标题在首个 `<h2>`。
- 馆藏：不在详情页 HTML 内联，走 Ajax JSON 接口 `/opac/api/holding/{bookrecno}`；馆码/位置码/状态码分别经 `libcodeMap`/`localMap`/`holdStateMap` 翻译，查不到回退码本身。
- 应还日期：借出单册在 `loanWorkMap[barcode].returnDate`（epoch 毫秒，按 UTC+8 解释，与馆方系统时区一致），退回单册 `loan` 字段保守提取。
- 可借分类：`is_available_status` 状态词表——命中不可借词优先，命中可借词次之，都不中**保守判不可借**（未识别状态不让读者白跑）。
- 详情页 tagTr 污染缺陷已修复（2026-10-02，江阴/温州各自独立实证）：「标签」行左格是裸 `<td>` 无 leftTD，其值「没有标签」曾挂到上一个已消费标签名下（污染 author 或 call_number）——穗杭 fixture 恰有「次要责任者」行重置才从未触发，**任何家族城市缺责任者行的记录都会命中**。修复口径：`_finish_value` 标签与值一对一消费（消费即清空 `_label`），钉在 `tests/test_jiangyin_parser.py` 与 `tests/test_wenzhou_compat.py`。
- **pro2018 模板代已家族化**（2026-10-02）：`InterlibConfig.pro2018`（默认 False＝广州基准）
  ＋ `pro2018_cite_author`（引文块责任者兜底，绍兴实证）＋ `parser.parse_search_pro2018`/
  `parse_detail_pro2018`；台州/成都/绍兴三城以开关委托，家族内不再有本地解析副本。搜索页
  条目 `li.libBookLi`（非 bookmeta）、详情页 `a.bkTxtTit`＋`bkTxtLeft/bkTxtRight`。
  pro2018 搜索分页必须走 JS 变量 `totalPage:`/`currentPage:`（广州基准的「下一页」锚点
  探测法在 pro2018 页恒 `has_next=False`，是错误结果）。`InterlibConfig.ctx`
  上下文路径字段仍未合入（合肥市图 `/lib2` 已由 hefei.py 本地实现，出现第二个
  非 `/opac` 上下文城市再抽象）。

成员城市差异（默认值即广州行为，差异以 `InterlibConfig` 字段表达）：

| 成员 | 家族配置 | 差异与数据边界 |
|---|---|---|
| 广州（基准） | 默认 | 结构事实基准，各城差异均相对此基准（`tests/fixtures/guangzhou/NOTES.md`）。 |
| 杭州 | 默认（另用 `search_raw` 取内部 isbn 供归并） | 「馆藏浏览」锚点缺失（用「馆藏地点」）；空结果页含 `bookDetail(` 的 JS 函数定义，解析必须按 `bookDetail(数字` 匹配，不能裸数出现次数；详情页 JS 甚至带广州分支函数；杭图源行为与合并前完全一致（`test_hangzhou_compat.py` 零改动仍绿）。双源合并见「一城多源合并」。 |
| 江阴 | 默认（零 quirk，不需要 `curlibcode`） | 本地自建单租户；base_url `http://libopac.jylib.cn:9090`（HTTP 明文＋9090 端口）；与杭州一样无「馆藏浏览」锚点；空结果页比杭州更干净（连 `bookDetail(` 函数定义都没有）；馆名两名并存原值照登——页内全称「江阴市图书馆」、`libcodeMap[JYLIB]` 译名「江阴图书馆」；网点含农家书屋等 24H 服务点（`tests/fixtures/jiangyin/NOTES.md`）。 |
| 温州 | 默认（本地部署，`curlibcode` 默认空） | 首页 28 处 `curlibcode` 是模板 JS 的「限定所在馆」筛选逻辑；首页 675KB 偏大是 91 馆/2555 地点筛选区全量服务端渲染，三端点与广州基准同构；部分书目有独立「索书号」行（data-sort=130，词表外不参与解析，`call_number` 维持取「中图分类法」，完整索书号以馆藏 JSON `callno` 为准）；「主要责任者」「内容提要」行是记录级可选，缺失则 author/summary 空串（数据边界）；主馆馆码 WT（温图市府路馆）；纯电子书书目 holdingList 为空属正常。 |
| 台州 | `pro2018=True` | 总数在 `schResNumIn` 元素；`rows` 参数服务端真实生效（total_pages 随 limit 变）；借出单册带应还日期，逾期形态原值照登；`curlibcode` 不需要（检索/详情裸参数可通）。`tests/fixtures/taizhou/NOTES.md`。 |
| 成都 | `pro2018=True` | 联合目录跨成都平原经济区（主馆成都图书馆 CD101，libcodeMap 483 馆码）；定性证据：meta keywords 自报「opac, 图创, interlib」、页脚 © www.interlib.com.cn、静态资源 `/opac/media/pro2018/simple/`（调研原话「汇文 Libsys Pro2018」有误）；holdStateMap 原值 `2→在馆`（可借）/`3→借出`（不可借）与调研初判**相反**，家族词表判定无需新表；应还日期 loanWorkMap.returnDate 直取；自带 ≥2 秒节流；detail 的 `?return_fmt=json` 完整 MARC 未采用；p1 首条 ebkType 显示「期刊」语义存疑，原值照登。`tests/fixtures/chengdu/NOTES.md`。 |
| 绍兴 | `pro2018=True`＋`pro2018_cite_author=True` | 搜索：结果容器 `<ul class="libBookUl"><li class="libBookLi">`；稳定 ID 取题名锚点 `bookDetail(<recno>,…)` 调用；`has_next` 仍可靠「下一页」锚点。详情：字段为「标签：值」行（`ISBN：/出版发行：/中图分类法：`等）。馆藏：单书 `GET /opac/api/holding/{recno}`；联合层书目（无本地单册）单书 GET 与批量 `POST /opac/api/holding/getHoldingsBybookrecnos` 均为空——属数据边界，检索页「在馆」计数即走该批量 POST。`tests/fixtures/shaoxing/NOTES.md`。 |
| 合肥（皖图 `AH:` ＋ 市图 `HF:`） | 默认，另按 `_Source.ctx` 拼路径自建单源三原语（复用家族 client/parser） | 两源与穗杭完全同模板，唯一结构差异：**HF 应用上下文是 `/lib2` 非 `/opac`**（`/opac/*` 返回 nginx 500）；`InterlibConfig.ctx` 家族化提案未合入。tagTr 缺陷由合肥 AH 布局第三路独立实证，回归钉子 `test_ah_detail_author_not_clobbered_by_tag_row`。双源合并见「一城多源合并」。`tests/fixtures/hefei/NOTES.md`。 |
| 中新友好（生态城，天津第三源） | `curlibcode=STC001` | 检索与详情必须带 `curlibcode`（缺详情参数直接 HTTP 500），馆藏 JSON 不需要；ISBN 在 `expressServiceTab` 兄弟节点上，家族 parser 以 `express_bookrecno` 后挂；`search_raw` 暴露内部 isbn 字段供归并（契约 `BookSummary` 不含 isbn）。 |
| 青岛 | 默认，**检索通道在适配器内改走站点内嵌 Solr** | 主站 HTML 检索页 `/opac/search` 被滑动验证码常态拦截（`slideVerify`，新会话首个检索请求即触发，非限速型；验证结果只落在当次浏览器会话），而站点内嵌的 Solr 后端 `GET /opac/api/search` 开放——检索原语改走该通道（`wt=json`，`q`＋`rows`＋`page`；服务端凭 `page` 自算 `start`，直传 `start` 被忽略），是本城相对广州基准的唯一结构差异。`docs[].id` 即 `bookrecno`，可直接用于详情与馆藏端点；详情无需 `curlibcode`，`/opac/book/{id}` 与 `/opac/api/holding/{id}` 与广州基准完全同构，家族 parser 零改动全字段解析。数据边界：服务端默认 `fq` 是硬编码状态白名单＋定位集合，自行追加 `fq` 会被整体覆盖，故结果默认只含有馆藏书目、`hasholding` 恒为 `y`（`availability_summary` 恒空串）；带连字符 ISBN 命中不了（同广州 marc），首搜为空时去连字符重试；自带 ≥2 秒节流。`tests/fixtures/qingdao/NOTES.md`。 |
| 苏州 | 默认（零 quirk，不需要 `curlibcode`） | `https://reader.szlib.com`，默认（非 pro2018）模板；检索/详情/馆藏裸参数均通，无需 `curlibcode`。详情页内嵌馆藏请求带 `jsessionid`＋`isCluster=false`，但家族 `isCluster=`（空）实测同样返回完整 holdingList、不依赖会话，故不新增字段。libcodeMap 仅 4 项（`ST=苏图`、`999=中心馆`、`zd=职大分馆`、`GS=姑苏区分馆`，馆名译名缩写「苏图」原值照登）、localMap 250 项。部分书目 `holdingList` 为空但 maps 齐全，属记录级数据事实（无实体单册），返回空馆藏列表正确。tagTr stale-label 缺陷在苏州记录上未触发。`tests/fixtures/suzhou/NOTES.md`。 |

新接同族城市：`adapters/cn/<city>.py` 照广州/杭州同款 `_client` 形态 + 在 `adapters/cn/__init__.py` 注册 + 在本文件总览表登记 + 在上表加一行。

## VuFind（上海）

vendor 组件 shanghai-library-book-search-python（Apache-2.0），细节与本地补丁记录见根 [NOTICE](../../NOTICE)。

- 检索总条数：站点统计区不再输出（`total_results` 恒为 0），adapter 按"0 且当前页有结果 → 视为未知（null）"处理，不属于代码 bug。
- 简介：站点没有独立简介区块，内容简介以书目"附注"字段（MARC 500）形式给出，vendor 补丁将 summary 回退到附注（见 NOTICE 变更）。
- 应还日期：馆藏页不直接渲染归还日期，已借出馆藏的 `<a class="item-return-date">` 只带单册 `data-itemid`，需按条调用 `AJAX/JSON?method=itemReturnDate`（vendor 提供 `get_return_date`，adapter 负责逐个补 `due_date`）。
- 同步上游：上游是平铺 import，已改为包内相对导入；覆盖同名文件同步后必须重新应用该修改。本地补丁（parser 的 has_next、library_client 的 statistics）同步后检查是否需重打，并在 NOTICE 变更里记一笔。

## ALEPH 家族（天津、南京）

`aleph/` 是家族共享模块（`client.py` HTTP 层＋每 host 节流＋验证码墙、`parser.py`
三种页面解析、`__init__.py` 三原语与 `AlephConfig`），成员：天津主馆 `TJL01`、少儿馆
`TJC01`（`adapters/cn/tianjin.py`）与南京图书馆 `NJL01`（`adapters/cn/nanjing.py` 的南图源）。
天津同城的第三源中新友好走 Interlib 家族；两城的多源合并口径见「一城多源合并」。

- **同城多台 ALEPH 不可并查**：opacwh/opacse 是两台独立服务器、各自独立 `local_base`，
  同一「三体」检索 TJL01 156 条 vs TJC01 32 条，数据互不相通——必须分别检索再归并。
- **ALEPH quirks**（详见 `tests/fixtures/tianjin/NOTES.md`、`tests/fixtures/nanjing_prov/NOTES.md`）：
  检索码以页内下拉为准——ISBN 是 **ISB**（`ISBN` 会报「检索请求解析错误」）、全字段 WRD、
  系统号 SYS；ISB/SYS 单命中**直接返回完整记录页**（非 brief 列表）；`short-jump` 的 jump 是
  **记录偏移不是页码**（页 P → jump=(P-1)×10+1）；天津必须用页内会话 URL（`F/VV...` 前缀，
  set_number 绑定 cookie 会话），南图无 Cookie、会话号写在 URL 路径里可跨请求复用；
  brief 页 publish section 注释块多于真实条目（13 vs 10），以 `class=itemtitle` 锚定并按
  DOC-NUMBER 去重；**编码 UTF-8**（GBK 初判被实测否定）；天津无会话 `full-set-set` 直连
  不可用，两城详情统一走 SYS 检索。
- **单册页 item-global 列语义**：「单册状态」列是流通类型（阅览/中文图书借阅…），
  「应还日期」列才是可借性原值（在架上 / 借出日期 / 分配中·编目中·物流中等）；
  可借判定只看应还日期列，词表外保守不可借。**南图另有坑**：`year/volume/sub_library`
  三个参数可以留空但**不能整个省略**，省略即返回「在服务器上没有找到所要查询的文件」
  错误页——故南图源开 `item_global_all_params=True`。南图取馆藏要用详情页里的
  `doc_library`，它与检索用的 `FIND-BASE` 可以不同（CNBOK 命中、馆藏在 NJL01）。
- **限频与验证码墙**：天津约 8 个快速请求触发 **HTTP 401 按 IP 封**（上次实测约 1 小时）；
  南图首次访问即可能 401。墙**按 host 独立**——解南图不解天津。实抓以 8 秒间隔稳定，
  适配器按 4 秒/host 节流。401 与 200 验证码页统一抛 `CaptchaError`（带手动解封指引），
  **穿透源级容错**直达调用方——封禁是全局信号，静默降级成部分结果会误导。
  其余源级失败：≥1 源存活即返回，全失败汇总报错。
- **跨行吞值陷阱（已修）**：字段取值正则写 `\s*` 会跨行，字段为空时把下一行文本
  吞成值（空 ISBN 吞掉 `SET-NUMBER`/`TITLE`、空 `IMPRINT` 吞掉 `CALL-NO`）。天津
  fixture 各字段全非空故从未暴露，南图的音像与古籍记录踩中；已统一收紧为只吃同行
  空白，钉在 `tests/test_nanjing_prov_recon.py`。
- 同家族但未接入：国家图书馆（检索码 NLC01/NLC09，仅 HTTP；当日探测仍 empty reply）
  ——状态与依据见总览表。

## 汇文 uopac 家族（南京金陵源、扬州）

家族模块 `uopac/`：`parser.py` 页面解析（检索结果／详情／馆藏表）、`client.py`
HTTP 层（每 host 节流、网络类错误重试一次、可选 securitycam cookie）。城市差异
只允许以 `UopacConfig` 带默认值的字段（quirk）新增，默认值即金陵行为。适配器：
`adapters/cn/nanjing.py`（金陵源＋南图 ALEPH 双源合并）、`adapters/cn/yangzhou.py`（单源）。
扬州接入时把金陵源一并家族化——两站实测逐项同构，避免两份会各自漂移的解析副本
（同 Interlib／ALEPH 家族先例）。

**金陵源**（另一源是南图 ALEPH，见上章）：API 基址 http://uopac.jllib.cn
（汇文「南京市公共图书馆书目全文检索」，金陵图书馆运营，成员馆＝金陵＋12 区馆），
**无状态、无 Cookie**（裸请求与带会话响应逐字节相同，实证），节流 4 秒/host，
timeout 90 秒（源站 chunked 传输可停顿 ≥60 秒，重试即好——家族 HTTP 层据此重试
一次网络类失败，HTTP 状态错误不重试）。

- **金陵自研 PHP OPAC 整体登录墙**：`opac.jllib.cn/opac/*`（search_adv.php/search.php/
  presearch.php/top_lend.php）全部 `302 → ../reader/login.php?msg=login_to_continue`，
  带 PHPSESSID 会话同样拦；先期调研看到的「公开检索入口」实为登录页外壳导航链接。
  未绕行，证据存 `tests/fixtures/nanjing/loginwall_*.headers.txt`，勿当入口登记。
  金陵馆藏经 uopac **服务端代理**匿名可取（`ajax_holding.action?url=<成员馆代理>`）。
- **检索**：GET `/uopac/s/search_result.action?q=&meta=&page=`（meta：20 任意/11 题名/
  14 ISBN 等）；总数「有 N 项」；**每页固定 20 条，limit 不生效**（数据边界）；
  默认全市联合目录，分面 `fkey=facet_libs&fval=JL` 可锁金陵（适配器未启用，机制在 NOTES）。
- **ISBN quirk**：索引按各馆存储原样前缀匹配（带/不带连字符不一）——数字间插 `*`
  通配归一，四形态探针实证稳定命中。
- **jsessionid quirk**：无 Cookie 时 Tomcat 把条目 URL 重写为
  `detail.action;jsessionid=…?id=`——首版正则单测全绿、实网 0 条目（正是
  architecture.md 警示的故障类活例），解析兼容两形态并钉裸抓 fixture（`*_bare.html`）。
- **详情**：GET `/uopac/s/detail.action?id={N}`，含提要（summary）；**无索书号字段 →
  `call_number=""`**（单册索书号在馆藏明细里）；多馆 tab 逐馆展开。
- **馆藏**：GET `/uopac/s/ajax_holding.action?type=full&url=&lib=&id=`，单册级表格
  （索书号/条码/校区/馆藏地/状态）；状态词「可借」/「借出-应还日期：YYYY-MM-DD」
  （due_date 归一提取，坏日期不猜），词表外保守不可借；单馆代理失败容忍不整败。
- book_id＝`JL:` ＋ uopac 原生数字 id（源前缀由双源合并引入；**向后兼容**：0.4.0 已上线的
  裸数字 id 一律按 JL 成员路由，兼容垫片钉在 `tests/test_nanjing_dual_source.py`）。
- 侦察结论见 `tests/fixtures/nanjing/NOTES.md`（「钉死事实一/二」节）。

### 扬州（`yangzhou`，汇文 uopac 家族）

- **入口与范围**：http://ytlmopac.cn:8080/uopac/s/search.action ——页头「扬州市图书馆
  联盟馆藏书目检索 v1.0」，与金陵**同系统、页面逐项同构**（检索页/详情页/馆藏表
  全字段同形），解析直接走 `uopac/` 家族；单源，不做成员馆过滤（联盟联合口径）。
  成员馆实测含扬州市图书馆（`YZLIB`）与扬州市邗江区图书馆（`YZHJQG`）等。
- **securitycam 反爬＝静态挑战（与金陵的唯一差别）**：全路径要求 `securitycam`
  cookie，缺 cookie 返回 ~2.5KB JS 壳页（HTTP 200，非 403）。壳页里 key／IV／密文
  三个常量**硬编码且跨请求逐字节相同**（多次响应只有回显的 `location.href` 不同），
  单块 AES-128-CBC 解出的 cookie 是固定值 → 直接写进 `UopacConfig.securitycam`，
  **不引入 JS 引擎、不移植 slowAES**。常量若被轮换，家族 HTTP 层认出壳页即抛含馆名
  的错误（不静默退化成空结果），重算一条命令，推导与命令见
  `tests/fixtures/yangzhou/NOTES.md`。
- **`;jsessionid=` 无关**：带不带都同样被壳页拦或不拦，真正的门是 cookie。
- **状态词表**：实测只有「可借」「借出」两种裸词，**源站不给应还日期**——按家族
  统一口径 `due_date` 恒空串（数据边界，非故障；与浙江图书馆源、金华源同理）。
- **无索书号字段**：详情页同金陵，`call_number` 恒空串（中图法分类号不冒充）。
- 侦察结论见 `tests/fixtures/yangzhou/NOTES.md`。

**汇文 uopac 防护逐站不同**：同系统不代表同防护——南京站匿名全通，扬州站有
securitycam 墙。将来评估其他汇文站点必须逐站实测，不能按系统家族推定；页面结构
则相反（两站同构，可共用解析）。

## 自研 JSON 系（深圳、浙江图书馆）

两套都是馆方自研、无商业产品可复用的 JSON 接口，实现各自独立、彼此不共享代码
（`adapters/cn/shenzhen.py`、`adapters/cn/_zjlib.py`）。

### 深圳（图书馆之城）

`adapters/cn/shenzhen.py` 独立实现（与 Interlib 无关），轻量 client（urllib + json）内置在模块内。

- 接口：`getQueryResult`（搜索，真实总数 `numFound`）、`getBookDetail`（书目详情 + 三桶馆藏）。`book_id = "{tablename}:{recordid}"`，详情接口需成对传 `metaTable`/`metaId`。
- 检索策略：关键词判为 ISBN 形态（去连字符后 13 位且 978/979 开头，或 10 位且末位可为 X）走 `v_index=isbn`，其余一律走 `v_index=all`（任意词）。isbn 索引要求完整参数集（`library=all`、`v_tablearray=bibliosm,serbibm,apabibibm,mmbibm,`、`sortfield=ptitle`、`sorttype=desc`、`cirtype`、`v_secondquery`、`v_startpubyear`、`v_endpubyear` 缺一不可），缺参会被静默忽略并回退成全库检索（实测返回约 360 万条）；带连字符与紧凑形态均可命中。任意词索引的字段集不含 ISBN，ISBN 形态关键词必须路由到 isbn 索引。实测结论钉在 `tests/fixtures/shenzhen/NOTES.md`。
- 分页：与参数名直觉相反——`page → v_page`（页码）、`limit → pageNum`（每页条数）。实测结论钉在 `tests/fixtures/shenzhen/NOTES.md`。
- 三桶：`CanLoanBook`/`OnlyReadBook` 是 `list[group]`，`BorrowedBook` 是单个 group dict 或 `null`，容器形态不一须归一化；`OnlyReadBook`（仅阅览）判不可借。
- 馆名：可借/阅览组在 group 级 `serviceaddrnotes`，借出单册在单册 `libraryNotes`；单册的 `library` 是馆代码不是馆名。
- 应还日期：`BorrowedBook` 单册的 `ReturnDate`（`YYYYMMDD` → 归一 `YYYY-MM-DD`）。
- 公共参数 `client_id=t1` 由 client 层统一注入，业务函数不传。
- 注意：该 API 非官方公开接口，字段可能漂移；字段侦察结论见 `tests/fixtures/shenzhen/NOTES.md`，漂移时以实抓为准更新解析与 fixture。

### 浙江图书馆（BFF 网关）

`adapters/cn/_zjlib.py` 轻量 JSON 客户端，节流 2 秒/host；作为 `ZJ:` 成员并入
`hangzhou`（双源合并见「一城多源合并」）。

- **接口要点**（详见 `tests/fixtures/zjlib/NOTES.md`）：全部 POST JSON，必带
  `BFF-ORG-ID` 头，无需鉴权；检索 `search-admin-service/open-api/search/pageList`
  （真实 total、`current` 分页实测生效、ISBN 关键词任意词直接命中无需专门路由；
  record 无可借性字段 → ZJ 成员 `availability_summary` 恒空）；详情
  `portal-pc-api/search/getWorkById`（书目字段嵌套在 `data.record`、多为单元素数组，
  与调研笔记有 4 处出入以 NOTES 为准；「记录不存在」与「服务器忙」统一
  `code:500` 不可区分，desc 原值照登）；馆藏 `resourceList` 是**两跳链**
  （`getWorkById(originalId) → workId → resourceList(workId)`，误传 originalId
  静默返回空、不报错）。
- **数据边界**：访客视角无应还日期（需读者登录），`due_date` 恒空串；
  library＝馆区名（districtId 查字典，查不到回退码原值，null → 空串）；
  location＝`local_name` 原值；status＝`state_name` 原值（缺失回退 state 码），
  词表（2=在馆/3=借出/9=锁定/16=馆内阅览/33=已通还…）外保守不可借。

## tcc-opac（宁波）

`adapters/cn/ningbo.py` 独立实现——tcc-opac 与 Interlib 是不同产品线，不可复用家族。
纯 JSON ＋ JWT 访客令牌（`POST /system/user/getOpenApiAccessToken` 匿名即发，
`ACCESS-TOKEN` 请求头，过期自动重取一次）：

- **检索**：`POST /search/`（尾斜杠；`bookSearch` 是开放平台端点、参数形态不同且
  长期「系统异常」，勿混用）body `{current,size,searchWay,sortWay,sortOrder,hasholding,q}`；
  `hasholding` 是二值过滤，`1`（或缺省）＝只看有馆藏、`0`＝只看无馆藏，两集合不相交
  （实测「三体」375 条 vs 32 条；前端「在馆记录」复选框默认勾选即 1）——**接入时曾误传 0**，
  结果集被限死在聚合条目所在的空壳子集上，现已固定传 1；
  `searchWay` 词表与 Interlib 同款（marc=任意词/title/isbn/author）；响应无 `code` 字段
  即成功，`numFound` 为字符串。
- **滑块风控**：`code ∈ {43001,-1,-402}` 触发前端滑块验证 → 程序化停手抛错，不硬闯。
- **详情**：`POST /service/biblios/getbyid?id=&fields=…`（参数走查询串、空 body）；
  UNIMARC 字段字典（200$a/200$f/010$a/100$a/690$a…）；`code==-1`「数据不存在」＝
  聚合条目无本地书目（数据边界）。
- **馆藏**：`POST /service/hold/pagelist {current,size:500,bibliosId}`，单册级；
  `statename` 原生状态词、`returnTime` 时间戳取日期段；一页 500 册封顶（前端同款）。
- **数据边界**：联合目录含区县馆与城市书房（馆名带源站原值前缀）；聚合条目无本地书目
  （详情「数据不存在」/馆藏 0 条），它们属「无馆藏」子集，`hasholding=1` 不返回；有馆藏
  条目字段已富化，「无馆藏」子集的 publisher/pubdate 常为空串；老书目出版项
  可能缺失（出版年兜底取 100$a）；`classno` 是分类号不作索书号，单册完整索书号在馆藏 `callno`。

## InDigLib（重庆）

`adapters/cn/chongqing.py` 独立实现（urllib + CookieJar 会话），API 基址
http://222.177.237.197:8080 （InDigLib 集群数字图书馆，Struts2 + Solr）。
使用者入口是总览表的 SearchIndex 地址；根路径 `/InDigLib/` 返回的是登录页
（6455 字节，实测），别当入口登记。

- **会话流程**：先 GET `frontV2/SearchIndex!simple.action?opacType=local` 拿 JSESSIONID，
  再 POST `OpacMarcSearchSolr!simpleSearch.action`；会话失效按页面标题标记判定
  （`opac检索结果页`/`书目详细页面`/`opac查询页`），失效重建一次再试，仍失败抛错。
- **检索参数**：`select1` 词表（all/isbn/title/author/publisher/subject/series…）+ `text1`
  关键词 + `pageSize`（生效）；ISBN 形态关键词路由 `select1=isbn`。
- **分页 quirk**：POST 的 `page` 参数被**静默忽略**，翻页必须 GET 全查询串带 `pageNo`
  （含 `lastSearchValue={select1}FIELD_SPLITVALUE_SPLIT{keyword}`）。
- **总数**：源只给 `#totalPage`（总页数）不给总条数 → `total_results` 恒为 None，不编造。
- **详情**：`book_id = {metatable}:{metaid}`（如 `i_biblios:2313420`）；字段锚点
  h4 题名/「著者」/出版社/ISBN-ISSN em/tipbox 简介；详情页无索书号字段 → `call_number=""`。
- **馆藏到单册级**：根路径 `POST InDigLib/GetAsset.action`（`metatables`/`metaids`/
  `type=map`/`orderType=`）**匿名可通、无需会话**（响应自带 JSESSIONID Set-Cookie，
  但非前提），返回 JSON `{list:[…], map:{馆名:[…]}}`，单册字段 barcode/callno/
  curlocal/cursublib/status/cirtype/loandate/retudate。**`frontV2/` 前缀的同名
  action 有登录拦截**（全链路头重放三次均 302 登录页），不用——被拦时先试根路径。
- **可借口径统一保守**：源站无明确「可借/在架」状态词，全部单册 `available=False`、
  `status` 原值照登（入藏/普通借出…），确定借出的带 `due_date=retudate`
  （YYYY-MM-DD 归一，异形置空不猜）。`only_available=True` 恒返回空列表——这是
  数据边界，不是故障；不做「入藏＝在架」预设。
- **回退**：GetAsset 不可用（请求失败/响应非 JSON）时退回详情页「馆藏信息」注释块
  的 `class="first"` 馆名，只到分馆级（`status=""`、`available=False`）。
- 字段侦察与端点真伪结论见 `tests/fixtures/chongqing/NOTES.md`。

## SirsiDynix iLink（大连）

`adapters/cn/dalian.py` 独立实现（新家族，全 HTML、无 JSON）。**会话制**：ps token 每响应都变，
全程同一 CookieJar 串行（类重庆流程）；节流 ≥4 秒/host：

- 检索：`POST /uhtbin/cgisirsi/?ps={token}/DALIANLIB/X/123`，字段 `searchdata1`=关键词、
  `srchfield1`=检索字段（实抓下拉无 ISBN 选项）。
- **检索语义（源码站行为，非适配器取舍）**：裸词按**单字 AND** 匹配、无相关度排序——
  所有字段「三体」27944 条（三 218148 ∩ 体 241303）、题名「三体」862 条，两者的首条
  都与题名无关；**ASCII 双引号才是短语检索**（所有字段「"三体"」132 条、题名「"三体"」
  63 条，均相关；ISBN 串引号与否都命中）。适配器一律按短语下发，短语 0 命中或源站拒答
  （含罗马数字等索引不收字符时回 `Error message` 页）时退回裸词再试一次。
- 翻页：结果页 hitlist 表单 POST（`/X/9` 形态）；详情/馆藏需带当次 ps token、同会话内访问，
  馆藏 HTML 内联。
- 详情定位：`book_id` 里的题名是列表页原值拼串（「题名＋资料类型＋版本＋责任者＋语种」），
  整串即便短语检索也 0 命中，故按**候选梯度**重检索：短语截断题名（在「 专著」等资料类型
  词处截断）→ 裸截断题名 → 裸整串 → 短语首段 → 裸首段（老记录题名无资料类型词时靠首段），
  取第一个能把 catkey 带回命中列表的候选。命中多于首页时在候选内逐页翻找（≤5 页）；
  **`VIEW^N` 的 N 是命中集全局序号**（第 2 页第 1 位＝21），不是页内序号。
- 会话失效（跳回入口页形态）重建一次再试，仍失败抛错；源站回 Error 页不算会话失效，换候选继续。

## UILAS（金华）

`adapters/cn/jinhua.py` 独立实现（urllib，全链路匿名零 cookie），入口
http://202.101.180.43/ILASOPAC/Index?target=0（裸 IP，**仅 HTTP**：443 证书已过期）；
节流 4 秒/host。先期调研（`docs/team/research/2026-10-02-ilas-jinhua.md`）大方向成立，
两处实质出入以实抓为准已修正（NOTES.md 先更新再写代码）：

- **检索**：POST `NTRdrBookRetr.do`；ISBN 形态路由 `searchType=isbnsrh`（带/不带连字符
  均命中），其余走任意词；总数「共有 [N]条记录」，空结果页括号为空（`共有 []条记录`）
  → total=0，总数锚点整体缺失＝非结果页，报错。
- **翻页 quirk**：GET 带 `nCurrentpage`，**SearchKey 双重 URL 编码**（页内翻页链接原样
  `%25E4%25B8%2589…`），适配器复刻二次编码。
- **book_id＝裸 recno**（纯数字，无 tablename 前缀——与深圳/重庆 `{table}:{id}` 形态
  不同），非纯数字直接报错。
- **详情**：GET `NTRdrBookRetrInfo.do?recno=`；详情页标题可能短于列表页（原值照登
  不对齐）；出版时间可为民国纪年（publish_year 提取公历，提不到空串不猜）；ISBN
  「书号不详」原值照登。
- **馆藏**：在 `div#BookHolding` 内（BookHolding 之前的两个 `table.table` 是 CADAL
  数字图书表、常为空 tbody，**别当馆藏解析**——调研笔记此处有误已修正）；只有入藏
  复本时单表「馆藏信息」，有借出才出现「已外借馆藏」两表；状态词表仅
  「入藏（可借）/借出（不可借）」，词表外保守。
- **简介**：调研称「恒空」被实抓否定——详情页有内联「附注提要」块，summary 取其原值
  （上海「附注」回退同款思路）；`getBookCatalog.do` 仍不接。
- **数据边界**：借出单册无应还日期（due_date=""，站方访客视角不提供，不猜）。
- 字段侦察与出入清单见 `tests/fixtures/jinhua/NOTES.md`。

## 图星 LibStar Find（无锡、徐州、盐城、淮安）

家族模块 `libstar/`：`client.py`（HTTP 层＋`Referer`/`groupcode` 必需头＋节流）、
`parser.py`（检索/详情/馆藏解析）、`__init__.py`（单实例三原语与 `LibStarConfig`）。
成员：无锡市新吴区图书馆（`adapters/cn/wuxi.py`，单实例＋多源预留）、徐州
（`adapters/cn/xuzhou.py`）、淮安（`adapters/cn/huaian.py`）。城市差异只允许以
`LibStarConfig` 带默认值的字段新增。
技术组件是图星 LibStar Find v3.2023.12（北京图星/超星集团），与图创 Interlib 是
两家厂商，不共用代码；家族 client 节流 1 秒/host。

**其余同款站点（2026-10-03 侦察，待接入）**：盐城 `https://findyctsg.libsp.com`
（`groupCode=100026`）。与无锡新吴、徐州、淮安**同协议、同字段**（`POST
/find/unify/search` 固定请求体；结果 `recordId/title/author/publisher/publishYear/
isbn/physicalCount/onShelfCountI` 逐项同形；同样必须带 `groupcode` 头，缺则静默
0 结果），接入只需在家族加配置与薄适配器。租户号可由 `POST /find/homePage/
getGroupCode {mappingPath}` 查得（`data.groupCode`）。已调通实测：「三体」盐城
857 条（无锡 407、徐州 407、淮安 3110 均已接入）。

> **`*.libsp.com` 是通配停放域**：`find<城>*.libsp.com` 之类任意子域都解析到
> 198.20.x.x 停放页（回「新一代图书馆服务平台」），凭域名猜测判断可达性会误判——
> 必须见到真站特征（`static*.libsp.com/static/js/*`）或调通 API 才算数。

- **两个必需请求头（本城最大的坑）**：`Referer`（任意值即可，只校验存在）与
  `groupcode: 800507`（新吴区租户号，≠ libCode）。缺 `Referer` 时**所有内容类
  端点**返回 `errCode:9999`「系统访问中断」——措辞指向下游 OPAC 不可达，实为
  站点的反爬兜底，**极易误判成服务端宕机**（2026-10-02 初判「无锡不通」即此）；
  缺 `groupcode` 不报错，HTTP 200 但 `numFound` 恒 0。配置类端点
  （`findConfig/*`、`webSite/*`）不受影响，所以站点看起来「一半是活的」。
  两者由 `_request()` 统一注入，三个原语无从遗漏。
- **检索**：`POST /find/unify/search`，请求体是约 30 个字段的固定模板，只有
  `searchFieldContent`/`page`/`rows` 随调用变化（`searchField=keyWord` 通吃
  书名/作者/ISBN）。响应 `data.numFound` 为真实总数（扁平数字）；
  `data.facetResult` 有 14 个聚类维度。**ISBN 带不带连字符都命中**，无需去连字符重试。
- **详情**：`GET /find/searchResultDetail/getBookDetail?recordId=`（**必须 GET**，
  同参数 POST 回 9999）。响应 `data.bean2List[]` 字段码：`cnb01` 题名/责任者
  （按第一个 `/` 切分）、`cnb03` 出版发行项（`北京:出版社,2022` 或 `北京,2017`）、
  `cnb04` ISBN及定价、`cnb67` 中图法分类号、`cnb96` 提要文摘附注。
  详情页无独立索书号字段，`call_number` 取 `cnb67`（同青岛家族口径）。
- **馆藏**：`POST /find/physical/groupItemsByLibCode {recordId}`，响应
  `data.sortedList[馆名].phyItemVo[]`，单册含 `callNo`/`locationName`/`inDate`。
  馆藏下沉到街道分馆与社区服务点（净湖社区、伯渎河文化中心图书馆各层等），原值照登。
- **状态词表**：`processType` 实测只有两态——`在架`（可借）与
  `借出-应还日期:YYYY-MM-DD`（不可借，**应还日期直接内嵌在状态串里**，访客视角
  即可拿到，比浙图/金华强）。词表外观测值保守判不可借、原值照登（同重庆口径）。
- **可借概况**：检索结果给 `physicalCount`（总册）与 `onShelfCountI`（在架），
  站点 UI 即以此显示「纸本(N) / 可借(M)」，`availability_summary` 由此二值拼装；
  任一项缺失（老书目）留空串。
- **数据边界**：检索索引与馆藏端点会不一致——实抓 143656 索引计 1 册而三种馆藏取法
  全空，**馆藏端点为准**，适配器如实返回空列表；`onShelfCountI=null` 本身不等于无馆藏
  （311140 同为 null 却有 1 册），只是可借概况留空。
- **多源预留**：无锡市图书馆（主馆）后续接入，届时在 `wuxi.py` 内作第二数据源、按
  ISBN 归并（天津口径）。`book_id` 从第一天就带 `WXXW:` 源前缀，故新增源不改变
  既有 id 契约；预留源码 `WXST` 优先级在前，未接入时查询给出明确报错而非静默空。
  2026-10-03 复测：市图旧 OPAC（`222.191.248.124:8088`）仍不通，官网 www.wxlib.cn
  亦仍指向它，市图源继续搁置，待其迁到可用平台（疑为图星/超星系）后再接入。
- **徐州（`xuzhou`）差异（均无需新 quirk）**：单实例、无多源归并（所有分馆在同一
  `sortedList` 多分组里），`book_id` 即裸 `recordId`；主馆分组可为空（实抓 439114
  主馆无单册、仅鼓楼黄楼分馆 1 册）；状态词表多一态 `本馆归还: 正在上架`（保守判
  不可借）。详情接口 `errCode` 恒 `9000124`（`success:true`）是源站固定返回码，非
  错误。侦察结论见 `tests/fixtures/xuzhou/NOTES.md`。
- **淮安（`huaian`）差异（均无需新 quirk）**：单实例、无多源归并；域名是
  `*.chaoxing.com` 而非 `*.libsp.com`（同为图星系统，接入不受影响）；主馆分组可为空
  （实抓 733596 主馆无单册、清江浦区馆 2 册均借出，且索引 `可借2` 与馆藏端点不一致，
  两口径各自如实呈现）；状态词表同无锡（`在架`/`借出-应还日期:*`）。侦察结论见
  `tests/fixtures/huaian/NOTES.md`。
- 字段侦察、状态词表样本与 fixture 清单见 `tests/fixtures/wuxi/NOTES.md`、
  `tests/fixtures/xuzhou/NOTES.md`、`tests/fixtures/huaian/NOTES.md`。

## 超星智慧门户（宿迁、连云港）

宿迁 `https://sqstsg.mh.chaoxing.com`、连云港 `https://4366ha.mh.chaoxing.com` 均为
超星「智慧门户」（wisweb／chaoxing 系，静态资源在 `static.wisweb.com/entry/assets/*`）：
首页是服务端渲染的 Vue 壳，菜单与检索入口经 `/entry/page/ck/peking_library` 动态加载。
2026-10-03 实测：连云港所给入口 `/entry/global/offline` 显示「系统升级中」（根路径亦
302 到该页），但门户页本体 HTTP 200；宿迁同款门户页 HTTP 200。两站**底层书目检索
入口尚未侦察**（总览状态列 🔍 待核验），暂按门户登记，待确认其是否有可编程调用的
OPAC／发现接口后再评估接入。

## 一城多源合并（天津范本）

一个城市聚合多个独立系统时共用这套口径，天津是最早的范本，杭州、合肥、南京照此实现：

| 城市 | 源（前缀） | 优先级 |
|---|---|---|
| 天津 `tianjin` | 天津图书馆（主馆，含全市通借网络）`TJL01`、天津市少年儿童图书馆 `TJC01`、中新友好图书馆（生态城）`ZXYH` | TJL01 > TJC01 > ZXYH |
| 杭州 `hangzhou` | 杭州图书馆 `HZ`、浙江图书馆 `ZJ` | HZ > ZJ |
| 合肥 `hefei` | 安徽省图书馆 `AH`、合肥市图书馆 `HF` | AH > HF |
| 南京 `nanjing` | 金陵图书馆联合目录（含 12 区馆）`JL`、南京图书馆（江苏省图）`NJL01` | JL > NJL01（南京两源的书目字段取值与 id 顺序同此） |
| 无锡 `wuxi` | 无锡市新吴区图书馆 `WXXW`（**当前唯一已接入源**）；无锡市图书馆 `WXST` **预留未接入** | WXST > WXXW（主馆在前；市图接入前 WXST 不会命中） |

- **必须分别检索再归并**：各源是独立系统、独立书目库，同一本书的命中互不相同（天津实证：
  同一「三体」TJL01 156 条 vs TJC01 32 条），只查一个源会漏。
- **book_id 形态**：单成员 `源前缀:记录号`（如 `TJL01:002892667`、`ZXYH:217795`）；
  跨源同 ISBN 命中合成**复合 id**，成员按优先级以 `+` 连接
  （如 `TJL01:000856840+TJC01:000178012+ZXYH:217795`），书目字段取最高优先级成员原值。
  杭州另有**向后兼容**：0.3.0 已上线的裸数字 book_id（无前缀）一律按 HZ 成员路由
  （兼容垫片钉在 `tests/test_hangzhou_merge.py`；搜索输出形态升级为带前缀）。
- **ISBN 归并口径**：去连字符与空白、校验形态后归并；脏值与无 ISBN 不参与、各自成条；
  源内同 ISBN 多条（多卷/重印）保留首条。浙图 `identifierIsbn` 原值带脏后缀
  （如「9784152098702 :」），归并键按形态从脏串提取（带数字边界断言防误切），
  展示字段保持原值。
  **南京例外**：只有跨源命中的 ISBN 才合并，同源重复逐条原位保留。金陵是联合目录，
  同一本书各成员馆常各编一条记录（实抓 20 条里 3 组同 ISBN），按天津口径只留首条会把
  其余记录的馆藏一并丢掉；跨源命中时复合 id 带上全部成员，`get_holdings` 才查得全。
  结果顺序也保持各源原相关度顺序（天津口径是分组前置、无 ISBN 散条后置）。
- **聚合**：holdings 按成员拆分路由后聚合（可借在前、馆名升序）；detail 取优先级最高成员；
  `total_results`＝存活源之和，任一存活源无总数则如实 None（不编造）。
- **源级容错**：≥1 源存活即返回，全源失败才汇总报错；**限频/验证码类封禁信号穿透容错**
  直达调用方（见「ALEPH 系」的 401 说明）——封禁是全局信号，静默降级会误导。
- **实现**：各城在自己的 `adapters/cn/<city>.py` 里实现，无共享合并模块，改口径时多处都要看；
  归并行为分别钉在 `tests/test_hangzhou_merge.py`、`tests/test_hefei_merge.py`、
  `tests/test_nanjing_dual_source.py`。**待办**：天津/杭州/南京三份 `_merge_books`／
  `_norm_isbn` 已高度同源（浙图的脏后缀提取是唯一实质差异），可抽成共享模块；本次未做，
  以免在同一改动里动到已上线的两城行为。
