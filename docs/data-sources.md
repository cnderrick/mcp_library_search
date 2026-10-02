# 数据源清单

各城市图书馆的线上入口、系统技术组件与接入要点。**新增城市先在总览表登记一行**，实现细节追加到对应小节。

> 引用约定：本文与 `tests/fixtures/*/NOTES.md` 中出现的 `docs/team/research/*.md` 调研笔记为**本地存档**（`.git/info/exclude` 排除，不随仓库分发）；各笔记的关键结论均已照实摘录进本文对应条目与 NOTES.md，外部读者无需原文即可理解全部登记依据。

## 总览

同一省份的城市排在一起，省份列只在该省首行填写（视觉上等同于合并单元格），新增城市时接在本省行之后。

| 省份 | 城市 | 标识 | 线上图书馆入口 | 技术组件 | 适配层位置 |
|---|---|---|---|---|---|
| 上海市（直辖市） | 上海 | `shanghai` | https://vufind.library.sh.cn | VuFind（上海中心图书馆"一卡通"总分馆体系，900+ 网点） | `vendor/shanghai_library/` + `adapters/shanghai.py` |
| 北京市（直辖市） | 北京 | — | https://primo.clcn.net.cn/ （首都图书馆） | Ex Libris Primo classic（整域名网宿 WAF：HTTP 200＋33KB JS 验证页，覆盖 80/443/1701 三端口与三类 API；主站与 bplisn.net.cn 均无独立检索后端，表单全部外链 Primo） | 🔜 搁置：WAF 拦截程序化访问、无替代入口 |
|  |  | — | http://opac.nlc.cn/F/ （国家图书馆） | Ex Libris ALEPH 5.20（与天津同款家族；检索码 NLC01/NLC09；仅 HTTP，HTTPS 不通） | 🔍 待定：首页可达，但同 IP 连续请求触发 empty reply、需冷却 ≥20 秒，find-m 结果页未走通；需 ≥30 秒/请求的冷启动全流程稳定性验证，通过可照天津 ALEPH 经验接入 |
| 天津市（直辖市） | 天津 | `tianjin` | http://opacwh.tjl.tj.cn:8991/F （主馆） | Ex Libris ALEPH 20.1 www_f_chi | `adapters/tianjin.py`（三源合并） |
|  |  |  | http://opacse.tjl.tj.cn:8991/F （少儿馆） | 同款 ALEPH（独立 host 独立 base） |  |
|  |  |  | http://sm.interlib.cn:8104 （中新友好） | 图创 Interlib（租户 STC001） |  |
| 重庆市（直辖市） | 重庆 | `chongqing` | http://222.177.237.197:8080/InDigLib/frontV2/SearchIndex!simple.action?opacType=local | InDigLib 集群数字图书馆（Struts2+Solr） | `adapters/chongqing.py`（独立实现） |
| 安徽省 | 合肥 | `hefei` | https://opac.ahlib.com/opac/index （安徽省图书馆） | 图创 Interlib（已确认，与穗杭完全同模板） | `interlib/` 家族 + `adapters/hefei.py`（双源合并：皖图 `AH:` ＋ 市图 `HF:`，天津口径） |
|  |  |  | https://opac.hflib.org.cn/lib2/ （合肥市图书馆） | 图创 Interlib（已确认，同模板；应用上下文是 `/lib2` 非 `/opac`，`/opac/*` 返回 nginx 500） |  |
| 广东省 | 广州 | `guangzhou` | https://opac.gzlib.org.cn | 图创 Interlib | `interlib/` 家族 + `adapters/guangzhou.py` |
|  | 深圳 | `shenzhen` | https://www.szlib.org.cn/opac/ | 图书馆之城自研 JSON API（后端 ILAS，167 馆统一平台） | `adapters/shenzhen.py`（独立实现） |
| 江苏省 | 南京 | — | https://opac.jslib.org.cn/F/ （南京图书馆/江苏省图） | Ex Libris ALEPH（外层 openresty 全局验证码墙） | 🔜 搁置：首次访问即触发验证码墙（Nginx 层拦截，非限速型、节流不可规避）；替代入口排查：主站「全省馆藏书目」指向的 `gqcx.jstsg.org.cn` 为原型站（无生产数据、后端需账户），省级统一检索无公开入口，已接入的 `nanjing` 联合目录不含南图 |
|  |  | `nanjing` | http://uopac.jllib.cn/uopac/s/search.action （金陵图书馆联合目录，金陵运营，覆盖金陵＋12 区馆） | 汇文 uopac 区域联合 OPAC（Struts2；金陵自研 PHP OPAC `opac.jllib.cn/opac/*` 整体登录墙不可用，勿当入口） | `adapters/nanjing.py`（独立实现，单源＝联合目录，原生数字 book_id 不加前缀；南图 ALEPH 将来解锁照天津模式加源合并） |
|  | 扬州 | — | http://ytlmopac.cn:8080/uopac/s/search.action | 汇文 Libsys/uopac（Struts2，已确认） | 🔜 搁置：站点部署 JS AES 加密 Cookie 反爬（securitycam），所有路径仅返回 2.5KB JS 壳，需浏览器引擎或逆向才能接入 |
|  | 江阴 | `jiangyin` | http://libopac.jylib.cn:9090/opac/index | 图创 Interlib（已确认，与广州同模板、零 quirk，自建单租户） | `interlib/` 家族 + `adapters/jiangyin.py` |
|  | 无锡（新吴区） | — | http://wxxqlsp.xw.i-wnd.cn:8013/#/home | 图星 LibStar Find v3.2023.12（北京图星/超星系，300+ JSON API 端点） | 🔜 搁置：所有检索类端点返回 `errCode:9999`「系统访问中断」（下游 OPAC 不可达，服务端问题） |
| 辽宁省 | 大连 | `dalian` | 超星入口 http://www.dl.superlib.net/ （搁置）；**在用入口** http://ykt.dl-library.net.cn/ （大连地区网上联合目录） | SirsiDynix iLink（`/uhtbin/cgisirsi/`，本仓库首见新家族，与成都不同家族不共享模块）；原超星入口 IP 白名单硬墙 | `adapters/dalian.py`（独立实现；ps token＋会话 cookie 每请求变、全程同 cookie jar，类重庆会话流程；节流 ≥4 秒/host） |
| 山东省 | 青岛 | — | http://124.129.202.157/opac/index | 图创 Interlib（站点自报「青岛市公共图书馆联合目录」，26 馆联合，主馆馆码 QT） | 🔜 搁置：检索入口 `/opac/search` 被滑动验证码常态拦截（slideVerify，新会话首请求即触发，非限速型）；详情 `/opac/book/{id}` 与馆藏 `/opac/api/holding/{id}` 开放且家族 parser 零改动兼容，检索通道若可用即可快速接入 |
| 四川省 | 成都 | `chengdu` | https://opac.cdclib.cn/opac/index （成都市公共图书馆联合书目检索；原超星入口 books.gdlink.net.cn IP 白名单硬墙仍搁置） | 图创 Interlib（已确认，pro2018 模板代 simple 皮肤；meta keywords 自报图创 interlib） | `interlib/` 家族（HTTP/检索参数/馆藏 JSON 原样复用）＋ `adapters/chengdu.py`（搜索/详情 pro2018 模板解析适配器内本地实现，台州同款路径；自带 ≥2 秒节流） |
| 浙江省 | 杭州 | `hangzhou` | https://my1.zjhzlib.cn （杭州图书馆） | 图创 Interlib（与广州同模板） | `interlib/` 家族 ＋ `adapters/hangzhou.py`（双源合并，杭图 `HZ:`） |
|  |  |  | https://www.zjlib.cn/ （浙江图书馆，BFF 网关 `/bff-api/`） | 自研微服务（已确认；Nuxt 3＋Java/Spring＋ES，纯 JSON、无需鉴权；省级馆，6 馆区） | `adapters/_zjlib.py`（浙图 `ZJ:`，天津模式并入 `hangzhou`） |
|  | 宁波 | `ningbo` | https://opac.nblib.cn/999 | 图创 tcc-opac（已确认；Java/Spring＋Vue2 SPA，纯 JSON＋JWT 访客令牌，与 Interlib 不同产品线，不可复用家族） | `adapters/ningbo.py`（独立实现；真实检索端点为 `POST /search/` 尾斜杠形态——`bookSearch` 是开放平台端点、参数形态不同且长期「系统异常」，勿混用）；数据边界：聚合条目可能无本地书目（详情空属正常）、馆藏一页 500 册封顶 |
|  | 温州 | `wenzhou` | https://opac3.wzlib.cn/opac/index | 图创 Interlib（已确认，与广州同模板；站点为温州市图书馆，全市总分馆 91 馆） | `interlib/` 家族 + `adapters/wenzhou.py` |
|  | 绍兴 | `shaoxing` | https://opac.sxlib.com/opac/index | 图创 Interlib（已确认，pro2018 模板代；「绍兴市公共图书馆联合目录」，主馆绍兴图书馆） | `interlib/` 家族（HTTP/检索参数/馆藏 JSON 原样复用）＋ `adapters/shaoxing.py`（搜索/详情 pro2018 解析在适配器内本地实现，台州同款路径） |
|  | 台州 | `taizhou` | https://opac.tzlib.cn:8182/opac/index | 图创 Interlib（已确认，pro2018 新版模板变体；台州市图书馆，浙江地级市馆，含 S1 线地铁站等全市通借网点） | `interlib/` 家族（HTTP/检索参数/馆藏 JSON 原样复用）＋ `adapters/taizhou.py`（搜索/详情 pro2018 模板解析在适配器内本地实现） |
|  | 金华 | `jinhua` | http://202.101.180.43/ILASOPAC/Index?target=0 | UILAS 知识检索平台（ILAS 系 HTML OPAC，Tomcat/JSP，与深圳的自研 JSON API 封装不同，不可复用） | `adapters/jinhua.py`（独立实现，HTML 解析，匿名全链路）；数据边界：借出无应还日期、裸 IP 仅 HTTP（443 证书过期）、详情页最大 870KB |

