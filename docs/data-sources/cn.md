# 中国数据源清单（cn）

> 本文是 data-sources 总目录下的中国分卷；总目录与各国家分卷的关系见 [README.md](README.md)。

各城市图书馆的线上入口、系统技术组件与接入要点。**新增城市先在总览表登记一行**，接入要点写进对应的「接入系统」章；一个系统对多座城的，城市差异收在该章的城市表里。

> 引用约定：本文与 `tests/fixtures/*/NOTES.md` 中出现的 `docs/team/research/*.md` 调研笔记为**本地存档**（`.git/info/exclude` 排除，不随仓库分发）；各笔记的关键结论均已照实摘录进本文对应条目与 NOTES.md，外部读者无需原文即可理解全部登记依据。

> 地区维度：MCP 的 `region` 参数取域名后缀（ccTLD），默认 `cn`（中国）。本表所录站点均为 `.cn` 域名，故全部归在 `cn` 地区；将来接入其他后缀的站点时，先在该地区下登记城市，再按家族或独立实现接入。

## 总览

同一省份的城市排在一起，省份列只在该省首行填写（视觉上等同于合并单元格），新增城市时接在本省行之后。同一城市的多座馆（省馆＋市馆等）接在该城行之后，城市列只在该城首行填写，具体馆名随入口地址注明。表序分三段：直辖市在前、省居中、自治区殿后。

登记的行政粒度：二级行政单位默认指**地级市＋市辖区＋县级单位**（自治州／地区／盟同理），粒度最小到县；检索按「县级命中优先返回，未命中再上溯地级市」解析。总览含两批补入的未接入城市：一批自《全国公共图书馆OPAC查询地址清单》照登（城市与馆名原样），另一批按**地级行政区名册**补全（地级市＋自治州＋地区＋盟；只登城市名，入口缺失）。两批的标识、技术组件、适配层均留空待侦察。部分条目存在清单本身的张冠李戴（同一域名被安到多座城市），未作改写，以实测结果为准。

