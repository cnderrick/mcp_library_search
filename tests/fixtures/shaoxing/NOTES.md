# 绍兴 OPAC 页面结构侦察（2026-10-02 实抓）

站点：`https://opac.sxlib.com`（入口 `/opac/index`）。首页 `<title>检索系统</title>`，
`<meta name="keywords">` 含「opac, 图创, interlib, 图书检索, 借书, 绍兴市公共图书馆联合目录」，
页脚 `© www.interlib.com.cn`——**确属图创 Interlib**。但模板代与广州/杭州基准不同：
静态资源走 `/opac/media/pro2018/`（下称「pro2018 模板」），搜索结果页与详情页的
HTML 结构与家族 parser 依赖的标记**全部对不上**。全部只读 GET，HTTP 200。

## 馆名

- 主馆全称：**绍兴图书馆**（搜索页 `title='绍兴图书馆'`；holding JSON `libcodeMap` 里
  `sxslib → 绍兴图书馆`）。
- 系统口径：**绍兴市公共图书馆联合目录**（首页 meta keywords），联合 `sxslib 绍兴图书馆`、
  `syslib 上虞图书馆`、`999 中心馆` 等多馆；搜索结果里另见「绍兴诸暨市图书馆」。
- 建议 `name_cn` 记「绍兴图书馆」（主馆全称照实），联合目录属性写进 data-sources 备注。

## Fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `search_p1.html` | `GET /opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1` | 搜索第 1 页，`numFound=203`、`totalPage: 21` |
| `detail.html` | `GET /opac/book/1227282` | 《三体》（刘慈欣著，重庆出版社 2010.11）详情页 |
| `holding.json` | `GET /opac/api/holding/1227282?limitLibcodes=&isCluster=` | 馆藏 JSON；顶层键与广州一致，但本书 `holdingList` 为空（见下） |

> 另测：`isCluster=true` 与另一书目 `1553034` 的 holding 响应均 47654 字节、`holdingList` 仍空
> （大字典 `libcodeMap`/`localMap` 恒定、单册数组空导致体积相同）。搜索页的「在馆」计数（页面出现
> 33 次）是前端经**批量 POST** `/opac/api/holding/getHoldingsBybookrecnos` 异步渲染的，
> 不在单书 GET 响应里。

## 搜索页结构（pro2018 模板，与广州基准不同）

结果列表是 `<ul class="libBookUl">` → `<li class="libBookLi">`，**不是** `<div class="bookmeta" bookrecno="…">`。
`bookrecno` 不挂在条目容器上，而是散落在内层元素（`<img bookrecno>`、`<span id="book_summary_…" bookrecno>`、
`<li class="…bkDetTabLi" bookrecno>`）；稳定 ID 要从题名锚点的 `bookDetail(1227282,1,1)` 调用里取。

单条目字段标记（实测《三体》条目）：

- 题名：`<a href="javascript:bookDetail(1227282,1,1);" class="libBookDetNm">三体</a>`
  —— class 是 `libBookDetNm`，**不是** `title-link`。
- 责任者：`<span class="libBkDetTit">责任者</span> <a … class="color33 layerTip" id="name-1">刘慈欣著</a>`
  —— 靠「责任者」标签 + `layerTip` class，**不是** `author-link`。
- 出版信息：`<span class="libBkDetTit">出版信息</span> <a … class="color33 layerTip" id="name1">重庆出版社</a> ,2010.11`
  —— 靠「出版信息」标签，**不是** `publisher-link`；出版年 `,2010.11` 裸文本跟在链接后。
- 文献类型：`<span class="ebkType">图书</span>`。

总数与分页（**走 JS 变量，不是广州的可见文案**）：

- 总数：`numFound=203`（JS 里），页面**无**「检索到: N 条结果」文案（`检索到` 计数 0）。
- 总页数：`totalPage: 21`（JS 里），页面**无**「共 N 页」文案。
- 「下一页」锚点存在（家族靠它判 `has_next`，此标记绍兴也有）。

## 详情页结构（pro2018 模板，与广州基准不同）

layui-tab 模板（`class="bookDetPie layui-tab layui-tab-brief"`）。**无** `bookInfoTable`、
**无** `leftTD`/`rightTD`、**无** `<h1/h2/h3>`、**无**「主要责任者」「内容提要」标签。

- 题名：`<a href="#" class="bkTxtTit">三体</a>`（class `bkTxtTit`，不是 `<h2>`）；
  另有 JS 变量 `var booktitle = "三体"` / `var name = "三体"`。
- 字段是 `<li>标签：<span>值</span></li>` 列表，实测可见标签：
  - `ISBN：`（行 2700）→ `<span>978-7-229-03093-3</span>`
  - `出版发行：`（行 2787）→ `<span><a class="bkTxtInLink">重庆出版社，</a>2010.11</span>`
  - `载体形态：`（行 3043）
  - `中图分类法：`（行 3135）→ `<span>…</span>`