## 上海（VuFind）

vendor 组件 shanghai-library-book-search-python（Apache-2.0），细节与本地补丁记录见根 [NOTICE](../NOTICE)。

- 检索总条数：站点统计区不再输出（`total_results` 恒为 0），adapter 按"0 且当前页有结果 → 视为未知（null）"处理，不属于代码 bug。
- 简介：站点没有独立简介区块，内容简介以书目"附注"字段（MARC 500）形式给出，vendor 补丁将 summary 回退到附注（见 NOTICE 变更）。
- 应还日期：馆藏页不直接渲染归还日期，已借出馆藏的 `<a class="item-return-date">` 只带单册 `data-itemid`，需按条调用 `AJAX/JSON?method=itemReturnDate`（vendor 提供 `get_return_date`，adapter 负责逐个补 `due_date`）。
- 同步上游：上游是平铺 import，已改为包内相对导入；覆盖同名文件同步后必须重新应用该修改。本地补丁（parser 的 has_next、library_client 的 statistics）同步后检查是否需重打，并在 NOTICE 变更里记一笔。

## Interlib 家族（广州、杭州、江阴、温州）

`src/mcp_library_search/interlib/` 是一方共享代码：`client.py`（HTTP）、`parser.py`（搜索页/详情页 HTML + 馆藏 JSON）、`__init__.py`（三原语，对外签名冻结）。结构事实以广州 fixture 为基准（`tests/fixtures/guangzhou/NOTES.md`），杭州的结构兼容性钉在 `tests/test_hangzhou_compat.py`。