状态列标识：✅ 接入＝全链路实网跑通；⚠️ 部分接入＝链路有环节待修；⛔ 不通＝站点侧拦截、不可达，或实测已被域名停放/无关站点占用；🚧 攻关＝已侦察、待攻克；📋 计划＝可接入、待立项；🔍 待核验＝首页实测可达、OPAC 未侦察；⏳ 等待确认＝外部提供候选入口、页面真伪未核验；❓ 缺失＝名册内城市尚无任何登记（入口缺失）。

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
|  | 江门 | `jiangmen` | ✅ 接入 | http://125.93.12.202:9188/#/index （江门市图书馆） | 新版 UILAS（ILAS REST 平台） | `uilas_rest/` 家族 + `adapters/cn/jiangmen.py`；实抓「三体」367 条 |
|  | 湛江 | — | ⛔ 不通 | http://www.zjlib.net （湛江市图书馆） | — | — |
|  | 茂名 | — | ⛔ 不通 | http://www.mmlib.net （茂名市图书馆） | — | — |
|  | 肇庆 | — | ⛔ 不通 | http://www.zqlib.net （肇庆市图书馆） | — | — |
|  | 惠州 | — | ⛔ 不通 | http://www.hzlib.net （惠州市图书馆） | — | — |
|  | 梅州 | — | ⛔ 不通 | http://www.mzlib.net （梅州市图书馆） | — | — |
|  | 汕尾 | — | ⛔ 不通 | http://www.swlib.net （汕尾市图书馆） | — | — |
|  | 河源 | `heyuan` | ✅ 接入 | https://interlib.hylib.cn:9443/opac/index （河源市图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/heyuan.py`；实抓「三体」111 条 |
|  | 阳江 | `yangjiang` | ✅ 接入 | http://219.129.187.234:38082/opac/index （阳江市图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/yangjiang.py`；实抓「三体」98 条 |
|  | 清远 | — | ⛔ 不通 | http://www.qylib.net （清远市图书馆） | — | — |
|  | 东莞 | — | ⛔ 不通 | http://www.dglib.net （东莞图书馆） | — | — |
|  | 中山 | — | ⛔ 不通 | http://www.zslib.net （中山市图书馆） | — | — |
|  | 潮州 | `chaozhou` | ✅ 接入 | http://czlib.cn:8089/opac/ （潮州市图书馆） | 图创 Interlib（Solr 检索） | `interlib/` 家族 + `adapters/cn/chaozhou.py`；实抓「三体」90 条 |
|  | 揭阳 | — | ⛔ 不通 | http://www.jylib.net （揭阳市图书馆） | — | — |
|  | 云浮 | — | ⛔ 不通 | http://www.yflib.net （云浮市图书馆） | — | — |
| 江苏省 | 南京 | `nanjing` | ✅ 接入 | http://uopac.jllib.cn/uopac/s/search.action （金陵图书馆联合目录，金陵运营，覆盖金陵＋12 区馆） | 汇文 uopac 区域联合 OPAC（Struts2；金陵自研 PHP OPAC `opac.jllib.cn/opac/*` 整体登录墙不可用，勿当入口） | `uopac/` 家族 + `adapters/cn/nanjing.py`（双源合并：金陵 `JL:` ＋ 南图 `NJL01:`，天津口径；金陵源解析走 uopac 家族、与扬州共用，原生数字 book_id 现带 `JL:` 前缀、裸数字走兼容垫片；源站偶发 chunked 停顿，已按 NOTES 口径重试一次） |
|  |  |  | ✅ 接入 | https://opac.jslib.org.cn/F/ （南京图书馆/江苏省图） | Ex Libris ALEPH `u20_1 / www_f_chi`（外层 openresty 全局验证码墙；**按 host 独立封禁**，解南图不解天津） | `aleph/` 家族原语 ＋ `adapters/cn/nanjing.py`（南图源，`item_global_all_params=True`）；2026-10-02 全链路实网跑通，库代码表·两处坑与家族兼容性证据见 `tests/fixtures/nanjing_prov/NOTES.md` |
|  | 扬州 | `yangzhou` | ✅ 接入 | http://ytlmopac.cn:8080/uopac/s/search.action （扬州市图书馆联盟联合目录，含邗江区馆等成员馆） | 汇文 Libsys/uopac（Struts2，与金陵同系统；全路径 securitycam 静态挑战） | `uopac/` 家族 + `adapters/cn/yangzhou.py`；壳页 key/IV/密文为硬编码常量、cookie 恒定（解出值见 NOTES），故直接带常量 cookie，无需 JS 引擎；常量轮换由家族 HTTP 层认出壳页抛错，不静默空结果 |
|  | 江阴 | `jiangyin` | ✅ 接入 | http://libopac.jylib.cn:9090/opac/index | 图创 Interlib（已确认，与广州同模板、零 quirk，自建单租户） | `interlib/` 家族 + `adapters/cn/jiangyin.py` |
|  | 无锡 | `wuxi` | ✅ 接入 | http://wxxqlsp.xw.i-wnd.cn:8013/#/home （新吴区图书馆，单馆） | 图星 LibStar Find v3.2023.12（北京图星/超星系，JSON API） | `libstar/` 家族 + `adapters/cn/wuxi.py`；市图书馆源按天津口径预留（源码 `WXST`，未接入）。**两处必需请求头缺一不可：`Referer`（任意值即可，缺失时全部内容端点回 `errCode:9999`「系统访问中断」，极易误判为服务端故障）与 `groupcode: 800507`（缺失则 HTTP 200 但静默 0 结果）** |
|  |  | — | ⛔ 不通 | http://222.191.248.124:8088/opac/book_cart.php （无锡市图书馆旧 OPAC） | — | 2026-10-03 实测 8088 端口空响应、同 IP 80 端口仅 Tomcat 默认 404；官网 www.wxlib.cn 仍指向该 8088 旧 OPAC，暂无可用检索入口，市图源 `WXST` 继续搁置 |
|  | 苏州 | `suzhou` | ✅ 接入 | https://reader.szlib.com/opac/index （苏州图书馆，页标题「检索系统」，全市集群目录） | 图创 Interlib（已确认：页内自报图创／interlib、`/opac/media/*`、`bookrecno`；2026-10-03 实抓「三体」232 条、24 页） | `interlib/` 家族 + `adapters/cn/suzhou.py`（双源合并：苏州图书馆 `SZ` ＋ 苏州工业园区图书馆 `SIP`） |
|  |  |  | ✅ 接入 | http://opac.sdll.cn:8088/opac/index （苏州工业园区图书馆） | 图创 Interlib（已确认，meta keywords 自报；与苏州图书馆同款默认模板、零 quirk） | （并入 `suzhou` 双源，源前缀 `SIP`；实抓「三体」98 条） |
|  | 徐州 | `xuzhou` | ✅ 接入 | https://findxz.libsp.com （徐州市图书馆，同名多分馆含鼓楼区馆等） | 图星 LibStar Find（与无锡新吴同款，JSON API） | `libstar/` 家族 + `adapters/cn/xuzhou.py`；`groupCode=3203001001`（与主馆 libCode 同）。检索须带 `Referer`＋`groupcode` 头，缺 `groupcode` 静默 0 结果；实抓「三体」407 条 |
|  | 常州 | — | ⛔ 不通 | http://www.czlib.net （常州市图书馆） | — | 2026-10-03 实测域名解析到 198.20.x.x 域名停放段、TCP 空响应，非馆方站点；近似域名 czlib.cn＝潮州市图书馆，亦非本市，未找到可用检索入口 |
|  | 南通 | — | ⛔ 不通 | https://www.ntlib.org.cn （南通市图书馆） | — | 2026-10-03 实测 `www.ntlib.org.cn`（58.221.24.12）TLS 握手直接 EOF，裸 `ntlib.org.cn` 302 指回 www 形成循环；原登记 `www.ntlib.net` 落在 198.20.x.x 域名停放段，均无可用检索入口 |
|  | 连云港 | — | 🔍 待核验 | https://4366ha.mh.chaoxing.com/entry/page/ck/peking_library （连云港市图书馆，超星智慧门户） | 超星智慧门户（wisweb／chaoxing 系） | 用户所给入口 `…/entry/global/offline` 实测显示「系统升级中」；门户页本身 HTTP 200，底层书目检索入口未侦察 |
|  | 淮安 | `huaian` | ✅ 接入 | https://findhastsg.pub.chaoxing.com （淮安市图书馆，含少儿馆、清江浦区馆等） | 图星 LibStar Find（与无锡新吴同款，JSON API） | `libstar/` 家族 + `adapters/cn/huaian.py`；`groupCode=100382`。检索须带 `Referer`＋`groupcode` 头；实抓「三体」3110 条 |
|  | 盐城 | `yancheng` | ✅ 接入 | https://findyctsg.libsp.com （盐城市图书馆） | 图星 LibStar Find（与无锡新吴同款，JSON API） | `libstar/` 家族 + `adapters/cn/yancheng.py`；`groupCode=100026`。检索须带 `Referer`＋`groupcode` 头；实抓「三体」857 条 |
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
|  |  | `jinan` | ✅ 接入 | https://www.jnlib.net.cn:8087/999 （济南市图书馆） | 图创 tcc-opac（与宁波同款，见 tcc-opac 家族章） | `tccopac/` 家族 + `adapters/cn/jinan.py`；实抓「三体」96 条 |
|  | 淄博 | `zibo` | ✅ 接入 | http://zblib.org.cn:458/opac/index （淄博市图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/zibo.py`；实抓「三体」61 条 |
|  | 枣庄 | — | 📋 计划 | http://60.214.100.211:8082/#/index （枣庄市图书馆） | 新版 UILAS（ILAS REST 平台，页标题「UILAS知识检索平台」） | 2026-10-03 用户提供；同 `uilas_rest/` 家族（兰州/榆林/陕西省图），可立项接入 |
|  | 东营 | — | ⛔ 不通 | http://www.dylib.net （东营市图书馆） | — | — |
|  | 烟台 | — | ⛔ 不通 | http://www.ytlib.net （烟台市图书馆） | — | — |
|  | 潍坊 | — | ⛔ 不通 | http://www.wflib.net （潍坊市图书馆） | — | — |
|  | 济宁 | — | ⛔ 不通 | http://www.jnlib.net （济宁市图书馆） | — | — |
|  | 泰安 | — | ⛔ 不通 | http://www.talib.net （泰安市图书馆） | — | — |
|  | 威海 | — | ⛔ 不通 | http://www.whlib.net （威海市图书馆） | — | — |
|  | 日照 | — | ⛔ 不通 | http://www.rzlib.net （日照市图书馆） | — | — |
|  | 临沂 | — | ⛔ 不通 | http://www.lylib.net （临沂市图书馆） | — | — |
|  | 德州 | `dezhou` | ✅ 接入 | https://opac.dzelib.cn/opac/index （德州市图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/dezhou.py`；实抓「三体」30 条 |
|  | 聊城 | — | ⛔ 不通 | http://www.lclib.net （聊城市图书馆） | — | — |
|  | 滨州 | — | ⛔ 不通 | http://www.bzlib.net （滨州市图书馆） | — | — |
|  | 菏泽 | — | ⛔ 不通 | http://www.hzlib.net （菏泽市图书馆） | — | — |
| 四川省 | 成都 | `chengdu` | ✅ 接入 | https://opac.cdclib.cn/opac/index （成都市公共图书馆联合书目检索；原超星入口 books.gdlink.net.cn IP 白名单硬墙仍搁置） | 图创 Interlib（已确认，pro2018 模板代 simple 皮肤；meta keywords 自报图创 interlib） | `interlib/` 家族 ＋ `adapters/cn/chengdu.py`（`pro2018=True` 启用家族 pro2018 解析；自带 ≥2 秒节流） |
|  | 自贡 | — | ❓ 缺失 | — | — | — |
|  | 攀枝花 | — | 🔍 待核验 | http://www.pzhlib.com.cn （攀枝花市图书馆） | 图创 Interlib（站内 interlibSSO／ifs/search） | 2026-10-03 首页标题「攀枝花市图书馆网站」；OPAC 候选 host http://125.66.234.132:8180（本网络 8180 不可达，待换网复测） |
|  | 泸州 | — | ❓ 缺失 | — | — | — |
|  | 德阳 | — | 🔍 待核验 | http://www.deyanglib.cn （德阳市图书馆） | 超星智慧门户（wisweb／chaoxing） | 2026-10-03 首页标题「德阳市图书馆」，wisweb＋chaoxing 变量；OPAC 未侦察 |
|  | 绵阳 | — | ⛔ 不通 | http://www.mylib.net （外源候选，实测域名停放） | — | 2026-10-03 解析至 198.20.2.16（域名停放段，与同批 .16–.24 连续）、TCP 空响应，非馆方站点 |
|  | 广元 | — | 🔍 待核验 | http://www.gyslib.org.cn （广元市图书馆） | 超星智慧门户（wisweb／chaoxing） | 2026-10-03 首页标题「广元市图书馆」；OPAC 未侦察 |
|  | 遂宁 | — | ❓ 缺失 | — | — | — |
|  | 内江 | — | ⛔ 不通 | http://www.scnjlib.cn （内江市图书馆） | — | 2026-10-03 用户实测入口可达但需登录，无可匿名检索的书目 OPAC；本机探测 HTTP 空响应（DNS→61.188.216.37，非 198.20 停放段） |
|  | 乐山 | — | 🚧 攻关 | http://opac.sclib.cn:8088/opac/search?q=&f_curlibcode=LS （四川省图书馆联合目录，按 `f_curlibcode=LS` 过滤乐山） | 系统待定（页标题「四川省图书馆书目检索系统」，非 Interlib、无 `/opac/api/search`） | 2026-10-03 用户提供：借四川省图 OPAC 过滤乐山馆。实测 `/opac/index` 200，但 `/opac/search`（任意参数）触发「opac验证」页、程序化被拦；需破解验证后可用 |
|  | 南充 | — | ⛔ 不通 | http://www.ncstsg.cn （外源候选，域名不存在） | — | 2026-10-03 DNS 无解析（NXDOMAIN），非馆方站点 |
|  | 眉山 | — | 🔍 待核验 | http://www.mslib.cn （眉山市图书馆） | 超星系（站内有 cxstar／sslibrary） | 2026-10-03 首页标题「眉山市图书馆」；:9001/msss 不可达、bookCity.html 404，OPAC 待侦 |
|  | 宜宾 | — | 🔍 待核验 | http://ybslib.cn （宜宾市图书馆） | 自研 Nuxt（待侦） | 2026-10-03 首页标题「宜宾市图书馆」；OPAC 未侦察 |
|  | 广安 | — | ❓ 缺失 | — | — | — |
|  | 达州 | — | 🔍 待核验 | https://www.dzslib.cn （达州市图书馆） | 自研 Vue SPA（待侦） | 2026-10-03 首页标题「达州市图书馆」，Vue SPA；OPAC 未侦察；与广元同 IP 124.243.227.8 |
|  | 雅安 | — | ⛔ 不通 | http://www.yaanlib.com （外源候选，实测域名停放） | — | 2026-10-03 解析至 198.20.2.17（域名停放段，与同批 .16–.24 连续）、TCP 空响应，非馆方站点 |
|  | 巴中 | — | 🔍 待核验 | https://www.bzslib.cn （巴中市图书馆） | 帝国CMS 门户 | 2026-10-03 首页标题「巴中市图书馆」；站内有 opac/馆藏字样，入口待侦 |
|  | 资阳 | — | ⛔ 不通 | http://www.zyslib.com （外源候选，实测域名停放） | — | 2026-10-03 解析至 198.20.2.18（域名停放段，与同批 .16–.24 连续）、TCP 空响应，非馆方站点 |
|  | 阿坝 | — | ❓ 缺失 | — | — | — |
|  | 甘孜 | — | ⛔ 不通 | http://www.gzzlib.com （外源候选，实测域名停放） | — | 2026-10-03 解析至 198.20.2.19（域名停放段，与同批 .16–.24 连续）、TCP 空响应，非馆方站点 |
|  | 凉山 | — | ❓ 缺失 | — | — | — |
| 浙江省 | 杭州 | `hangzhou` | ✅ 接入 | https://my1.zjhzlib.cn （杭州图书馆） | 图创 Interlib（与广州同模板） | `interlib/` 家族 ＋ `adapters/cn/hangzhou.py`（双源合并，杭图 `HZ:`） |
|  |  |  | ✅ 接入 | https://www.zjlib.cn/ （浙江图书馆，BFF 网关 `/bff-api/`） | 自研微服务（已确认；Nuxt 3＋Java/Spring＋ES，纯 JSON、无需鉴权；省级馆，6 馆区） | `adapters/cn/_zjlib.py`（浙图 `ZJ:`，天津模式并入 `hangzhou`） |
|  | 宁波 | `ningbo` | ✅ 接入 | https://opac.nblib.cn/999 | 图创 tcc-opac（已确认；Java/Spring＋Vue2 SPA，纯 JSON＋JWT 访客令牌，与 Interlib 不同产品线） | `tccopac/` 家族 + `adapters/cn/ningbo.py`（真实检索端点为 `POST /search/` 尾斜杠形态——`bookSearch` 是开放平台端点、参数形态不同且长期「系统异常」，勿混用；检索须传 `hasholding=1`＝只看有馆藏，`0` 是聚合条目所在的空壳子集）；数据边界：馆藏一页 500 册封顶 |
|  | 温州 | `wenzhou` | ✅ 接入 | https://opac3.wzlib.cn/opac/index | 图创 Interlib（已确认，与广州同模板；站点为温州市图书馆，全市总分馆 91 馆） | `interlib/` 家族 + `adapters/cn/wenzhou.py` |
|  | 绍兴 | `shaoxing` | ✅ 接入 | https://opac.sxlib.com/opac/index | 图创 Interlib（已确认，pro2018 模板代；「绍兴市公共图书馆联合目录」，主馆绍兴图书馆） | `interlib/` 家族 ＋ `adapters/cn/shaoxing.py`（`pro2018=True`＋`pro2018_cite_author=True` 启用家族解析与引文块责任者兜底） |
|  | 台州 | `taizhou` | ✅ 接入 | https://opac.tzlib.cn:8182/opac/index | 图创 Interlib（已确认，pro2018 新版模板变体；台州市图书馆，浙江地级市馆，含 S1 线地铁站等全市通借网点） | `interlib/` 家族 ＋ `adapters/cn/taizhou.py`（`pro2018=True` 启用家族 pro2018 解析） |
|  | 金华 | `jinhua` | ✅ 接入 | http://202.101.180.43/ILASOPAC/Index?target=0 | UILAS 知识检索平台（ILAS 系 HTML OPAC，Tomcat/JSP） | `uilas/` 家族 + `adapters/cn/jinhua.py`；数据边界：借出无应还日期、裸 IP 仅 HTTP（443 证书过期）、详情页最大 870KB |
|  | 湖州 | — | ⛔ 不通 | https://www.hztsg.com/Cloud/Module/Index/index.html （湖州市图书馆） | — | 2026-10-03 实测：`www.hztsg.com` 解析到 **198.20.1.102 域名停放段**，80/443 端口均连接超时无响应字节；原登记 `www.hzlib.net` 亦不通。无可用检索入口 |
|  | 德清（县） | `deqing` | ✅ 接入 | http://opac.dqlib.com.cn/opac/index （德清县图书馆，湖州市辖） | 图创 Interlib（默认模板；HTML 检索页被「opac验证」拦，检索改走内嵌 Solr） | `interlib/` 家族 + `adapters/cn/deqing.py`（`api_detail=True`＋`solr_search=True`）；实抓「三体」55 条 |
|  | 嘉兴 | — | ⛔ 不通 | http://www.jxlib.net （嘉兴市图书馆） | — | — |
|  | 舟山 | `zhoushan` | ✅ 接入 | https://opac.zsodl.cn/Index?target=0 | UILAS 知识检索平台（与金华同款） | `uilas/` 家族 + `adapters/cn/zhoushan.py`；旧式 TLS quirk（只支持静态 RSA kx 套件，需显式放行，见家族章） |
|  | 衢州 | — | ⛔ 不通 | http://www.qzlib.net （衢州市图书馆） | — | — |
|  | 丽水 | `lishui` | ✅ 接入 | http://60.190.125.252:8086/opac/index | 图创 Interlib（已确认，pro2018 模板代；丽水市公共图书馆联合目录，含景宁/庆元/缙云等县馆） | `interlib/` 家族 + `adapters/cn/lishui.py`（`pro2018=True`，零 quirk） |
| 河北省 | 石家庄 | — | ⛔ 不通 | http://www.helib.net （河北省图书馆） | — | — |
|  |  | — | ⛔ 不通 | http://www.sjzlib.cn （石家庄市图书馆） | — | — |
|  | 唐山 | `tangshan` | ✅ 接入 | https://opac.tslib.net:7085/opac/ （唐山市图书馆） | 图创 Interlib（检索页滑动验证码，改走 Solr /api/search） | `interlib/` 家族 + `adapters/cn/tangshan.py`；实抓「三体」101 条 |
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
|  |  | — | 📋 计划 | http://opac.tylib.org.cn/opac/index （太原市图书馆） | 图创 Interlib（已确认） | 2026-10-03 用户提供；页标题「检索系统」、页内 interlib／opac/api，可立项接入 |
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
|  |  | `changchun` | ✅ 接入 | http://221.8.55.75:8888/opac/index （长春市图书馆） | 图创 Interlib（Solr 检索） | `interlib/` 家族 + `adapters/cn/changchun.py`；实抓「三体」171 条 |
|  | 吉林 | — | ⛔ 不通 | http://www.jllib.net （吉林市图书馆） | — | — |
|  | 四平 | — | ⛔ 不通 | http://www.splib.net （四平市图书馆） | — | — |
|  | 辽源 | — | ⛔ 不通 | http://www.lylib.net （辽源市图书馆） | — | — |
|  | 通化 | — | ⛔ 不通 | http://www.thlib.net （通化市图书馆） | — | — |
|  | 白山 | — | ⛔ 不通 | http://www.bslib.net （白山市图书馆） | — | — |
|  | 松原 | — | ⛔ 不通 | http://www.sylib.net （松原市图书馆） | — | — |
|  | 白城 | — | ⛔ 不通 | http://www.bclib.net （白城市图书馆） | — | — |
|  | 延边 | — | ⛔ 不通 | http://218.27.205.12:8099/opac/index （延边州图书馆） | — | 2026-10-03 实测 TCP 空响应（用户述不通） |
| 黑龙江省 | 哈尔滨 | `heilongjiang` | ✅ 接入 | http://lib.hljlib.org.cn:2333/opac/index （黑龙江省图书馆） | 图创 Interlib（Solr 检索） | `interlib/` 家族 + `adapters/cn/heilongjiang.py`；实抓「三体」70 条 |
|  | 齐齐哈尔 | — | ⛔ 不通 | http://www.qqhrlib.net （齐齐哈尔市图书馆） | — | — |
|  | 鸡西 | — | ⛔ 不通 | http://www.jxlib.net （鸡西市图书馆） | — | — |
|  | 鹤岗 | — | ⛔ 不通 | http://www.hglib.net （鹤岗市图书馆） | — | — |
|  | 双鸭山 | — | ⛔ 不通 | http://www.syslib.net （双鸭山市图书馆） | — | — |
|  | 大庆 | — | 📋 计划 | http://111.43.226.77:8091/opac/index （大庆市图书馆） | 图创 Interlib（已确认） | 2026-10-03 用户提供；页标题「检索系统」、页内 interlib，可立项接入 |
|  | 伊春 | — | ⛔ 不通 | http://www.yclib.net （伊春市图书馆） | — | — |
|  | 佳木斯 | — | ⛔ 不通 | http://www.jmslib.net （佳木斯市图书馆） | — | — |
|  | 七台河 | — | ⛔ 不通 | http://www.qthlib.net （七台河市图书馆） | — | — |
|  | 牡丹江 | — | ⛔ 不通 | http://www.mdjlib.net （牡丹江市图书馆） | — | — |
|  | 黑河 | — | ⛔ 不通 | http://www.hhlib.net （黑河市图书馆） | — | — |
|  | 绥化 | — | ⛔ 不通 | http://www.shlib.net （绥化市图书馆） | — | — |
|  | 大兴安岭 | — | ⛔ 不通 | http://www.dxallib.net （大兴安岭地区图书馆） | — | — |
| 福建省 | 福州 | `fujian_prov` | ✅ 接入 | https://opac.fjlib.net/opac/index （福建省图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/fujian_prov.py`；实抓「三体」127 条 |
|  |  | — | ⛔ 不通 | https://opcs.fzlib.org:8082/opac/ （福州市图书馆） | — | 2026-10-03 用户实测不通；本机复核 TLS 握手失败、域名解析至 198.20.2.5（域名停放段），不可用 |
|  | 厦门 | — | ⛔ 不通 | https://www.xmlib.net （厦门市图书馆） | — | — |
|  | 莆田 | — | ⛔ 不通 | http://www.ptlib.net （莆田市图书馆） | — | — |
|  | 三明 | — | ⛔ 不通 | http://www.smlib.net （三明市图书馆） | — | — |
|  | 泉州 | `quanzhou` | ✅ 接入 | http://218.66.169.78:85/opac/index （泉州市图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/quanzhou.py`；实抓「三体」103 条 |
|  | 漳州 | — | ⛔ 不通 | http://www.zzlib.net （漳州市图书馆） | — | 2026-10-03 有登记但实测为假站：原 `www.zzlib.net`→198.20.1.65、apex `zzlib.net`→198.20.2.61 均在域名停放段、TCP 空响应；用户所给 `www.fzlib.org`→198.20.0.209 亦停放段。故非「缺失」 |
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
|  | 景德镇 | — | ⛔ 不通 | http://www.jdzstsg.com （外源候选，实测域名停放） | — | 2026-10-03 解析至 198.20.2.20（域名停放段，与同批 .16–.24 连续）、TCP 空响应，非馆方站点 |
| 河南省 | 郑州 | `henan_prov` | ✅ 接入 | http://218.28.6.78:8081/ILASOPAC/Index?target=0 （河南省图书馆） | UILAS 知识检索平台（老版 HTML OPAC） | `uilas/` 家族 + `adapters/cn/henan_prov.py`；实抓「三体」57 条 |
|  |  | — | 📋 计划 | http://123.15.53.180:62280/client/zh_CN/default/? （郑州图书馆） | SirsiDynix Enterprise（页内 `com_sirsi_ent_widgets`，本仓库首见新家族，VSE Discovery） | 2026-10-03 用户确认可直接访问；JS 前端发现层，检索/详情接口待按 Enterprise 家族侦察接入 |
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
|  | 周口 | `zhoukou` | ✅ 接入 | http://222.136.172.30:8079/opac/index （周口市图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/zhoukou.py`；实抓「三体」20 条 |
|  | 驻马店 | — | ⛔ 不通 | http://www.zmdlib.net （驻马店市图书馆） | — | — |
| 湖北省 | 武汉 | — | 🔍 待核验 | https://www.library.hb.cn （湖北省图书馆） | — | — |
|  |  | — | 📋 计划 | https://opac.whlib.org.cn/opac/index （武汉图书馆） | 图创 Interlib（已确认） | 2026-10-03 用户提供；页标题「检索系统」、页内 interlib／opac/api，可立项接入 |
|  | 十堰 | — | ⛔ 不通 | http://www.sylib.net （十堰市图书馆） | — | — |
|  | 襄阳 | — | ⛔ 不通 | http://www.xylib.net （襄阳市图书馆） | — | — |
|  | 鄂州 | — | ⛔ 不通 | http://www.ezlib.net （鄂州市图书馆） | — | — |
|  | 荆门 | `jingmen` | ✅ 接入 | http://221.234.32.236:8081/opac/index （荆门市图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/jingmen.py`；实抓「三体」87 条 |
|  | 孝感 | `xiaogan` | ✅ 接入 | http://183.92.156.82:6061/opac/index （孝感市图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/xiaogan.py`；实抓「三体」96 条 |
|  | 荆州 | — | ⛔ 不通 | http://www.jzlib.net （荆州市图书馆） | — | — |
|  | 黄冈 | — | ⛔ 不通 | http://www.hhlib.net （黄冈市图书馆） | — | — |
|  | 咸宁 | — | ⛔ 不通 | http://www.xnlib.net （咸宁市图书馆） | — | — |
|  | 随州 | — | ⛔ 不通 | http://www.szlib.net （随州市图书馆） | — | — |
|  | 恩施 | — | ⛔ 不通 | http://www.eslib.net （恩施州图书馆） | — | — |
|  | 黄石 | `huangshi` | ✅ 接入 | http://61.184.117.12:8081/opac/index （黄石市图书馆） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/huangshi.py`（`api_detail=True`）；实抓「三体」54 条 |
|  | 宜昌 | — | ⛔ 不通 | https://www.yclibrary.cn （宜昌市图书馆） | 超星智慧门户（wisweb／chaoxing） | 2026-10-03 用户述页面全白；实测仅 2.5KB 超星门户壳，无书目检索入口 |
| 湖南省 | 长沙 | `hunan_prov` | ✅ 接入 | https://opac.library.hn.cn/opac/ （湖南图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/hunan_prov.py`；实抓「三体」176 条 |
|  |  | — | ⛔ 不通 | https://opac.changshalib.cn/opac/ （长沙图书馆） | 图创 Interlib | 2026-10-03 实测：`/opac/index`、`/opac/search`、`/opac/api/search` 全部 HTTP 403（整站 WAF 拦截程序化访问，带 cookie/Referer 亦 403），无可用入口 |
|  | 株洲 | `zhuzhou` | ✅ 接入 | http://218.75.211.12:8899/opac/index （株洲市图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/zhuzhou.py`；实抓「三体」222 条 |
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
| 海南省 | 海口 | `haikou` | ✅ 接入 | http://221.11.163.25:5656/opac/index （海口市图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/haikou.py`；实抓「三体」18 条。海南省图书馆 www.hilib.com 仍不通 |
|  |  | — | ⛔ 不通 | https://www.ucdrs.cn/area/hilib （海南省图书馆） | 超星 ucdrs 门户 | 2026-10-03 为超星 ucdrs 区域页、需登录，非匿名 OPAC（检索后跳 gdlink 404）；原 www.hilib.com 亦不通 |
|  |  | — | 📋 计划 | http://221.11.163.25:5656/opac/index （海口图书馆，与已接入的海口市图同一 Interlib 实例 `haikou`） | 图创 Interlib | 2026-10-03 用户提供此 Interlib 入口，与已接入 `haikou` 同 host 同源；如为同一馆可并入（另有官网 www.haikoulib.cn） |
|  | 三亚 | — | ⛔ 不通 | http://www.sanyalib.com （外源候选，实测域名停放） | — | 2026-10-03 解析至 198.20.2.21（域名停放段，与同批 .16–.24 连续）、TCP 空响应，非馆方站点 |
|  | 三沙 | — | ❓ 缺失 | — | — | — |
|  | 儋州 | — | ❓ 缺失 | — | — | — |
| 贵州省 | 贵阳 | — | ⛔ 不通 | https://ilas.gzlib.com.cn/opac/index （贵州省图书馆） | 图创 Interlib | 2026-10-03 实测：`/opac/index` HTTP 200，但 `/opac/search`（任意参数）恒 HTTP 500、`/opac/api/search` 亦 500——检索后端故障，暂不可用 |
|  |  | — | ⛔ 不通 | https://www.gylib.org.cn/entry （贵阳市图书馆） | — | 用户述需登录；2026-10-03 实测入口为登录/门户页，无可匿名检索的书目 OPAC |
|  | 六盘水 | — | ⛔ 不通 | http://www.lpslib.com （外源候选，实测域名停放） | — | 2026-10-03 解析至 198.20.2.22（域名停放段，与同批 .16–.24 连续）、TCP 空响应，非馆方站点 |
|  | 遵义 | `zunyi` | ✅ 接入 | http://opac.zylib.cn:82/opac/index （遵义市图书馆） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/zunyi.py`（`api_detail=True`）；实抓「三体」43 条 |
|  | 安顺 | — | ⛔ 不通 | http://www.asstsg.com （外源候选，实测域名停放） | — | 2026-10-03 解析至 198.20.2.23（域名停放段，与同批 .16–.24 连续）、TCP 空响应，非馆方站点 |
|  | 毕节 | — | ⛔ 不通 | http://www.bijlib.com （外源候选，实测域名停放） | — | 2026-10-03 解析至 198.20.2.24（域名停放段，与同批 .16–.24 连续）、TCP 空响应，非馆方站点 |
|  | 铜仁 | — | ❓ 缺失 | — | — | — |
|  | 黔西南 | — | ❓ 缺失 | — | — | — |
|  | 黔东南 | `qiandongnan` | ✅ 接入 | http://111.124.33.40:8088/opac/index （黔东南州图书馆） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/qiandongnan.py`（`api_detail=True`）；实抓「三体」77 条 |
|  | 黔南 | `qiannan` | ✅ 接入 | http://114.135.66.82:8082/opac/index （黔南州图书馆） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/qiannan.py`（`api_detail=True`）；实抓「三体」20 条 |
| 云南省 | 昆明 | — | 🔍 待核验 | http://metalsp.ynlib.cn:3006/ （云南省图书馆 MetaLSP 发现系统） | MetaLSP 发现系统 | 2026-10-03 实测入口 HTTP 200「MetaLSP发现系统」；底层书目接口未侦察 |
|  |  | — | ⛔ 不通 | http://ilasweb.kmlib.yn.cn/ （昆明市图书馆） | — | 2026-10-03 实测：域名无法解析（DNS 失败），入口待寻 |
|  | 曲靖 | `qujing` | ✅ 接入 | http://www.qjlib.com.cn:8088/opac/index （曲靖市图书馆） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/qujing.py`（`api_detail=True`）；实抓「三体」138 条 |
|  | 玉溪 | — | ⛔ 不通 | http://www.yxstsg.cn （外源候选，域名不存在） | — | 2026-10-03 DNS 无解析（NXDOMAIN），非馆方站点 |
|  | 保山 | — | ⛔ 不通 | https://bsstsg.superlib.libsou.com （保山市图书馆） | 超星 superlib 门户 | 2026-10-03 首页 200「保山市图书馆」，但站内无书目检索入口（用户亦述未找到） |
|  | 昭通 | — | ⛔ 不通 | http://www.csln.net/ztstsg/AjaxPanel.aspx （昭通市图书馆） | — | 2026-10-03 域名解析至 198.20.2.58（停放段）、TCP 空响应；用户述全白、仅小程序可查且需登录 |
|  | 丽江 | `lijiang` | ✅ 接入 | https://www.ljstsg.cn/opac/index （丽江市图书馆） | 图创 Interlib（已确认，meta keywords 自报；默认模板） | `interlib/` 家族 + `adapters/cn/lijiang.py`（`api_detail=True`）；实抓「三体」80 条 |
|  | 普洱 | — | ❓ 缺失 | — | — | — |
|  | 临沧 | `lincang` | ✅ 接入 | http://106.58.172.142:8081/opac/index （临沧市图书馆） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/lincang.py`（`api_detail=True`）；实抓「三体」31 条 |
|  | 楚雄 | `chuxiong` | ✅ 接入 | http://220.165.139.19:8082/opac/index （楚雄州图书馆） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/chuxiong.py`（`api_detail=True`）；实抓「三体」76 条 |
|  | 红河 | `honghe` | ✅ 接入 | http://182.246.32.25:83/opac/index （红河州图书馆） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/honghe.py`（`api_detail=True`）；实抓「三体」33 条 |
|  | 文山 | — | ⛔ 不通 | http://opac.whlibrary.cn:8088/ （文山州图书馆） | — | 2026-10-03 实测 TCP 空响应（用户述页面全白），无可匿名检索入口 |
|  | 西双版纳 | `xishuangbanna` | ✅ 接入 | http://106.58.209.101:8080/opac/index （西双版纳州图书馆） | 图创 Interlib（默认模板；HTML 检索页 HTTP 500，检索改走内嵌 Solr） | `interlib/` 家族 + `adapters/cn/xishuangbanna.py`（`api_detail=True`＋`solr_search=True`）；实抓「三体」18 条 |
|  | 大理 | — | ⛔ 不通 | https://dali.superlib.libsou.com/ （大理州图书馆） | 超星 superlib 门户 | 2026-10-03 官网 www.dalilib.cn（超星门户）与 superlib 门户均无书目检索入口，官网页面全白 |
|  | 德宏 | `dehong` | ✅ 接入 | http://36.140.104.72:8086/opac/index （德宏州图书馆） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/dehong.py`（`api_detail=True`）；实抓「三体」52 条 |
|  | 怒江 | `nujiang` | ✅ 接入 | http://106.58.214.4:8082/opac/index （怒江州图书馆） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/nujiang.py`（`api_detail=True`）；实抓「三体」9 条 |
|  | 迪庆 | — | ⛔ 不通 | https://diqingzhou.superlib.libsou.com/ （迪庆州图书馆） | 超星 superlib 门户 | 2026-10-03 返回「暂停页面」（站点维护中），无检索入口 |
| 陕西省 | 西安 | `shaanxi` | ✅ 接入 | https://uilas.sxlib.org.cn （陕西省图书馆，页标题「UILAS知识检索平台」） | 新版 UILAS（ILAS REST 平台，Vue 前端＋`/prod-api/*` JSON，与老版 UILAS 同宗不同代） | `uilas_rest/` 家族 + `adapters/cn/shaanxi.py`（省级馆，馆址西安） |
|  |  | `xian` | ✅ 接入 | https://opac.xalib.org.cn/opac3/index （西安市图书馆，西安市公共图书馆集群信息化管理平台） | 图创 Interlib（pro2018 模板，应用上下文 `/opac3`） | `interlib/` 家族 + `adapters/cn/xian.py`（`ctx=/opac3`、`pro2018=True`、`api_detail=True`） |
|  | 铜川 | — | 🔍 待核验 | https://uilas.sxlib.org.cn/#/index （铜川市图书馆，入口与陕图同平台） | 新版 UILAS（同陕图） | 用户所给入口即陕图省馆平台（`shaanxi`）；铜川馆专有检索入口待确认 |
|  | 咸阳 | `xianyang` | ✅ 接入 | http://61.185.20.96:8082/opac/index （咸阳市公共图书馆联盟） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/xianyang.py`（`api_detail=True`）；实抓「三体」79 条 |
|  | 宝鸡 | `baoji` | ✅ 接入 | http://1.82.133.119:8082/opac/ （宝鸡市公共图书馆集群信息化管理平台） | 图创 Interlib（默认模板） | `interlib/` 家族 + `adapters/cn/baoji.py`（`api_detail=True`）；实抓「三体」110 条 |
|  | 渭南 | — | ⛔ 不通 | http://www.wnlib.org.cn/ | — | 2026-10-03 实测：站点仅返 971 字节 Vue 壳、无检索入口（用户亦述「没查询入口」） |
|  | 延安 | — | ⛔ 不通 | https://ydlib.mh.chaoxing.com/ | 超星智慧门户 | 2026-10-03 实测：根路径 HTTP 400（13 字节），不可达 |
|  | 汉中 | `hanzhong` | ✅ 接入 | https://findhanzhong.libsp.cn/#/home | 图星 LibStar Find（JSON API） | `libstar/` 家族 + `adapters/cn/hanzhong.py`；`groupCode=100121`；实抓「三体」930 条 |
|  | 榆林 | `yulin` | ✅ 接入 | https://www.yulinlib.org.cn/opac/#/index | 新版 UILAS（ILAS REST 平台） | `uilas_rest/` 家族 + `adapters/cn/yulin.py`（Referer 须 `/opac/`）；实抓「三体」16 条 |
|  | 安康 | `ankang` | ✅ 接入 | http://219.145.206.134:8082/opac/index | 图创 Interlib（pro2018 模板） | `interlib/` 家族 + `adapters/cn/ankang.py`（`pro2018=True`、`api_detail=True`；详情页 HTML 被源站截断，改走 `/api/book/{}`）；实抓「三体」161 条 |
|  | 商洛 | — | ⛔ 不通 | https://shangluo.superlib.libsou.com/ | 超星（superlib/libsou） | 2026-10-03 实测：站点为超星发现页、无书目 OPAC 检索入口（用户亦述「没查询入口」） |
| 甘肃省 | 兰州 | — | 🔍 待核验 | http://search.gslib.com.cn/uhtbin/cgisirsi/ （甘肃省图书馆 iLink，仅查馆别＝省馆） | SirsiDynix iLink（同大连 ykt 家族） | 2026-10-03 入口 200 可达（页标题「iLink」；`ps=` token 会话地址、表单外链 `cgisirsi`）；JS 驱动，检索/详情/馆藏流程待侦察 |
|  |  | `lanzhou` | ✅ 接入 | http://36.137.50.135:8082/#/index （兰州市图书馆） | 新版 UILAS（ILAS REST 平台） | `uilas_rest/` 家族 + `adapters/cn/lanzhou.py`；实抓「三体」521 条 |
|  | 嘉峪关 | — | 🔍 待核验 | http://jygslib.com.cn （嘉峪关市图书馆） | 自研 Vue SPA（页标题仅「门户网站」） | 2026-10-03 入口可达(200)但页面无馆名、弱证；static/config.js 404，身份与 OPAC 待另行确证 |
|  | 金昌 | — | ⛔ 不通 | http://www.jctsg.com/ （金昌市图书馆） | — | 2026-10-03 解析至 198.20.2.53（域名停放段）、TCP 空响应 |
|  | 白银 | — | ⛔ 不通 | http://www.byslib.com/ （白银市图书馆） | — | 2026-10-03 解析至 198.20.2.54（域名停放段）、TCP 空响应 |
|  | 天水 | — | ⛔ 不通 | http://www.gstslib.com.cn （外源候选） | — | 2026-10-03 用户实测打不开；本机探测 DNS→125.74.52.173、TCP 可达但 HTTP 空响应，无可匿名检索入口 |
|  | 武威 | — | ⛔ 不通 | http://117.156.117.23:8083/CustCount/index （武威市图书馆） | — | 2026-10-03 入口 200 但页面全白（用户确认），无可匿名检索入口 |
|  | 张掖 | — | ❓ 缺失 | — | — | — |
|  | 平凉 | — | ⛔ 不通 | http://www.plslib.com/ （平凉市图书馆） | — | 2026-10-03 解析至 198.20.2.56（域名停放段）、TCP 空响应 |
|  | 酒泉 | — | ❓ 缺失 | — | — | — |
|  | 庆阳 | — | ❓ 缺失 | — | — | — |
|  | 定西 | — | ❓ 缺失 | — | — | — |
|  | 陇南 | — | 🔍 待核验 | — （无独立入口，借甘肃省图 iLink＋馆别过滤） | SirsiDynix iLink | 2026-10-03 无独立入口；用甘肃省图书馆 iLink OPAC 按馆别过滤查询，与省馆共用同一系统，待侦察 |
|  | 临夏 | — | ❓ 缺失 | — | — | — |
|  | 甘南 | — | 🔍 待核验 | — （无独立入口，借甘肃省图 iLink＋馆别过滤） | SirsiDynix iLink | 2026-10-03 无独立入口；用甘肃省图书馆 iLink OPAC 按馆别过滤查询，与省馆共用同一系统，待侦察 |
| 青海省 | 西宁 | — | ⛔ 不通 | http://www.qhlib.org （青海省图书馆） | — | — |
|  |  | — | 🔍 待核验 | https://www.xnlib.cn/ （西宁市图书馆） | 门户站 | 2026-10-03 实测门户页 HTTP 200（3.7KB），底层书目 OPAC 未侦察 |
|  | 海东 | — | 🔍 待核验 | https://hdtsg.cn/index.aspx （海东市图书馆） | 自研 ASP.NET（含 BibliographySearch.aspx） | 2026-10-03 入口/查询页 200，站内 `/BibliographySearch.aspx`、`/ClassifySearch.aspx` 书目检索页待侦察 |
|  | 海北 | — | ⛔ 不通 | http://hbztsg.cn:8088/ （海北州图书馆） | — | 2026-10-03 实测 TCP 空响应（用户述不通） |
|  | 黄南 | — | ❓ 缺失 | — | — | — |
|  | 海南州 | — | ❓ 缺失 | — | — | — |
|  | 果洛 | — | ⛔ 不通 | https://guoluo.superlib.libsou.com/ （果洛藏族自治州图书馆） | 超星 superlib 门户 | 2026-10-03 首页 200 但无书目检索入口（同商洛/保山） |
|  | 玉树 | — | ❓ 缺失 | — | — | — |
|  | 海西 | — | ⛔ 不通 | https://hxztsg.libsp.cn/ （海西州图书馆） | LibStar「新一代图书馆服务平台」（SPA） | 2026-10-03 首页 200 为 SPA 壳、需登录，未获匿名检索接口（用户述需登录） |
| 西藏自治区 | 拉萨 | — | ❓ 缺失 | — | — | — |
|  | 日喀则 | — | ❓ 缺失 | — | — | — |
|  | 昌都 | — | ❓ 缺失 | — | — | — |
|  | 林芝 | — | ❓ 缺失 | — | — | — |
|  | 山南 | — | ❓ 缺失 | — | — | — |
|  | 那曲 | — | ❓ 缺失 | — | — | — |
|  | 阿里 | — | ❓ 缺失 | — | — | — |
| 内蒙古自治区 | 呼和浩特 | `huhehaote` | ✅ 接入 | http://w.hhhtlib.org.cn:92/opac/index （呼和浩特市图书馆） | 图创 Interlib（Solr 检索） | `interlib/` 家族 + `adapters/cn/huhehaote.py`；实抓「三体」122 条 |
|  | 包头 | `baotou` | ✅ 接入 | https://opac.btslib.cn:8088/opac/index （包头市图书馆） | 图创 Interlib（Solr 检索） | `interlib/` 家族 + `adapters/cn/baotou.py`；实抓「三体」40 条 |
|  | 赤峰 | — | ⛔ 不通 | http://www.cflib.net （赤峰市图书馆） | — | — |
|  | 通辽 | `tongliao` | ✅ 接入 | http://60.31.181.203:8088/opac/ （通辽市图书馆） | 图创 Interlib | `interlib/` 家族 + `adapters/cn/tongliao.py`；实抓「三体」11 条 |
|  | 鄂尔多斯 | `eerduosi` | ✅ 接入 | http://1.183.72.92:8089/ordoslib （鄂尔多斯市图书馆） | 图创 tcc-opac（与宁波同款） | `tccopac/` 家族 + `adapters/cn/eerduosi.py`；实抓「三体」253 条 |
|  | 呼伦贝尔 | — | ⛔ 不通 | http://www.hlbrlib.net （呼伦贝尔市图书馆） | — | — |
|  | 巴彦淖尔 | — | ⛔ 不通 | http://www.bynrlib.net （巴彦淖尔市图书馆） | — | — |
|  | 乌兰察布 | — | ⛔ 不通 | http://58.18.107.6:18080/opac/search （乌兰察布市图书馆） | 图创 Interlib（待定） | 2026-10-03 实测：连接被重置（RemoteDisconnected），用户述不通；入口待寻 |
|  | 乌海 | `wuhai` | ✅ 接入 | http://1.24.223.177:8085/opac/index （乌海市图书馆） | 图创 Interlib（Solr 检索） | `interlib/` 家族 + `adapters/cn/wuhai.py`；实抓「三体」75 条 |
|  | 兴安盟 | — | ❓ 缺失 | — | — | — |
|  | 锡林郭勒盟 | — | 🔍 待核验 | http://58.18.112.198:8100/ （锡林郭勒盟图书馆） | ASP.NET「OPAC查询系统」（非 Interlib，系统待定） | 2026-10-03 首页 200、页标题「锡林郭勒盟图书馆OPAC查询系统」，响应慢（分块 33KB 逾 25s）；检索接口未侦察 |
|  | 阿拉善盟 | — | ❓ 缺失 | — | — | — |
| 广西壮族自治区 | 南宁 | — | 🔍 待核验 | https://opac.gxlib.org.cn/#/home （广西壮族自治区图书馆） | 新版 UILAS（待定，疑似） | 2026-10-03 实测：TLS 握手 EOF（OpenSSL 3.5 与 LibreSSL 均失败），需进一步侦察 |
|  |  | — | 🔍 待核验 | https://book.nnlib.com.cn/dss-portal/ （南宁市图书馆） | 未知（dss-portal） | 2026-10-03 实测入口 HTTP 200（Vue 壳），检索接口未侦察 |
|  | 桂林 | — | ⛔ 不通 | http://www.gll-gx.org.cn （广西壮族自治区桂林图书馆） | — | — |
|  | 柳州 | — | ⛔ 不通 | http://www.lzlib.net （柳州市图书馆） | — | — |
|  | 梧州 | — | ⛔ 不通 | http://www.wzlib.net （梧州市图书馆） | — | — |
|  | 北海 | — | ⛔ 不通 | http://www.bhlib.net （北海市图书馆） | — | — |
|  | 防城港 | — | ⛔ 不通 | http://www.fcglib.net （防城港市图书馆） | — | — |
|  | 钦州 | — | ⛔ 不通 | http://www.qzlib.net （钦州市图书馆） | — | — |
|  | 贵港 | — | ⛔ 不通 | http://www.gglib.net （贵港市图书馆） | — | — |
|  | 玉林 | — | ⛔ 不通 | http://www.yllib.net （玉林市图书馆） | — | — |
|  | 百色 | — | ⛔ 不通 | http://www.bslib.net （百色市图书馆） | — | — |
|  | 贺州 | — | ⛔ 不通 | http://222.218.248.23:8080/opac/ （贺州市图书馆） | 未知 | 2026-10-03 全路径自定义 403；另 https://www.hztsg.com:8282 解析至 198.20.1.102（停放段）TLS 失败，均不可用 |
|  | 河池 | — | ⛔ 不通 | http://222.218.124.59:8086/opac/ （河池市图书馆） | 未知 | 2026-10-03 自定义 403；原 www.hclib.org.cn 解析至私网 10.16.24.103、TCP 空响应 |
|  | 来宾 | `laibin` | ✅ 接入 | http://180.141.168.199:8086/opac/index （来宾市图书馆） | 图创 Interlib（已确认，默认模板） | `interlib/` 家族 + `adapters/cn/laibin.py`（`api_detail=True`）；实抓「三体」15 条 |
|  | 崇左 | — | ⛔ 不通 | https://opac.chzlib.org.cn:9002/opac/ （崇左市图书馆） | 未知（入口 `:9002/opac/`，疑图创 Interlib） | 2026-10-03 入口为真（馆方 www.chzlib.org.cn 首页直链此地址），但 `:9002` 全路径含静态 CSS 一律自定义 403「拒绝访问」（端口级 IP/地域白名单或 WAF；伪造 XFF／带 Referer/Cookie 均 403），本机不可程序化访问；馆网首页（超星门户，同 IP）200 |
| 宁夏回族自治区 | 银川 | — | 🔍 待核验 | http://www.nxlib.cn （宁夏图书馆） | — | — |
|  | 石嘴山 | — | ❓ 缺失 | — | — | — |
|  | 吴忠 | — | ❓ 缺失 | — | — | — |
|  | 固原 | — | 🔍 待核验 | http://www.gyslib.cn （固原市图书馆） | 超星智慧门户（wisweb／chaoxing） | 2026-10-03 用户述不通，但本机实测 200（标题「固原市图书馆」、超星门户，与广元/达州同 IP 124.243.227.8）；身份存疑、OPAC 未侦察 |
|  | 中卫 | — | ❓ 缺失 | — | — | — |
| 新疆维吾尔自治区 | 乌鲁木齐 | — | 🔍 待核验 | https://www.xjlib.org （新疆维吾尔自治区图书馆） | — | — |
|  | 克拉玛依 | — | ⛔ 不通 | https://www.klmylib.cn:8016/opac/ （克拉玛依市图书馆） | 未知 | 2026-10-03 全路径自定义 403（同崇左，端口级 IP/WAF 拦截） |
|  | 吐鲁番 | — | ⛔ 不通 | https://www.ucdrs.cn/area/tlfstsg （吐鲁番市图书馆） | 超星 ucdrs 门户 | 2026-10-03 为超星 ucdrs 区域页、需登录，非馆匿名 OPAC（同省图口径） |
|  | 哈密 | — | ❓ 缺失 | — | — | — |
|  | 昌吉 | — | ⛔ 不通 | http://222.80.229.116:8085/interlibSSO/main/ （昌吉回族自治州图书馆） | 图创 Interlib（SSO） | 2026-10-03 入口为 Interlib SSO 登录页（标题「昌吉回族自治州图书馆-登录」）；`/`、`/opac/*` 均 404，无可匿名检索入口 |
|  | 博尔塔拉 | — | ⛔ 不通 | https://www.ucdrs.cn/area/betltsg （博尔塔拉蒙古自治州图书馆） | 超星 ucdrs 门户 | 2026-10-03 同上（ucdrs 区域页、需登录） |
|  | 巴音郭楞 | — | ❓ 缺失 | — | — | — |
|  | 克孜勒苏 | — | ⛔ 不通 | https://www.ucdrs.cn/area/kztsg （克孜勒苏柯尔克孜自治州图书馆） | 超星 ucdrs 门户 | 2026-10-03 同上（ucdrs 区域页、需登录） |
|  | 伊犁 | — | ❓ 缺失 | — | — | — |
|  | 阿克苏 | — | ❓ 缺失 | — | — | — |
|  | 喀什 | — | ❓ 缺失 | — | — | — |
|  | 和田 | — | ⛔ 不通 | https://www.ucdrs.cn/area/htdqtsg （和田地区图书馆） | 超星 ucdrs 门户 | 2026-10-03 同上（ucdrs 区域页、需登录） |
|  | 塔城 | — | ❓ 缺失 | — | — | — |
|  | 阿勒泰 | — | ⛔ 不通 | http://60.13.230.143:8088/opac （阿勒泰地区图书馆） | — | 2026-10-03 实测 TCP 空响应（用户述不通） |

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
| 苏州（双源 `SZ`＋`SIP`） | 默认，另按源自建三原语（两源均默认模板、`/opac` 上下文） | **双源合并**（见「一城多源合并」）：苏州图书馆 `SZ`（`https://reader.szlib.com`）＋苏州工业园区图书馆 `SIP`（`http://opac.sdll.cn:8088`），两源与广州同款默认（非 pro2018）模板、结构逐项同构。SZ 详情页内嵌馆藏请求带 `jsessionid`＋`isCluster=false`，但家族 `isCluster=`（空）实测同样返回完整 holdingList、不依赖会话。SZ libcodeMap 4 项（`ST=苏图`…）、SIP libcodeMap 5 项（`SDLL=工业园区图书馆`…）。部分书目 `holdingList` 为空但 maps 齐全属记录级数据事实。`tests/fixtures/suzhou/NOTES.md`。 |
| 丽水 | `pro2018=True` | 裸 IP ＋ HTTP：base_url `http://60.190.125.252:8086`；pro2018 模板代（搜索条目 `libBookLi`，页内也带 `bookrecno`）。检索/详情/馆藏裸参数均通，不需要 `curlibcode`；不需要 `pro2018_cite_author`（author 直取「刘慈欣」）。全市联合目录：libcodeMap 含丽水市图书馆（`lsslib`）与景宁/庆元/缙云/遂昌/松阳/云和/青田等县馆及乡镇分馆、城市书房、阅读驿站。部分书目 holdingList 为空而 maps 齐全属记录级数据事实；详情记录无内容提要时 summary 空串。`tests/fixtures/lishui/NOTES.md`。 |
| 苏州工业园区（`suzhou` 第二源 `SIP`） | 默认（零 quirk，不需要 `curlibcode`） | `http://opac.sdll.cn:8088`（HTTP＋8088 端口），默认（非 pro2018）模板；检索/详情/馆藏裸参数均通。libcodeMap 仅 5 项（`SDLL=工业园区图书馆`、`999=中心馆`、`DAYTON=馆藏业务处理馆`、`SIPDSH=东沙湖学校图书馆`、`SZCYS=重元寺`）；网点含网借书库、星海高中、科技阅览室、东部市民中心分馆等。`tests/fixtures/suzhou/NOTES.md`。 |
| 西安（西安市图书馆） | `ctx="/opac3"`＋`pro2018=True`＋`api_detail=True` | 西安市公共图书馆集群信息化管理平台，应用上下文**是 `/opac3` 非 `/opac`**（家族 `ctx` 字段的第二个城市，首个是合肥市图 `/lib2`）。pro2018 模板；详情走 `/api/book/{recno}` JSON。集群含碑林区图书馆等成员馆。`tests/fixtures/xian/NOTES.md`。 |
| 咸阳 | `api_detail=True` | 咸阳市公共图书馆联盟（`http://61.185.20.96:8082`），默认（非 pro2018）模板；详情走 `/api/book/{recno}` JSON。联盟含兴平图书馆等。`tests/fixtures/xianyang/NOTES.md`。 |
| 宝鸡 | `api_detail=True` | 宝鸡市公共图书馆集群平台（`http://1.82.133.119:8082`），默认模板；详情走 `/api/book/{recno}` JSON。含「宝图-工人文化宫分馆」等网点。`tests/fixtures/baoji/NOTES.md`。 |
| 安康 | `pro2018=True`＋`api_detail=True` | pro2018 模板；**详情页 HTML 被源站截断**（实测稳定停在 ~67597 字节、无书目表），故 `api_detail=True` 走 `/api/book/{recno}` JSON；馆藏 `/api/holding/{recno}` 正常。`tests/fixtures/ankang/NOTES.md`。 |

