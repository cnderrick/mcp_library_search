# 郑州图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://123.15.53.180:62280/client/zh_CN/default/`（页标题「Home Room」，
`generator` meta 自报 **Apache Tapestry Framework 5.3.3**，`com_sirsi_ent_widgets`
变量 → **SirsiDynix Enterprise / Portfolio 4.3（30190）**，本仓库首见新家族）。
抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

> 入口修正：登记的 `http://123.15.53.180:62280/opac/index` 是 **404**；正确的应用
> 上下文是 `/client/zh_CN/default/`（`zh_CN` 为语言，`default` 为皮肤）。

## 技术组件

SirsiDynix Enterprise（Portfolio/VSE），**服务端渲染 HTML**（Tapestry），与既有
Interlib／UILAS／LibStar 等 JSON 系均不同，独立成 `sirsi_ent/` 家族。会话制：
`JSESSIONID` cookie 串起检索→详情→可用性；本站点首次 GET 首页即发 cookie。

## 检索：`GET {ctx}/search/results`

`GET /client/zh_CN/default/search/results?qu=三体&te=ILS` 直连可用，返回结果页。
实抓「三体」共 **23312 条**、12 条/页。

- 条目字段：隐藏域 `id="daN"` 的 `value` 是实体 URI `ent://SD_ILS/2207/SD_ILS:2207712`
  （即 `book_id`）；题名在 `id="detailLinkN"` 锚（「题名 /著者」形态）；
  著者在 `INITIAL_AUTHOR_SRCH`；ISBN 在 `class="isbnValue"` 隐藏域。
- **检索页不渲染出版社/出版年** → 列表条目二字段空串（详情页有）。
- **分页 quirk**：站点每页固定 **12** 条，`limit` 不生效；翻页参数是
  `rw=(page-1)*12`（`rw` 为「已跳过的记录数」）。总数锚点
  `resultsToolbar_num_results`>「N 找到结果」；0 结果时该锚点整体缺失、改由
  `no_results_wrapper`／「本次检索未返回任何结果。」判 0。

## 详情：`GET {ctx}/search/detailnonmodal`

`GET /client/zh_CN/default/search/detailnonmodal?d=<实体编码>~ILS~0~<n>&te=ILS&ps=300`
返回详情页。**`d` 参数 quirk**：`d` 须是 `urllib.quote(entity) + "%7EILS%7E0%7E<n>"`
（Tapestry 只认带 `~ILS~0~<n>` 后缀的形态；`n` 任意，实测 0/2/23311 均可）。
书目字段在 `displayElementLabel X_label` / `displayElementText X` 对：
`INITIAL_TITLE_SRCH`（「题名 /著者」）、`INITIAL_AUTHOR_SRCH`、`ISBN`、
`PUBLICATION_INFO`（「城市, 出版社 年 …」）、`GENERAL_NOTE`（提要）。索书号取
内联单册表「排架号」首值。

## 馆藏：内联单册表 ＋ `loadavailability` JSON

详情页**内联渲染单册表**（`tr.detailItemsTableRow`：资料类型／图书条形码／排架号／
状态），状态列由异步 `loadavailability` 从 `正在检索...` 填充。

- **必需 `X-Requested-With: XMLHttpRequest`**：缺该头时 `loadavailability` 回
  Tapestry「未预料错误」页（错误摘要里反而打印 JSON）；带头即回干净 JSON。
- JSON：`{ids:[条形码...], strings:[状态/地点...], totalAvailable, copies, holdCounts}`；
  `strings[i]` 是单册 `ids[i]` 的状态列原值——**可借时为馆藏地点名**（如
  `永城馆流通书库`、`荥阳馆审计局分馆`），**不可借时为状态词**（`到期 24-3-8`、
  `在馆际调拨中`）。故：命中不可借词判不可借（`到期` 顺带提应还日期），否则视为
  可借、该串作 `library`（源站未拆「分馆／地点」两栏，故 `location` 空串）。
- 实抓「三体」实体 2207712：内联 5 册、`totalAvailable=5`，地点均「永城馆流通书库」。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页（`/client/zh_CN/default/`） |
| `search_santi.html` | 检索「三体」，23312 条、首页 12 条 |
| `search_empty.html` | 生造关键词，0 条（`no_results_wrapper`） |
| `detail_santi.html` | `detailnonmodal`（实体 2207712，题名/著者/ISBN/出版/提要） |
| `holding.json` | 该实体 `loadavailability` JSON（5 册） |

## 数据边界

- 检索列表 publisher/publish_year 空串（源站检索页不渲染），详情页有值。
- 馆藏 `strings` 把「分馆+地点」合成一栏，故 `library` 为原值、`location` 空串。
- `status` 原值照登；词表外保守判不可借（地名为可借标志）。
- `limit` 不生效（固定 12/页）。