- 搜索页：每条结果是 `bookmeta` 容器（`bookrecno` 即 `book_id`），字段按 class 锚点提取（title-link/author-link/publisher-link）；总数"检索到: N 条结果"（带千分位逗号）；分页"共 N 页" + 「下一页」锚点存在与否。
- 详情页：书目在 `bookInfoTable` 两列表格（leftTD 标签 / rightTD 值）；**没有独立索书号字段**，`call_number` 取"中图分类法"值；简介取"内容提要"；标题在首个 `<h2>`。
- 馆藏：不在详情页 HTML 内联，走 Ajax JSON 接口 `/opac/api/holding/{bookrecno}`；馆码/位置码/状态码分别经 `libcodeMap`/`localMap`/`holdStateMap` 翻译，查不到回退码本身。
- 应还日期：借出单册在 `loanWorkMap[barcode].returnDate`（epoch 毫秒，按 UTC+8 解释，与馆方系统时区一致），退回单册 `loan` 字段保守提取。
- 可借分类：`is_available_status` 状态词表——命中不可借词优先，命中可借词次之，都不中**保守判不可借**（未识别状态不让读者白跑）。
- 杭州差异（quirk）：与广州同模板（详情页 JS 甚至带广州分支函数）；「馆藏浏览」锚点缺失（用「馆藏地点」）；空结果页含 `bookDetail(` 的 JS 函数定义，解析必须按 `bookDetail(数字` 匹配，不能裸数出现次数。
- 江阴差异：与广州同模板、**零 quirk**（本地自建单租户，不需要 curlibcode）；HTTP 明文 + 9090 端口（base_url=`http://libopac.jylib.cn:9090`）；与杭州一样无「馆藏浏览」锚点；空结果页比杭州更干净（连 `bookDetail(` 函数定义都没有）；馆名两名并存原值照登——页内全称「江阴市图书馆」、libcodeMap[JYLIB] 译名「江阴图书馆」；网点含农家书屋等 24H 服务点（libcodeMap 实证，`tests/fixtures/jiangyin/NOTES.md`）。
- 温州差异：本地部署，curlibcode 默认空（首页 28 处 curlibcode 是模板 JS 的「限定所在馆」筛选逻辑）；首页 675KB 偏大是 91 馆/2555 地点筛选区全量服务端渲染，三端点与广州基准同构；部分书目有独立「索书号」行（data-sort=130，词表外不参与解析，call_number 维持取「中图分类法」，完整索书号以馆藏 JSON callno 为准）；「主要责任者」「内容提要」行是记录级可选，缺失则 author/summary 空串（数据边界）；主馆馆码 WT（温图市府路馆），纯电子书书目 holdingList 为空属正常。
- 详情页 tagTr 污染缺陷已修复（2026-10-02，江阴/温州各自独立实证）：「标签」行左格是裸 `<td>` 无 leftTD，其值「没有标签」曾挂到上一个已消费标签名下（污染 author 或 call_number）——穗杭 fixture 恰有「次要责任者」行重置才从未触发，**任何家族城市缺责任者行的记录都会命中**。修复口径：`_finish_value` 标签与值一对一消费（消费即清空 `_label`），钉在 `tests/test_jiangyin_parser.py` 与 `tests/test_wenzhou_compat.py`。
- 绍兴（`opac.sxlib.com`）确属家族但跑 **pro2018 模板代**，搜索/详情两个解析面与穗杭基准不兼容（`libBookUl`/`bkTxtTit` 结构）——**2026-10-02 已按台州同款「适配器本地解析」路径接入**（`adapters/shaoxing.py`，未动家族共享模块）；联合目录 holding 取数口径见 `tests/fixtures/shaoxing/NOTES.md`。
- 台州是 **pro2018 新版模板变体的已接入实证**：HTTP 层/检索参数集/馆藏 JSON 与广州基准同构（家族原样复用），仅搜索/详情两页解析放 `adapters/taizhou.py` 本地（结构对齐家族 parser）——pro2018 城市**不必动家族共享模块**即可交付。家族化候选提案（未合入，patch 存档于台州交付报告）：`InterlibConfig.search_template/detail_template` 判别字段 + parser 并行分支；`InterlibConfig.ctx` 上下文路径字段（默认 `/opac`，合肥市图 `/lib2` 实证需要，目前 hefei.py 内本地实现单源三原语）——出现第二个同形态城市时再家族化，避免投机抽象。**2026-10-02 成都接入后该条件已满足**（pro2018 第二城，台州解析器对成都 fixture 零修改全兼容），家族化执行安排在 batch3/批 4 合并收口之后，避免与在制批次产生共享文件冲突。
- 新接同族城市：`adapters/<city>.py` 照广州/杭州同款 `_client` 形态 + 在 `adapters/__init__.py` 注册 + 在本文件总览表登记。城市差异以带默认值的 `InterlibConfig` 字段（quirk）表达，默认值即广州行为。