**`api_detail` quirk（2026-10-03）**：`/api/book/{recno}`（各 Interlib 站点均提供）
返回 `{biblios:{title,author,publisher,pubdate,isbn,classNo,summary,…}, holdings:[…]}`
的书目 JSON，比 HTML 详情页更稳（不受模板差异与页面截断影响）。`api_detail=True`
的省份详情走该接口；**注意它返回的 holdings 是原始馆码未翻译**，故馆藏仍统一走
`/api/holding/{recno}`（含 libcodeMap/localMap/holdStateMap 映射）。

**`solr_search` quirk（2026-10-03）**：一批 Interlib 站点的 HTML 检索页
`/opac/search` 被滑动验证码常态拦截（返回 ~3.3KB「opac验证」页），但站点内嵌的
Solr 后端 `GET /api/search` 开放且不经验证码（与青岛同通道）。`solr_search=True`
时检索走该通道：`q`/`rows`/`page`/`wt=json`，命中数 `response.numFound`，书目在
`response.docs[]`（`title_meta`/`author_meta`/`publisher_meta`/`pubdate_meta`/
`isbn_meta`），稳定 id 为 `docs[].id`，解析用家族 `parser.parse_solr`；分页服务端
凭 `page` 自算。青岛为历史独立实现，其余 Solr 站点走本 quirk。**`docs[]` 字段可为
`null`**（德清实测 `isbn_meta`/`pubdate_meta` 均有 null），`parse_solr` 已统一按空串
处理（2026-10-03 修复，此前仅对全非空文档生效）。

