# 数据源清单

各城市图书馆的线上入口、系统技术组件与接入要点。**新增城市先在总览表登记一行**，实现细节追加到对应小节。

## 总览

同一省份的城市排在一起，省份列只在该省首行填写（视觉上等同于合并单元格），新增城市时接在本省行之后。

| 省份 | 城市 | 标识 | 线上图书馆入口 | 技术组件 | 适配层位置 |
|---|---|---|---|---|---|
| 上海市（直辖市） | 上海 | `shanghai` | https://vufind.library.sh.cn | VuFind（上海中心图书馆"一卡通"总分馆体系，900+ 网点） | `vendor/shanghai_library/` + `adapters/shanghai.py` |
| 北京市（直辖市） | 北京 | — | 待调研 | Ex Libris Primo（初判） | 🔜 搁置：站点 WAF 拦截程序化访问 |
| 天津市（直辖市） | 天津 | `tianjin` | http://opacwh.tjl.tj.cn:8991/F 等三个源（见下） | Ex Libris ALEPH ×2 + 图创 Interlib | `adapters/tianjin.py`（三源合并） |
| 重庆市（直辖市） | 重庆 | `chongqing` | http://222.177.237.197:8080/InDigLib/ | InDigLib 集群数字图书馆（Struts2+Solr） | `adapters/chongqing.py`（独立实现） |
| 广东省 | 广州 | `guangzhou` | https://opac.gzlib.org.cn | 图创 Interlib | `interlib/` 家族 + `adapters/guangzhou.py` |
|  | 深圳 | `shenzhen` | https://www.szlib.org.cn/opac/ | 图书馆之城自研 JSON API（后端 ILAS，167 馆统一平台） | `adapters/shenzhen.py`（独立实现） |
| 浙江省 | 杭州 | `hangzhou` | https://my1.zjhzlib.cn | 图创 Interlib（与广州同模板） | `interlib/` 家族 + `adapters/hangzhou.py` |

## 上海（VuFind）

vendor 组件 shanghai-library-book-search-python（Apache-2.0），细节与本地补丁记录见根 [NOTICE](../NOTICE)。

- 检索总条数：站点统计区不再输出（`total_results` 恒为 0），adapter 按"0 且当前页有结果 → 视为未知（null）"处理，不属于代码 bug。
- 简介：站点没有独立简介区块，内容简介以书目"附注"字段（MARC 500）形式给出，vendor 补丁将 summary 回退到附注（见 NOTICE 变更）。
- 应还日期：馆藏页不直接渲染归还日期，已借出馆藏的 `<a class="item-return-date">` 只带单册 `data-itemid`，需按条调用 `AJAX/JSON?method=itemReturnDate`（vendor 提供 `get_return_date`，adapter 负责逐个补 `due_date`）。
- 同步上游：上游是平铺 import，已改为包内相对导入；覆盖同名文件同步后必须重新应用该修改。本地补丁（parser 的 has_next、library_client 的 statistics）同步后检查是否需重打，并在 NOTICE 变更里记一笔。

## Interlib 家族（广州、杭州）

`src/mcp_library_search/interlib/` 是一方共享代码：`client.py`（HTTP）、`parser.py`（搜索页/详情页 HTML + 馆藏 JSON）、`__init__.py`（三原语，对外签名冻结）。结构事实以广州 fixture 为基准（`tests/fixtures/guangzhou/NOTES.md`），杭州的结构兼容性钉在 `tests/test_hangzhou_compat.py`。

- 搜索页：每条结果是 `bookmeta` 容器（`bookrecno` 即 `book_id`），字段按 class 锚点提取（title-link/author-link/publisher-link）；总数"检索到: N 条结果"（带千分位逗号）；分页"共 N 页" + 「下一页」锚点存在与否。
- 详情页：书目在 `bookInfoTable` 两列表格（leftTD 标签 / rightTD 值）；**没有独立索书号字段**，`call_number` 取"中图分类法"值；简介取"内容提要"；标题在首个 `<h2>`。
- 馆藏：不在详情页 HTML 内联，走 Ajax JSON 接口 `/opac/api/holding/{bookrecno}`；馆码/位置码/状态码分别经 `libcodeMap`/`localMap`/`holdStateMap` 翻译，查不到回退码本身。
- 应还日期：借出单册在 `loanWorkMap[barcode].returnDate`（epoch 毫秒，按 UTC+8 解释，与馆方系统时区一致），退回单册 `loan` 字段保守提取。
- 可借分类：`is_available_status` 状态词表——命中不可借词优先，命中可借词次之，都不中**保守判不可借**（未识别状态不让读者白跑）。
- 杭州差异（quirk）：与广州同模板（详情页 JS 甚至带广州分支函数）；「馆藏浏览」锚点缺失（用「馆藏地点」）；空结果页含 `bookDetail(` 的 JS 函数定义，解析必须按 `bookDetail(数字` 匹配，不能裸数出现次数。
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

`adapters/tianjin.py` 一个城市聚合三个独立系统：

| 源 | 前缀 | 系统 | 入口 |
|---|---|---|---|
| 天津图书馆（主馆，含全市通借网络） | `TJL01` | Ex Libris ALEPH 20.1 www_f_chi | http://opacwh.tjl.tj.cn:8991/F |
| 天津市少年儿童图书馆 | `TJC01` | 同款 ALEPH（独立 host 独立 base） | http://opacse.tjl.tj.cn:8991/F |
| 中新友好图书馆（生态城） | `ZXYH` | 图创 Interlib（租户 STC001） | http://sm.interlib.cn:8104 |

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

## 重庆（InDigLib）

`adapters/chongqing.py` 独立实现（urllib + CookieJar 会话），入口
http://222.177.237.197:8080 （InDigLib 集群数字图书馆，Struts2 + Solr）。

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
- **馆藏只到馆级**：详情页「馆藏信息」注释块内 `class="first"` 馆名可匿名取；
  **单册级 JSON `GetAsset.action` 有读者登录门槛**（带全链路头重放三次均 302 登录页），
  故 `available=False`、`status=""` 保守返回，不预设可借——这是公共数据的边界，
  不是解析缺陷。
- 字段侦察与端点真伪结论见 `tests/fixtures/chongqing/NOTES.md`。