## 深圳（自研 JSON API）

`adapters/shenzhen.py` 独立实现（与 Interlib 无关），轻量 client（urllib + json）内置在模块内。

- 接口：`getQueryResult`（搜索，真实总数 `numFound`）、`getBookDetail`（书目详情 + 三桶馆藏）。`book_id = "{tablename}:{recordid}"`，详情接口需成对传 `metaTable`/`metaId`。
- 检索策略：关键词判为 ISBN 形态（去连字符后 13 位且 978/979 开头，或 10 位且末位可为 X）走 `v_index=isbn`，其余一律走 `v_index=all`（任意词）。isbn 索引要求完整参数集（`library=all`、`v_tablearray=bibliosm,serbibm,apabibibm,mmbibm,`、`sortfield=ptitle`、`sorttype=desc`、`cirtype`、`v_secondquery`、`v_startpubyear`、`v_endpubyear` 缺一不可），缺参会被静默忽略并回退成全库检索（实测返回约 360 万条）；带连字符与紧凑形态均可命中。任意词索引的字段集不含 ISBN，ISBN 形态关键词必须路由到 isbn 索引。实测结论钉在 `tests/fixtures/shenzhen/NOTES.md`。
- 分页：与参数名直觉相反——`page → v_page`（页码）、`limit → pageNum`（每页条数）。实测结论钉在 `tests/fixtures/shenzhen/NOTES.md`。
- 三桶：`CanLoanBook`/`OnlyReadBook` 是 `list[group]`，`BorrowedBook` 是单个 group dict 或 `null`，容器形态不一须归一化；`OnlyReadBook`（仅阅览）判不可借。
- 馆名：可借/阅览组在 group 级 `serviceaddrnotes`，借出单册在单册 `libraryNotes`；单册的 `library` 是馆代码不是馆名。
- 应还日期：`BorrowedBook` 单册的 `ReturnDate`（`YYYYMMDD` → 归一 `YYYY-MM-DD`）。
- 公共参数 `client_id=t1` 由 client 层统一注入，业务函数不传。
- 注意：该 API 非官方公开接口，字段可能漂移；字段侦察结论见 `tests/fixtures/shenzhen/NOTES.md`，漂移时以实抓为准更新解析与 fixture。