**第二批成员（2026-10-03，均默认模板＋`api_detail=True`）**：海口 `haikou`、
株洲 `zhuzhou`、孝感 `xiaogan`、荆门 `jingmen`、湖南图书馆 `hunan_prov`、
福建省图书馆 `fujian_prov`、阳江 `yangjiang`、淄博 `zibo`、德州 `dezhou`、
周口 `zhoukou`、泉州 `quanzhou`、通辽 `tongliao`、河源 `heyuan`（HTML 检索页直连）；
黑龙江省图书馆 `heilongjiang`、长春 `changchun`、唐山 `tangshan`、包头 `baotou`、
乌海 `wuhai`、呼和浩特 `huhehaote`、潮州 `chaozhou`（`solr_search=True`）。各城
实抓总量与首条见对应 `tests/fixtures/<city>/NOTES.md`。来宾 `laibin`（2026-10-03
立项城市落地，默认模板＋`api_detail=True`，HTML 检索页直连；实抓「三体」15 条）同批。

**第三批成员（2026-10-03，均默认模板＋`api_detail=True`）**：黄石 `huangshi`、遵义
`zunyi`、黔东南 `qiandongnan`、黔南 `qiannan`、曲靖 `qujing`、临沧 `lincang`、楚雄
`chuxiong`、红河 `honghe`、德宏 `dehong`、怒江 `nujiang`（HTML 检索页直连）；德清
`deqing`、西双版纳 `xishuangbanna`（检索页被「opac验证」拦／HTTP 500，`solr_search=True`）。
各城实抓总量与首条见对应 `tests/fixtures/<city>/NOTES.md`。该批暴露的家族问题：
HTML 检索页命中数 > 0 时「下一页」锚点恒渲染（末页也 `has_next=True`，以
`total_pages` 为准）；德清 Solr 文档含 null 字段，`parse_solr` 已按空串修复。

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