- 责任者/引文：在引文块 `刘慈欣著.三体.重庆出版社,2010.11.`（行 3360），无独立「主要责任者」标签行。
- 简介：本页未见「内容提要」「简介」「摘要」标签（计数均 0）；简介可能异步或在另一 tab，未深挖。

## 馆藏 JSON（结构兼容，数据待查）

`GET /opac/api/holding/{bookrecno}` 顶层键与广州**完全一致**：
`shelfnoUrlMap`、`loanWorkMap`、`holdingList`、`libcodeMap`、`localMap`、`pBCtypeMap`、
`holdStateMap`、`barcodeLocationUrlMap`、`libcodeDeferDateMap`。`holdStateMap` 形状也一致
（`{stateType, stateName}`，如 `32→已签收`、`0→流通还回上架中`、`1→编目`、`33→已通还`）。
详情页 JS `holdingInfo()` 正是读 `data.holdingList`/`libcodeMap`/`localMap`/`holdStateMap`/`loanWorkMap`
——与 `interlib.parser.parse_holdings` 期望的字段一一对应。**结构上 holding 面兼容家族 parser。**

但采样书目（`1227282`《三体》、`1553034`）的单书 GET 响应 `holdingList` 均为空。
原因未定（联合目录可能需指定馆码/会话，或这些 bookrecno 是联合层书目、本地单册挂在别处）；
搜索页的「在馆」计数走批量 POST `/opac/api/holding/getHoldingsBybookrecnos`。
按「不确定数据不做预设判断」原则：holdingList 空照实记录，不猜语义。

## 与广州基准的兼容性结论（实证）

用当前家族 parser 直接跑绍兴 fixture（`uv run python3` 实测，可复现）：

| 解析面 | 家族函数 | 绍兴 fixture 结果 | 判定 |
|---|---|---|---|
| 搜索页 HTML | `parser.parse_search` | `books: 0`、`total_results: None`、`total_pages: 1`、`has_next: False` | **不兼容** |
| 详情页 HTML | `parser.parse_detail` | `title/author/isbn/publisher/call_number` 全空、`summary` 长度 0 | **不兼容** |
| 馆藏 JSON | `parser.parse_holdings` | 结构匹配（本书 `holdingList` 空 → 0 条） | 结构兼容 |

家族 `_SearchParser` 依赖 `class="bookmeta"` 容器 + `title-link`/`author-link`/`publisher-link`
锚点 + `检索到: N 条`/`共 N 页` 文案；绍兴这些**结果锚点全部不存在**：`<div class="bookmeta"` 计数 0，
`<a class="title-link">`/`author-link`/`publisher-link` 结果锚点计数 0，`检索到` 文案计数 0。
（注：`title-link` 字样在页面出现 1 次，但只是遗留 JS 选择器 `$(".title-link").each(...)`，
并非结果标记；pro2018 模板的题名实际用 `libBookDetNm`。）家族 `_DetailParser`
依赖 `bookInfoTable` + `leftTD`/`rightTD` + 首个 `<h2>` + `主要责任者`/`内容提要` 标签；绍兴
**全部缺失**（计数均 0）。三个解析面里两个（搜索、详情）根本不兼容，且差异是「整套模板代不同」，
不是锚点缺一个、可用 `InterlibConfig` quirk 字段（小开关，如 `curlibcode`）表达的程度。

## 处置：降级「待调研」

绍兴确是 Interlib，但跑的是 pro2018 模板代，搜索/详情两个 HTML 解析面与家族 parser 完全不兼容。
要让家族覆盖绍兴，须在 `interlib/parser.py`（**本次禁改领地**）里新增「模板代分支」：
按 `libBookUl`/`libBookDetNm`/`责任者`+`出版信息` 标签/`numFound=`/`totalPage:` 重写搜索解析，
按 `bkTxtTit`/`<li>标签：<span>值</span></li>` 重写详情解析——这是一套并行 parser，
远超 quirk 字段表达能力，也超出「照广州/杭州同款方式接入」的前提。按任务边界「停手不硬写」，
**该城降级「待调研」**，不产出 `adapters/shaoxing.py`（硬写会得到 0 条书、空详情的废适配器）。

holding JSON 面结构兼容这一事实保留：未来若在家族里补 pro2018 搜索/详情 parser 分支，
holding 解析可复用现有 `parse_holdings`（但需先查清联合目录下单书 GET `holdingList` 为空的取数条件）。

## 复抓命令（只读 GET，偶发 TLS 重置重试即可）

```
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
curl -sS -A "$UA" "https://opac.sxlib.com/opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1" -o search_p1.html
curl -sS -A "$UA" "https://opac.sxlib.com/opac/book/1227282" -o detail.html
curl -sS -A "$UA" "https://opac.sxlib.com/opac/api/holding/1227282?limitLibcodes=&isCluster=" -o holding.json
```