## 天津（三源合并，首个「一城多源」范本）

`adapters/tianjin.py` 一个城市聚合三个独立系统（入口与技术组件见总览表）：

| 源 | 前缀 |
|---|---|
| 天津图书馆（主馆，含全市通借网络） | `TJL01` |
| 天津市少年儿童图书馆 | `TJC01` |
| 中新友好图书馆（生态城） | `ZXYH` |

- **两 ALEPH 不可并查**：opacwh/opacse 是两台独立服务器、各自独立 `local_base`，
  同一「三体」检索 TJL01 156 条 vs TJC01 32 条，数据互不相通——必须分别检索再归并。
- **book_id 形态**：单成员 `源前缀:记录号`（如 `TJL01:002892667`、`ZXYH:217795`）；
  跨源同 ISBN 命中合成**复合 id**，成员按优先级 TJL01 > TJC01 > ZXYH 以 `+` 连接
  （如 `TJL01:000856840+TJC01:000178012+ZXYH:217795`），书目字段取最高优先级成员原值。
  holdings/detail 按成员拆分路由后聚合（可借在前、馆名升序）。
- **ISBN 归并口径**：去连字符与空白、校验形态后归并；脏值与无 ISBN 不参与、各自成条；
  源内同 ISBN 多条（多卷/重印）保留首条。合计口径：`total_results`＝存活源之和，
  任一存活源无总数则如实 None。
- **ALEPH quirks**（详见 `tests/fixtures/tianjin/NOTES.md`）：检索码以页内下拉为准——
  ISBN 是 **ISB**（`ISBN` 会报「检索请求解析错误」）、全字段 WRD、系统号 SYS；
  ISB/SYS 单命中**直接返回完整记录页**（非 brief 列表）；`short-jump` 的 jump 是
  **记录偏移不是页码**（页 P → jump=(P-1)×10+1），且必须用页内会话 URL（`F/VV...` 前缀，
  set_number 绑定 cookie 会话）；brief 页 publish section 注释块多于真实条目（13 vs 10），
  以 `class=itemtitle` 锚定并按 DOC-NUMBER 去重；**编码 UTF-8**（GBK 初判被实测否定）；
  无会话 `full-set-set` 直连不可用，详情走 SYS 检索。
- **单册页 item-global 列语义**：「单册状态」列是流通类型（阅览/中文图书借阅…），
  「应还日期」列才是可借性原值（在架上 / 借出日期 / 分配中·编目中·物流中等）；
  可借判定只看应还日期列，词表外保守不可借。
- **限频与验证码墙**：约 8 个快速请求触发 **HTTP 401 按 IP 封**（上次实测约 1 小时，
  需浏览器打开 OPAC 输入验证码手动解封）；实抓以 8 秒间隔稳定，适配器按 4 秒/host 节流。
  401 与 200 验证码页统一抛 `_CaptchaError`（带手动解封指引），**穿透源级容错**直达
  调用方——封禁是全局信号，静默降级成部分结果会误导。其余源级失败：≥1 源存活即返回，
  三源全失败汇总报错。
