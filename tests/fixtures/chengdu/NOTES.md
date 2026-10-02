# 成都 OPAC 页面结构侦察（2026-10-02 实抓）

站点：`https://opac.cdclib.cn`（入口 `/opac/index`，页面自证「成都市公共图书馆联合书目检索」）。
主馆全称：**成都图书馆**（holding JSON `libcodeMap` 里 `CD101 → 成都图书馆`，照实登记；
联合目录属性写 data-sources 备注，`name_cn` 建议记「成都图书馆」，同绍兴主馆口径）。
抓取全部只读 GET，HTTP 200，无验证码、无限频迹象（共 7 个请求，间隔 ≥2.5 秒）。

## 定性结论：图创 Interlib，pro2018 模板代（simple 皮肤）——调研「汇文 Libsys」标注有误

复活调研笔记（docs/team/research/2026-10-02-superlib-revival.md）原话称「汇文 Libsys Pro2018」，
**实抓指纹全部指向图创 Interlib，无一指向汇文**：

1. 搜索页 `<meta name="keywords" content="opac, 图创, interlib, 图书检索, 借书, , 成都市公共图书馆联合书目检索">`
   ——站点自报「图创 interlib」，与绍兴同款自证。
2. 首页页脚 `© 2005 - 2014 www.interlib.com.cn, all rights reserved`（图创官网版权行，绍兴同款）。
3. 静态资源走 `/opac/media/pro2018/simple/…`（pro2018 模板代；`simple` 是简版皮肤，
   首页 `<title>简版首页</title>`），与绍兴/台州的 pro2018 同源。
4. 端点形态全套家族同款：`/opac/search?q=`（HTML）、`/opac/book/{bookrecno}`（bkTxt 详情）、
   `/opac/api/holding/{bookrecno}`（JSON，顶层键与广州基准完全一致：holdingList/libcodeMap/
   localMap/holdStateMap/pBCtypeMap/barcodeLocationUrlMap/libcodeDeferDateMap/loanWorkMap/shelfnoUrlMap）。
5. **实证**：台州适配器 `_parse_search`/`_parse_detail`（pro2018 本地解析已实证范式）对成都
   fixture **零修改全兼容**（搜索 10 条/总数 1826/分页 183、空页判 0、详情全字段命中）；
   家族 `parser.parse_holdings` + `is_available_status` 对成都 holding JSON 98 条全部解析成功。

调研混淆点推测：「Pro2018」是图创 pro2018 模板代名，被调研误归到汇文产品线；
汇文系统的端点/DOM 形态与本页无一吻合。按实抓为准：**图创 Interlib pro2018**。

## Fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `index.html` + `headers_index.txt` | `GET /opac/index` | 首页（简版皮肤），厂商指纹证据（meta/页脚/pro2018 资源路径） |
| `search_p1.html` | `GET /opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1` | 搜索第 1 页，10 条结果，总数 1826，`totalPage: 183` |
| `search_p2.html` | 同上 `page=2` | 第 2 页，10 条，条目与第 1 页零重叠（`page` 参数真实翻页） |
| `search_empty.html` | 同上 `q=azbycxq不存在xyz` | 生造关键词，0 条，`notFindFt` 提示锚点在 |
| `detail.html` | `GET /opac/book/1002796122` | 《三体》（刘慈欣著，重庆出版社 2008）默认详情页，bkTxt 模板 |
| `holding.json` | `GET /opac/api/holding/1002796122?limitLibcodes=&isCluster=` | 馆藏 JSON，98 条单册（在馆 84/借出 14），与家族基准同构 |
| `detail.json` | `GET /opac/book/1002796122?return_fmt=json` | 详情 JSON（含完整 MARC `marcContent`，ISO 2709）；**可选增强，适配器未采用**（见下） |

## 搜索页结构（libBookLi 模板，与台州同款 pro2018 皮肤）

家族标准检索参数原样可用（`q/searchType/searchWay0/logical0/rows/sortWay/sortOrder/page`；
调研带过的 `isFacet=true&view=standard` 非必需，实抓未带也返回完整结果页）。

每条结果是 `<li class="libBookLi notBorder">` 容器，锚点与台州一致：

- 书目 ID 与标题：`<a href="javascript:bookDetail({bookrecno},1,1);" class="libBookDetNm">三体</a>`；
  同容器序号 `<span class="libBookDetNm mbLibBookNum">1</span>`（同 class 是 span，须按 a 标签取）。
  封面 `<img isbn="978-7-5366-9293-0" bookrecno="1004752340">` 属性可作 ID/ISBN 兜底。
- 字段标签 `<span class="libBkDetTit">`（责任者/出版信息/ISBN），标签后随 `<a class="color33 layerTip">`：
  责任者→作者 a 文本（含 MARC 责任方式「刘慈欣著」）；出版信息→出版社 a 文本，
  出版年是该 a 之后、下一个 `<p>` 前的裸文本 `,2008`；ISBN 标签后是裸文本，解析取封面 img 属性。
  注意：成都 HTML 里「责任者」标签文本带大量换行空白（台州是紧凑文本），`_clean` 折叠后一致，不影响解析。
