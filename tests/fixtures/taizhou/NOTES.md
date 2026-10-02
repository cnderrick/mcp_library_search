# 台州市图书馆 OPAC 页面结构侦察（2026-10-02 实抓）

站点：`https://opac.tzlib.cn:8182`（图创 Interlib，pro2018 新版模板变体）。
馆名全称：**台州市图书馆**（地级市馆，非区级馆；首页 meta keywords 与页脚版权自证，
页内 JS 馆码 `P2ZJ0576070`）。馆藏为全市通借网络：holding JSON 的 `libcodeMap`
含天台县图书馆、路桥区图书馆、城东分馆、大溪分馆、台州技师学院、台州市委党校等。
抓取全部只读 GET，TLS 正常无重置，无验证码、无限频迹象（共 8 个请求，间隔 ≥2 秒）。

与广州基准的关键差异一句话：**馆藏 JSON 与广州完全同构（家族解析器原样可用），
但搜索页与详情页是家族内另一套页面模板**——`bookmeta` 容器与 `bookInfoTable`
两列锚点在默认页面上均不存在，现有 `InterlibConfig` quirk 字段（仅 `curlibcode`）
表达不了「整套页面模板不同」，解析暂放 `adapters/taizhou.py`（家族化 patch 见交付报告）。

## Fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `search_p1.html` | `GET /opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1` | 搜索第 1 页，10 条结果，总数 163 |
| `search_p2.html` | 同上 `page=2` | 搜索第 2 页，10 条结果（`page` 参数真实翻页，条目与第 1 页不同） |
| `search_empty.html` | 同上 `q=azbycxq不存在xyz` | 生造关键词，0 条结果 |
| `detail.html` | `GET /opac/book/1185362?view=simple&flag=printer` | 《三体：新版》详情打印视图（`bookInfoTable` 家族模板，仅作对照证据，适配器不用它，见下） |
| `detail_default.html` | `GET /opac/book/1185362` | 同书默认详情页（bkTxt 模板，适配器解析对象） |
| `holding.json` | `GET /opac/api/holding/1185362?limitLibcodes=&isCluster=` | 馆藏 JSON，与广州同构 |

页面内链 URL 带服务端嵌入的 `jsessionid`（匿名会话），解析按结构锚点不按 URL，无影响。

## 搜索页结构（libBookLi 模板，与广州 bookmeta 基准不同模板)

家族标准检索参数原样可用（`q/searchType/searchWay0/logical0/rows/sortWay/sortOrder/page`，
`rows=10` 生效返回 10 条；站点自身分页回调还带 `isFacet=true&view=standard&scWay=full`，非必需）。

每条结果是 `<ul class="libBookUl">` 下的 `<li class="libBookLi ...">` 容器：

- 书目 ID 与标题：`<a href="javascript:bookDetail({bookrecno},1,1);" class="libBookDetNm">标题</a>`；
  注意同容器有序号 `<span class="libBookDetNm mbLibBookNum">1</span>`（同 class 但是 span），
  必须按 **a 标签**取标题。封面 `<img isbn="..." bookrecno="...">` 属性可作 ID/ISBN 兜底。
- 字段标签是 `<span class="libBkDetTit">` 文本，标签后随 `<a class="color33 layerTip">`：
  - `责任者` → 作者（文本含 MARC 责任方式，如「刘慈欣著」，同广州口径）
  - `出版信息` → 出版社（a 文本，如「重庆出版社」）；出版年是该 a **之后**的裸文本 `,2022`
  - `ISBN` → 标签后裸文本
- 总数：`<span class="schResNum">检索结果共有<i class="color50 schResNumIn">163</i>条</span>`
  （不是广州的「检索到: N 条结果」文案）。
- 分页：**JS 配置而非渲染锚点**——`$("#pagination3").pagination({currentPage: 1, totalPage: 17, ...})`；
  「下一页/首页/尾页」只存在于 JS 字符串（`nextPageText: "下一页"`），页面**没有**可点的
  分页 a 标签。`total_pages` 取 `totalPage:\s*(\d+)`；`has_next` 按 `currentPage < totalPage`
  计算（广州的「下一页」锚点探测法在此恒 False，不可用）。
- 空结果页：无 `libBookLi`、无 `schResNum`，总数区整体不渲染；有明确提示锚点
  `<div class="notResArea">` + `<span class="notFindFt">图书馆暂时没有“××”相关书目</span>`
  → `total_results` 判 0（源站明说没有，不是猜测）；JS 分页配置仍在（`totalPage: 1`）。
- 词条目内「馆藏信息」tab 是 iframe 异步加载（`holdingPreview_{id}`），
  `availability_summary` 同广州恒空串。
- 解析按 `bookDetail(数字` 提取书目 ID；空结果页含 `bookDetail(` 的 JS 定义处
  与杭州同款（无数字跟随不误判，实测空页 `bookDetail\(\d+` 计数为 0）。