- **ZXYH 走 interlib 家族**：检索与详情必须带 `curlibcode=STC001`（家族 quirk 字段，
  缺详情参数直接 HTTP 500），馆藏 JSON 不需要；ISBN 在 `expressServiceTab` 兄弟节点上，
  家族 parser 以 `express_bookrecno` 后挂；`search_raw` 暴露内部 isbn 字段供归并
  （契约 `BookSummary` 不含 isbn）。

## 杭州（双源合并：杭图 Interlib ＋ 浙图自研 JSON，2026-10-02）

`adapters/hangzhou.py` 照天津模式聚合两个独立系统：杭州图书馆（前缀 `HZ:`，
interlib 家族三原语，检索走 `search_raw` 取 isbn 内部字段供归并）＋浙江图书馆
（前缀 `ZJ:`，`adapters/_zjlib.py` 轻量 JSON 客户端，节流 2 秒/host）。

- **book_id 形态**：单成员 `HZ:{bookrecno}` / `ZJ:{originalId}`；跨源同 ISBN 命中
  合成复合 id（成员按优先级 HZ > ZJ 以 `+` 连接，书目字段取 HZ 成员原值，真网实证
  `HZ:2007154111+ZJ:110000014851476`）。**向后兼容**：0.3.0 已上线的裸数字
  book_id（无前缀）一律按 HZ 成员路由（兼容垫片，钉在 `tests/test_hangzhou_merge.py`；
  搜索输出形态升级为带前缀）。
- **归并口径（同天津）**：ISBN 去连字符与空白、校验形态后归并；浙图
  `identifierIsbn` 原值带脏后缀（如「9784152098702 :」），归并键按形态从脏串提取
  （带数字边界断言防误切），展示字段保持原值；脏值与无 ISBN 不参与、各自成条；
  源内同 ISBN 多条保留首条；`total_results`＝存活源之和（任一存活源无总数则 None）；
  holdings 聚合可借在前、馆名升序；detail 取优先级最高成员；源级容错（≥1 源存活
  即返回，双源全失败汇总报错）。
- **浙图接口要点**（详见 `tests/fixtures/zjlib/NOTES.md`）：全部 POST JSON，必带
  `BFF-ORG-ID` 头，无需鉴权；检索 `search-admin-service/open-api/search/pageList`
  （真实 total、`current` 分页实测生效、ISBN 关键词任意词直接命中无需专门路由；
  record 无可借性字段 → ZJ 成员 `availability_summary` 恒空）；详情
  `portal-pc-api/search/getWorkById`（书目字段嵌套在 `data.record`、多为单元素数组，
  与调研笔记有 4 处出入以 NOTES 为准；「记录不存在」与「服务器忙」统一
  `code:500` 不可区分，desc 原值照登）；馆藏 `resourceList` 是**两跳链**
  （`getWorkById(originalId) → workId → resourceList(workId)`，误传 originalId
  静默返回空、不报错）。
- **浙图数据边界**：访客视角无应还日期（需读者登录），`due_date` 恒空串；
  library＝馆区名（districtId 查字典，查不到回退码原值，null → 空串）；
  location＝`local_name` 原值；status＝`state_name` 原值（缺失回退 state 码），
  词表（2=在馆/3=借出/9=锁定/16=馆内阅览/33=已通还…）外保守不可借。
- 杭图源行为与合并前完全一致（`test_hangzhou_compat.py` 零改动仍绿）。

## 重庆（InDigLib）

`adapters/chongqing.py` 独立实现（urllib + CookieJar 会话），API 基址
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

## 合肥（Interlib 双源合并，2026-10-02 接入）

`adapters/hefei.py` 聚合两个 Interlib 源（入口见总览表），合并口径全套照天津范本：

- 前缀：安徽省图书馆 `AH:`、合肥市图书馆 `HF:`；跨源同 ISBN 合成复合 id（`AH:x+HF:y`），
  优先级 AH > HF，书目字段取 AH 原值；ISBN 归并/脏值各自成条/源内去重/total 求和与
  None/源级容错（≥1 源存活即返回）均照天津口径，钉在 `tests/test_hefei_merge.py`。