---

# 立项更新（2026-10-02 下午，batch3）：已接入 `adapters/shaoxing.py`

用户拍板「待立项的先搞」，绍兴按**台州已实证路径**立项：pro2018 搜索/详情
解析在适配器本地实现（不动家族共享模块），HTTP 层与馆藏层复用家族
（`interlib.client.get` + `interlib.get_holdings`）。真网冒烟全链路通过。

## 「holding 恒空」之谜已解（原「联合目录取数条件待查」关闭）

不是接口坏，是**采样偏差**：《三体》1227282/1553034/1553036 是联合层书目、
无本地单册——单书 GET 与批量 POST 对它们**都**返回空（holdingListMap 无键/
holdingList 空，libcodeMap/localMap 字典仍全量）。换鲁迅类书目（q=鲁迅
首页 5 个 id）批量 POST 全部有数据（1~3 条/书），单书 GET `879551` 也返回
完整 holdingList 3 条＋holdStateMap（state 2=在馆）＋loanWorkMap——**家族
参数形态（limitLibcodes=&isCluster=）实测可用**，`parse_holdings` 零改动
解析成功（上虞图书馆/储藏外借·资料/localMap 翻译正常）。

批量端点 `POST /opac/api/holding/getHoldingsBybookrecnos`（form 体
`bookrecnos=id1,id2,`，响应 `holdingListMap/localMap/libcodeMap/
libcodeDeferDateMap`，**无 holdStateMap**）是搜索页「在馆」计数的异步来源，
适配器不依赖它，仅存档为取数条件证据（batch_luxun.json）。

## pro2018 解析锚点（台州同款全部实证，差异两处）

- 搜索页与台州**逐锚点同款**：`schResNumIn`（「检索结果共有<i>203</i>条」）、
  JS `totalPage: 21`/`currentPage: 1`、`libBookLi`/`libBookDetNm`/
  `libBkDetTit`（责任者/出版信息标签）、`bookDetail(数字` id、封面 img
  `isbn=`/`bookrecno=` 属性（各 10 处）、空页 `notFindFt`——台州
  `_SearchParser` 逻辑原样适用（本地复制，共享模块化建议见交付报告）。
- 详情页同为 bkTxt 模板（`bkTxtTit`/`bkTxtLeft`/`bkTxtRight`、li 标签：
  ISBN/出版发行/价格/载体形态/主题词/中图分类法/相关资源），差异：
  1. **无「主要责任者」「内容提要」标签行**（两份实抓记录均缺）→ 责任者从
     引文块 `div.sendToConIn` 兜底：「刘慈欣著.三体.重庆出版社,2010.11.」
     取首个句点前段（原值照登含「著/编」）；summary 恒空串（数据边界，
     server 工具文案已声明）。
  2. 中图分类法值可能只剩「版次：」空壳（《三体》记录）→ call_number 空串
     照实；《鲁迅：1881--1936》记录有 K825.6。

## 新增 fixture（2026-10-02 下午实抓，共 7 请求，间隔 ≥2.5s）

| 文件 | 来源 | 说明 |
|---|---|---|
| `search_luxun_p1.html` | `GET /opac/search?q=鲁迅&…` | numFound 8523，10 条，id 60599 起 |
| `search_empty.html` | `GET /opac/search?q=azbycxq不存在xyz&…` | notFindFt 空页锚点，无 schResNumIn |
| `detail_879551.html` | `GET /opac/book/879551` | 《鲁迅：1881--1936》北京鲁迅博物馆编，文物出版社 1977.3，K825.6 |
| `holding_879551.json` | `GET /opac/api/holding/879551?limitLibcodes=&isCluster=` | 家族参数形态，holdingList 3 条全在馆（上虞） |
| `batch_luxun.json` | `POST /opac/api/holding/getHoldingsBybookrecnos`（form bookrecnos=5 ids） | holdingListMap 每书 1~3 条，取数条件证据 |

请求清单：批量 POST ×2（三体 3 id 空、鲁迅 5 id 有数据）、单书 GET ×2
（1227282 复核空、879551 有数据）、搜索 ×2（鲁迅、空检索）、详情 ×1
（879551）。加上适配器真网冒烟 4 请求（search 三体/detail 1227282/
holdings 879551/holdings 1227282），下午共约 11 请求，全部只读，未触发风控。

## 冒烟结果（适配器真网实跑）

`search_books("三体", limit=5)` → total=203/5 条/41 页；
`get_book_detail("1227282")` → 三体/刘慈欣著/重庆出版社/2010/
978-7-229-03093-3/call_number 空/summary 空；`get_holdings("879551")` →
3 条上虞图书馆在馆；`get_holdings("1227282")` → 0 条（联合层边界）。