## tcc-opac 家族（宁波、济南、鄂尔多斯）

家族模块 `tccopac/`：`client.py`（HTTP 层＋4 秒/host 节流＋访客令牌缓存）、
`parser.py`（检索/详情/馆藏 JSON 解析）、`__init__.py`（三原语与 `TccOpacConfig`）。
成员：宁波市图书馆（`adapters/cn/ningbo.py`）、济南市图书馆（`adapters/cn/jinan.py`）、
鄂尔多斯市图书馆（`adapters/cn/eerduosi.py`）。tcc-opac 与 Interlib 是不同产品线，
不可复用 `interlib/` 家族。城市差异只允许以带默认值的 `TccOpacConfig` 字段新增。
base_url 形态 `{host}/api/tcc-opac/{首段路径}`（前端 `getBaseUrl()` 逆向）。
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

## UILAS 家族（金华、舟山）

家族模块 `uilas/`：`client.py`（HTTP 层＋4 秒/host 节流＋可选旧式 TLS 兜底）、
`parser.py`（检索结果页／详情页／内联馆藏表解析）、`__init__.py`（三原语与
`UilasConfig`）。成员：金华市图书馆（`adapters/cn/jinhua.py`）、舟山市图书馆
（`adapters/cn/zhoushan.py`）、河南省图书馆（`adapters/cn/henan_prov.py`）。城市差异只允许以 `UilasConfig` 带默认值的字段
（quirk）新增，默认值即金华行为。UILAS 知识检索平台（ILAS 系 HTML OPAC，
Tomcat/JSP），全链路匿名零 cookie。