- 两源与穗杭完全同模板，唯一结构差异：**HF 应用上下文是 `/lib2` 非 `/opac`**
  （`/opac/*` 返回 nginx 500）——hefei.py 内按 `_Source.ctx` 拼路径自建单源三原语
  （复用家族 client/parser）；`InterlibConfig.ctx` 家族化提案未合入（见家族小节）。
- tagTr 陈旧标签缺陷（家族级，2026-10-02 已修复）由合肥 AH 布局第三路独立实证，
  回归钉子 `test_ah_detail_author_not_clobbered_by_tag_row`。
- 两源侦察结论见 `tests/fixtures/hefei/NOTES.md`。

## 台州（Interlib pro2018 模板变体，2026-10-02 接入）

`adapters/taizhou.py`：台州市图书馆（浙江地级市馆，馆藏含 S1 线地铁站等全市通借网点，
确系浙江台州非江苏泰州）。HTTP 层、检索参数集、馆藏 JSON 与广州基准同构（家族
`interlib.client`/`get_holdings` 原样复用），但搜索/详情是 pro2018 新版皮肤，两页解析
在适配器内本地实现（结构对齐家族 parser，含 isbn 内部字段）：

- 搜索页：条目 `li.libBookLi`（非 bookmeta），总数在 `schResNumIn` 元素，分页是 JS
  配置 `totalPage:`/`currentPage:`——广州基准的「共 N 页」+「下一页」锚点探测法在台州
  **恒 has_next=False（错误结果）**，pro2018 城市必须走 JS 变量。
- 详情页：`a.bkTxtTit` 标题 + `bkTxtLeft/bkTxtRight` 两列 li（非 bookInfoTable/h2）。
- `rows` 参数服务端真实生效（total_pages 随 limit 变）；借出单册带应还日期，
  逾期形态原值照登；curlibcode 不需要（检索/详情裸参数可通）。
- 与绍兴同属 pro2018 模板代——台州证明该模板可适配器本地解析交付，不动家族模块
  （家族化提案与 patch 存档于交付报告，见家族小节）。
- 字段侦察结论见 `tests/fixtures/taizhou/NOTES.md`。

## 金华（UILAS HTML OPAC，2026-10-02 接入）

`adapters/jinhua.py` 独立实现（urllib，全链路匿名零 cookie），入口
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

## 南京（金陵 uopac 联合目录，2026-10-02 接入）

`adapters/nanjing.py` 独立实现（urllib **无状态**、无 Cookie——裸请求与带会话响应
逐字节相同，实证），API 基址 http://uopac.jllib.cn （汇文「南京市公共图书馆书目全文
检索」，金陵图书馆运营，成员馆＝金陵＋12 区馆），节流 4 秒/host，timeout 90 秒
（源站 chunked 传输可停顿 ≥60 秒，重试即好）。

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
- book_id＝uopac 原生数字 id（无前缀）；南图 ALEPH（全局验证码墙，搁置）将来若解锁
  照天津模式加源合并。
- 侦察结论见 `tests/fixtures/nanjing/NOTES.md`（「钉死事实一/二」节）。**汇文 uopac
  防护逐站不同**：南京站无扬州站那套 JS AES 加密 Cookie（securitycam）反爬墙——同系统、
  不同站点、防护不同，将来评估其他汇文站点必须逐站实测，不能按系统家族推定。

## 成都（Interlib pro2018 模板代，2026-10-02 接入）

`adapters/chengdu.py`：成都市公共图书馆联合书目检索（主馆成都图书馆 CD101，联合目录跨
成都平原经济区：成都辖区＋德阳/什邡/资阳/眉山等市县馆，libcodeMap 483 馆码）。原登记
入口超星 ucdrs 因 IP 白名单硬墙搁置，本入口为馆方独立运营的图创 OPAC，与超星无关。

- 定性：调研原话「汇文 Libsys Pro2018」有误，实抓指纹（meta keywords 自报「opac, 图创,
  interlib」、页脚 © www.interlib.com.cn、静态资源 `/opac/media/pro2018/simple/`）确认为
  图创 Interlib pro2018 模板代；证据链见 `tests/fixtures/chengdu/NOTES.md`。
- HTTP 层、检索参数集、馆藏 JSON 与广州基准同构（家族原样复用）；搜索（libBookLi）/详情
  （bkTxt）两页解析在适配器本地实现——台州解析器对成都 fixture 零修改全兼容，pro2018
  同形态第二城，家族化提案条件已满足（见家族小节，执行排在批次收口后）。