- 带连字符 ISBN 的 marc 检索行为未对台州实测；家族「首搜为空去连字符重试一次」
  语义已在适配器内镜像（仅在首搜为空且含 `-` 时多发一次请求）。

## 详情页结构（bkTxt 模板，默认视图）

默认 `GET /opac/book/{bookrecno}` **没有** `bookInfoTable`/`leftTD`/`rightTD`/`h2`，
家族 `parse_detail` 返回全空。实际结构：

- 标题：`<a href="#" class="bkTxtTit">三体：新版</a>`（**完整标题**，含副题名）。
- 字段在 `bkTxtIn` 下的**左右两列**：`<div class="bkTxtLeft flLeft">` 与
  `<div class="bkTxtRight flLeft">`，各含一个 `<ul>`，每字段一个
  `<li>标签：<span>值</span></li>`。样例分布——左列：ISBN、出版发行、主要责任者；
  右列：价格、语种、载体形态、主题词、中图分类法。**列的划分不可假设**
  （页内 JS 会按两列条数动态搬移 li），解析必须同时跟踪两个容器。
- 标签词表与广州一致（ISBN / 出版发行 / 主要责任者 / 中图分类法 / 内容提要）：
  - `ISBN` → span 文本 `978-7-229-16692-2 价格：CNY42.00`，正则 `[\d\-]{10,}` 同广州
  - `出版发行` → span 内 `出版地文本 + <a>重庆出版社，</a> + 2022`：出版社取首个
    a 文本（去尾逗号），出版年正则 `(?:19|20)\d{2}`
  - `主要责任者` → span 内 `<a>刘慈欣</a> 著`：取首个 a 文本（无 a 退回首词，同广州）
  - `中图分类法` → span 文本 `I247.55 版次： 5`：取「版次」之前，同广州
- 简介：服务端 HTML **没有**「内容提要」行（本样例记录）；默认视图的内容简介由
  第三方推送 API（`api.interlib.com.cn:6699/interes`）异步注入 `#bookContentSummary`，
  不可依赖 → `summary` 常为空串；若个别记录带「内容提要」li，按同标签照抓。
- `view=simple&flag=printer` 打印视图渲染家族标准 `bookInfoTable`/`leftTD`/`rightTD`，
  家族 `parse_detail` 除标题外全部字段可直取；但其标题行标签是「题名」且**只有正题名**
  （`三体`，丢副题名「新版」；广州基准 h2 是完整标题）。为保标题保真，适配器采用
  默认视图 + 本地 bkTxt 解析，不用 simple 视图。搜索页加 `view=simple` 返回 5.5KB
  空壳（无结果无总数），该参数只对详情页有效。
- 详情页与搜索页均**不需要** `curlibcode`（直接可通，非多租户云托管形态）。

## 馆藏 JSON（与广州基准完全同构，家族解析器原样可用）

`GET /opac/api/holding/{bookrecno}?limitLibcodes=&isCluster=` 顶层键与广州一致：
`holdingList`、`libcodeMap`、`localMap`、`holdStateMap`、`pBCtypeMap`、
`barcodeLocationUrlMap`、`libcodeDeferDateMap`、`loanWorkMap`、`shelfnoUrlMap`。
单册字段同款（`barcode/callno/curlib/curlocal/state/loan/shelfno/...`）。

- `holdStateMap` 除广州已知 29 项外，台州出现扩展状态码：`32=已签收`、`33=已通还`、
  `34=损坏`、`35=丢失赔书`、`36=已装订`（状态原值照登；家族词表判定——「损坏/丢失赔书」
  含不可借词命中不可借，「已签收/已通还/已装订」词表外**保守判不可借**，符合家族口径）。
- 应还日期：`loanWorkMap[barcode].returnDate`（epoch 毫秒，UTC+8），家族
  `_holding_due_date` 直取。本 fixture《三体：新版》5 册**全部借出**且都带应还日期
  （2026-08-18 / 2026-09-22 / 2026-10-05 / 2026-10-17 / 2026-10-28，实抓日 2026-10-02，
  前两个日期早于实抓日——逾期形态，原值照登不判断），恰好覆盖广州 fixture 缺的借出样例。
- 馆藏地点含地铁 S1 线站点（`S1线南屏站`）与信阅柜（`台州文旅局信阅柜`）等自助网点，
  位置码经 `localMap` 翻译，原值照登。
- `state=3`（借出）的单册 `loan` 字段为 null，借出信息全在 `loanWorkMap`，与广州一致。

## 实测请求台账（侦察 + fixture 共 8 次 GET，全部 200）

首页 ×1、搜索页 ×4（p1、p2、空结果、view=simple 实验）、详情页 ×2（默认、simple）、
馆藏 JSON ×1。无 401、无验证码、无 TLS 重置。