- **检索**：POST `NTRdrBookRetr.do`（`searchType`/`searchKey`）；ISBN 形态路由
  `searchType=isbnsrh`（带/不带连字符均命中），其余走任意词；总数「共有 [N]条记录」，
  空结果页括号为空（`共有 []条记录`）→ total=0，总数锚点整体缺失＝非结果页，报错。
- **翻页 quirk**：GET 带 `nCurrentpage`，**SearchKey 双重 URL 编码**（页内翻页链接原样
  `%25E4%25B8%2589…`），适配器复刻二次编码。
- **book_id＝裸 recno**（纯数字，无 tablename 前缀——与深圳/重庆 `{table}:{id}` 形态
  不同），非纯数字直接报错。
- **详情**：GET `NTRdrBookRetrInfo.do?recno=`（标记「书目详细信息」）；详情页标题可能
  短于列表页（原值照登不对齐）；出版时间可为民国纪年（publish_year 提取公历，提不到
  空串不猜）；ISBN「书号不详」原值照登。
- **馆藏**：在 `div#BookHolding` 内（BookHolding 之前的两个 `table.table` 是 CADAL
  数字图书表、常为空 tbody，**别当馆藏解析**——调研笔记此处有误已修正）；只有入藏
  复本时单表「馆藏信息」，有借出才出现「已外借馆藏」两表；状态词表仅
  「入藏（可借）/借出（不可借）」，词表外保守。