- 状态码语义与调研初判**相反**：holdStateMap 原值 `2→在馆`（可借）、`3→借出`（不可借），
  家族词表判定无需新表；应还日期 loanWorkMap.returnDate 直取，远期/远逾期原值照登。
- detail 的 `?return_fmt=json` 完整 MARC 为可选增强，未采用（HTML 详情已覆盖契约全字段）。
- p1 首条 ebkType 显示「期刊」（其余 9 条「图书」），语义存疑，原值照登未采信
  （NOTES 有记录）。
- 字段侦察结论见 `tests/fixtures/chengdu/NOTES.md`。

## 宁波（图创 tcc-opac，2026-10-02 接入）

`adapters/ningbo.py` 独立实现——tcc-opac 与 Interlib 是不同产品线，不可复用家族。
纯 JSON ＋ JWT 访客令牌（`POST /system/user/getOpenApiAccessToken` 匿名即发，
`ACCESS-TOKEN` 请求头，过期自动重取一次）：

- **检索**：`POST /search/`（尾斜杠；`bookSearch` 是开放平台端点、参数形态不同且
  长期「系统异常」，勿混用）body `{current,size,searchWay,sortWay,sortOrder,hasholding,q}`；
  `searchWay` 词表与 Interlib 同款（marc=任意词/title/isbn/author）；响应无 `code` 字段
  即成功，`numFound` 为字符串。
- **滑块风控**：`code ∈ {43001,-1,-402}` 触发前端滑块验证 → 程序化停手抛错，不硬闯。
- **详情**：`POST /service/biblios/getbyid?id=&fields=…`（参数走查询串、空 body）；
  UNIMARC 字段字典（200$a/200$f/010$a/100$a/690$a…）；`code==-1`「数据不存在」＝
  聚合条目无本地书目（数据边界）。
- **馆藏**：`POST /service/hold/pagelist {current,size:500,bibliosId}`，单册级；
  `statename` 原生状态词、`returnTime` 时间戳取日期段；一页 500 册封顶（前端同款）。
- **数据边界**：联合目录含区县馆与城市书房（馆名带源站原值前缀）；聚合条目详情/馆藏
  可能为空；检索条目 publisher/pubdate 常空（索引未富化，完整字段看详情）；老书目出版项
  可能缺失（出版年兜底取 100$a）；`classno` 是分类号不作索书号，单册完整索书号在馆藏 `callno`。

## 绍兴（Interlib pro2018，2026-10-02 接入）

`adapters/shaoxing.py`：绍兴市公共图书馆联合目录（联合绍兴/上虞/诸暨等）。HTTP 层、
检索参数集、馆藏 JSON 与广州基准同构（家族复用）；搜索/详情为 pro2018 模板，两页解析
在适配器内本地实现（台州同款路径，未动家族共享模块）：

- 搜索：结果容器 `<ul class="libBookUl"><li class="libBookLi">`（非 `bookmeta`）；
  稳定 ID 取题名锚点 `bookDetail(<recno>,…)` 调用；`has_next` 仍可靠「下一页」锚点。
- 详情：题名 `a.bkTxtTit`；字段为「标签：值」行（`ISBN：/出版发行：/中图分类法：`等）。
- 馆藏：单书 `GET /opac/api/holding/{recno}`；联合层书目（无本地单册）单书 GET 与
  批量 `POST /opac/api/holding/getHoldingsBybookrecnos` 均为空——属数据边界，
  检索页「在馆」计数即走该批量 POST。

## 大连（SirsiDynix iLink，2026-10-02 接入）

`adapters/dalian.py` 独立实现（新家族，全 HTML、无 JSON）。**会话制**：ps token 每响应都变，
全程同一 CookieJar 串行（类重庆流程）；节流 ≥4 秒/host：

- 检索：`POST /uhtbin/cgisirsi/?ps={token}/DALIANLIB/X/123`，字段 `searchdata1`=关键词、
  `srchfield1`=检索字段（实抓下拉无 ISBN 选项）。
- 翻页：结果页 hitlist 表单 POST（`/X/9` 形态）；详情/馆藏需带当次 ps token、同会话内访问，
  馆藏 HTML 内联。
- 会话失效（跳回入口/形态变化）重建一次再试，仍失败抛错。