- 总数：`<span class="schResNum">检索结果共有<i class="color50 schResNumIn">1826</i>条</span>`（台州同款锚点）。
- 分页：JS 配置 `currentPage: 1`/`totalPage: 183`，无可点分页锚点，`has_next = currentPage < totalPage`。
- 空结果页：有 `notFindFt` 提示锚点（源站明说没有相关书目 → 判 0），JS 分页配置仍在（`totalPage: 1`）。
- 文献类型 `<span class="ebkType">`：本页 10 条中 9 条「图书」、**第 1 条（1004752340）显示「期刊」**——
  原值照登不判断（BookSummary 无类型字段，不影响解析；该条 img isbn/出版信息与 2008 重庆出版社
  《三体》图书一致，ebkType 语义存疑，不采信不猜测）。
- 馆藏信息 tab 是 iframe 异步（`holdingPreview_{id}`），`availability_summary` 同家族恒空串。

## 详情页结构（bkTxt 模板，与台州同款：左右两列 li 标签）

默认 `GET /opac/book/{bookrecno}` 无 `bookInfoTable`/`leftTD`（家族基准锚点计数 0），
实际结构为 `bkTxtLeft`/`bkTxtRight` 两列 `<li>标签：<span>值</span></li>`，标题 `<a class="bkTxtTit">三体</a>`。
台州 `_DetailParser` 实跑全字段命中：title 三体、author 刘慈欣（主要责任者 a 文本）、
publisher 重庆出版社、publish_year 2008、isbn 978-7-5366-9293-0、call_number I247.55（中图分类法，「版次」前）。
本样例**无「内容提要」标签行**（计数 0），`summary` 空串；若个别记录带该 li 按同标签照抓（台州口径）。

`detail.json`（`?return_fmt=json`）含完整 MARC（`book.biblios.marcContent`，ISO 2709，本记录 705 字符）
及 `libcodeMap/localMap/holdstateMap` 等冗余字典——**可选增强，未采用**：HTML 详情页已覆盖
BookDetail 契约全字段，MARC 解析（ISO 2709 目录+字段拆分）成本高收益零，不进本适配器。

## 馆藏 JSON（与家族基准同构，家族解析器原样可用；state 语义调研初判**相反**）

顶层键与广州/台州完全一致。单册字段同款（`barcode/callno/curlib/curlocal/state/loan/shelfno/…`）。

- **状态码以 `holdStateMap` 原值为准**（调研初判「2=非外借、3=在架可借」与实抓**相反**）：
  `2→在馆`（84 条）、`3→借出`（14 条）。家族词表判定：「在馆」命中可借词→available，
  「借出」命中不可借词→不可借，**无需新词表**。
- 本站 `holdStateMap` 共 26 项（比台州多出 `9锁定/12清点/14修补/15查找中/16重复锁定/17提存/31运回中/34报废/40馆际丢失`）：
  除「在馆」外全部被家族词表判不可借（命中不可借词，或词表外保守不可借），方向均正确，无需扩表。
- 应还日期：`loanWorkMap[barcode].returnDate`（epoch 毫秒，UTC+8），家族 `_holding_due_date` 直取。
  本书借出 14 条中 8 条带应还日期（loanWorkMap 仅 9 条），其余空串照登；日期含 `2035-02-10`（远期）与
  `2019-02-26`（远逾期）等原值，照登不判断（台州同款口径）。
- **联合目录跨市域**：`libcodeMap` 483 馆码；本书 98 条单册分布在 17 个馆码——除成都辖区
  （郫都区/新都区等）外，含德阳市图书馆、什邡市图书馆、资阳市图书馆、眉山市辖县馆（丹棱/青神/仁寿）、
  中江县图书馆等（成都平原经济区联合目录形态）。馆名一律经 `libcodeMap` 翻译原值照登，不按市域过滤。
- 位置码经 `localMap`（4417 条）翻译，如 `CD124_D001→总书库` 形态，原值照登。

## 实测请求台账（fixture 侦察共 7 次 GET，全部 200）

首页 ×1、搜索页 ×3（p1、p2、空结果）、详情页 ×1、馆藏 JSON ×1、详情 JSON ×1。
无 401、无验证码、无 TLS 重置、无限频迹象。响应头见 `Set-Cookie: JSESSIONID/IFCCAS_3RD_TOKEN`
——匿名会话即可用，适配器无状态、不带 Cookie。调研记录 `Server: panyun`（本次抓包响应头未回显
Server 行，CDN 形态不影响接入）。

## 复抓命令（只读 GET）

```
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
curl -sS -A "$UA" "https://opac.cdclib.cn/opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1" -o search_p1.html
curl -sS -A "$UA" "https://opac.cdclib.cn/opac/book/1002796122" -o detail.html
curl -sS -A "$UA" "https://opac.cdclib.cn/opac/api/holding/1002796122?limitLibcodes=&isCluster=" -o holding.json
```