- **简介**：调研称「恒空」被实抓否定——详情页有内联「附注提要」块，summary 取其原值
  （上海「附注」回退同款思路）；`getBookCatalog.do` 仍不接。
- **数据边界**：借出单册无应还日期（due_date=""，站方访客视角不提供，不猜）。
- **旧式 TLS quirk（舟山，2026-10-03）**：`opac.zsodl.cn` 只支持**静态 RSA 密钥交换**
  的 TLS 1.2 套件（协商为 `TLS_RSA_WITH_AES_256_GCM_SHA384`），不支持 ECDHE；
  OpenSSL 3.5 默认密码列表已停用静态 RSA kx，`urllib` 默认上下文直接回
  `SSLV3_ALERT_HANDSHAKE_FAILURE`（curl/LibreSSL 可通、Python 不可）。配置
  `UilasConfig.ssl_ciphers="AES256-GCM-SHA384:AES128-GCM-SHA256"`，家族 HTTP 层用
  `set_ciphers()` 显式放行并按串缓存 opener；金华是裸 IP 纯 HTTP，不受影响。
- **各城差异**：金华入口 http://202.101.180.43/ILASOPAC/Index?target=0（裸 IP，
  **仅 HTTP**：443 证书已过期）；舟山入口 https://opac.zsodl.cn/Index?target=0（HTTPS，
  带上述 TLS quirk）。两城页面结构逐项同构，家族 parser 零改动。
- 字段侦察与出入清单见 `tests/fixtures/jinhua/NOTES.md`、`tests/fixtures/zhoushan/NOTES.md`。

## 新版 UILAS REST（陕西省图书馆、榆林）

家族模块 `uilas_rest/`：`client.py`（HTTP 层＋`Referer` 必需头＋节流）、
`parser.py`（检索/详情/馆藏 JSON 解析）、`__init__.py`（三原语与
`UilasRestConfig`）。成员：陕西省图书馆（`adapters/cn/shaanxi.py`）、榆林市图书馆
（`adapters/cn/yulin.py`）、兰州市图书馆（`adapters/cn/lanzhou.py`）、江门市图书馆
（`adapters/cn/jiangmen.py`）。与老版 `uilas/`（HTML OPAC，`NTRdrBookRetr.do`）
**同宗不同代**：新版是前后端分离的 REST 平台（前端 Vue），接口在 `/prod-api/*`
（nginx 映射后端 `/ILASOPAC/*`），返回 JSON，故独立成家族。城市差异只允许以
`UilasRestConfig` 带默认值的字段新增。

- **检索**：`GET /prod-api/bookSearch/search`，参数 `searchKey`/`pageNum`/`pageSize`
  （`pageSize` 服务端生效）。响应 `data.pageList.list[]`（条目）＋
  `data.pageList.totalElements`（总数）＋ `totalPages/currentPage`。
- **详情＋馆藏一步**：`GET /prod-api/book/bookDetail?recno={id}`。书目在
  `data.bookDetail`（`name/author/publish/pubyear/isbn/classno/contents/publish…`），
  馆藏在 `data.inList[]`（`status/callno/curlib/curlocal/retudate/cirtype/barcode`），
  馆名表 `data.libraryList`。`book_id` 即裸 `id`（数字字符串）。
- **馆藏状态码**（前端 i18n `bookinfo_hold_status_*`）：`a=采编 / b=在馆 / c=借出 /
  d=租出 / e=预约`；**只有 `b`（在馆）视为可借**，其余与未知码保守不可判借。
- **必需 `Referer`**：部分部署（榆林）只认与站点同路径的 Referer——榆林须
  `https://www.yulinlib.org.cn/opac/`，用根路径 `/` 时**所有 `/prod-api/*` 接口**
  都回 `{"code":401,"msg":"…认证失败…"}`（接口本身匿名可通，401 是 Referer 门，
  实测）。故 `UilasRestConfig.referer` 逐站配置。
- **数据边界**：检索条目的可借概况由 `holdingCount`（总册）/`inHoldingCount`（在馆）
  拼装；`bookDetail.contents`（提要）可为 null → summary 空串；`retudate` 为 `null`
  或 `"0"` 时 `due_date` 空串。
- 字段侦察结论见 `tests/fixtures/shaanxi/NOTES.md`、`tests/fixtures/yulin/NOTES.md`。

## 图星 LibStar Find（无锡、徐州、盐城、淮安、汉中）

家族模块 `libstar/`：`client.py`（HTTP 层＋`Referer`/`groupcode` 必需头＋节流）、
`parser.py`（检索/详情/馆藏解析）、`__init__.py`（单实例三原语与 `LibStarConfig`）。
成员：无锡市新吴区图书馆（`adapters/cn/wuxi.py`，单实例＋多源预留）、徐州
（`adapters/cn/xuzhou.py`）、淮安（`adapters/cn/huaian.py`）、盐城
（`adapters/cn/yancheng.py`）、汉中（`adapters/cn/hanzhong.py`，`groupCode=100121`）。
城市差异只允许以 `LibStarConfig` 带默认值的字段新增。
技术组件是图星 LibStar Find v3.2023.12（北京图星/超星集团），与图创 Interlib 是
两家厂商，不共用代码；家族 client 节流 1 秒/host。

**四城同协议、同字段**：检索 `POST /find/unify/search` 固定请求体，结果
`recordId/title/author/publisher/publishYear/isbn/physicalCount/onShelfCountI`
逐项同形；同样必须带 `groupcode` 头，缺则静默 0 结果。租户号可由 `POST
/find/homePage/getGroupCode {mappingPath}` 查得（`data.groupCode`）。已调通实测：
「三体」无锡 407、徐州 407、淮安 3110、盐城 857 条；四城均已接入。

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
- **盐城（`yancheng`）差异（均无需新 quirk）**：单实例单馆（馆藏分组只有
  `盐城市图书馆`），无多源归并，`book_id` 即裸 `recordId`；其余（域名、状态词表、
  日期内嵌）与无锡/徐州/淮安一致。侦察结论见 `tests/fixtures/yancheng/NOTES.md`。
- 字段侦察、状态词表样本与 fixture 清单见 `tests/fixtures/{wuxi,xuzhou,huaian,
  yancheng}/NOTES.md`。

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
| 苏州 `suzhou` | 苏州图书馆 `SZ`、苏州工业园区图书馆 `SIP` | SZ > SIP（市级主馆在前） |

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
