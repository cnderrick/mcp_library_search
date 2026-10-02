# 无锡市新吴区图书馆 LibStar Find 侦察（2026-10-02 实抓）

站点：`http://wxxqlsp.xw.i-wnd.cn:8013/#/home`。单馆——全站只有
「无锡市新吴区图书馆」一个馆（`findConfig/getLibraryList` 返回
`libCode 80050700001`，`facetResult.libCode` 也只有这一个值）。

技术组件：**图星 LibStar Find v3.2023.12**（北京图星软件·超星集团）——统一检索/
发现系统，Java/Spring 后端，响应包封 `{success, message, errCode, data}`。与图创
Interlib 是两家厂商，不共用代码。后端响应头 `X-Application-Context: oga:dev:10010`
（跑在 dev 档，不影响功能）。

## 网关：两个必需请求头（本城最大的坑）

**这是 2026-10-02 初判「站点不通」的直接原因，务必先读这一节。**

| 头 | 值 | 缺失后果 |
|---|---|---|
| `Referer` | 任意值（实测 `http://example.com/` 也行，只校验存在） | **所有内容类端点**返回 `errCode:9999`「系统访问中断，请稍后再试！」 |
| `groupcode` | `800507`（新吴区租户号，≠ libCode `80050700001`） | HTTP 200 ＋ `success:true`，但 `numFound` 恒 0（静默空结果） |

`Referer` 缺失时的 9999 措辞直指「下游 OPAC 不可达」，极易误判成服务端宕机——
实际是站点的反爬兜底。配置类端点（`findConfig/*`、`webSite/*`）不受影响，所以站点
看起来「一半是活的」。

复现对照（同一请求体，只改头）：

```
带 Referer + groupcode  → success:true, numFound:83
带 Referer，无 groupcode → success:true, numFound:0
无 Referer              → errCode:9999
```

## 三原语接口形态

全部相对根路径，无额外前缀。

### 检索 `POST /find/unify/search`

请求体是固定模板（约 30 个字段），只有 `searchFieldContent` / `page` / `rows`
随调用变化，其余照抄。`searchField` 固定 `keyWord`（任意词，书名/作者/ISBN 通吃），
`matchMode: "2"`，`sortField: "relevance"`，`indexSearch: 1`。

响应：`data.numFound`（真实总数，扁平数字，非嵌套）＋ `data.searchResult[]`
＋ `data.facetResult`（14 个聚类维度）＋ `data.hlResult`（高亮，按 recordId 索引）
＋ `data.levelResultList`（恒空）。

`searchResult[]` 用到的字段：`recordId`（稳定 id，数字，馆藏/详情直接可用）、
`title`、`author`、`publisher`（可为 null）、`publishYear`、`isbn`、
`adstract`（**注意拼写，源站就是 adstract**）、`callNo`（数组）/`callNoOne`、
`physicalCount`（总馆藏册数）、`onShelfCountI`（在架册数）、`docName`（"图书"）。

**ISBN 检索带不带连字符都命中**（实测 `978-7-5086-6831-4` 与 `9787508668314`
均 numFound=1），无需广州/青岛那种去连字符重试。

### 详情 `GET /find/searchResultDetail/getBookDetail?recordId={数字}`

必须 GET（POST 同参数回 9999）。响应 `data.bean2List[]`，每条
`{key, description, fieldVal}`，字段码：

| 码 | 含义 | 样例 |
|---|---|---|
| `cnb01` | 题名/责任者 | `上瘾:让用户养成使用习惯的四大产品逻辑/(美)尼尔·埃亚尔…著` |
| `cnb03` | 出版发行项 | `北京:中国人民大学出版社,2022`（无出版社时为 `北京,2017`） |
| `cnb04` | ISBN及定价 | `978-7-5086-6831-4 精装/CNY49.00`；**可重复**，见下 |
| `cnb10` | 载体形态项 | `23,224页:图;21cm` |
| `cnb14` | 并列正题名 | `Hooked:how to build habit-forming products` |
| `cnb20` | 其它题名 | 可多条 |
| `cnb67` | 中图法分类号 | `TB472`，**可多条**（如 `F713.55` ＋ `F713.5`） |
| `cnb96` | 提要文摘附注 | 内容简介 |

`data` 顶层只有 `author`（恒 null）与 `bean2List` 两个键，其余字段全在 bean2List 里。
**详情页无独立索书号字段**，`call_number` 取 `cnb67`（中图分类号）——与青岛家族
口径一致；完整索书号在馆藏明细的 `callNo` 里。

### 馆藏 `POST /find/physical/groupItemsByLibCode`

请求体 `{"recordId": "703048"}`。响应 `data.sortedList`：按馆名分组的对象，
每组 `{phyItemVo[], mainFlag, libName, libCode}`。新吴区全站单馆，实际只有一组。

`phyItemVo[]` 用到的字段：`itemId`、`callNo`（索书号）、`barcode`、
`basecode`/`propNo`、`libName`、`locationName` / `realLocationName` / `curLocationName`
（同值，馆内位置）、`shelfNo`（实测空串）、`inDate`（入藏日期）、
**`processType`（状态，见下）**。

## 状态词表（30 个单册实抓样本）

只有两个值，无歧义：

| `processType` 实测值 | 出现 | 归一 |
|---|---|---|
| `在架` | 27 | `available=True` |
| `借出-应还日期:2025-10-10` | 1 | `available=False`，`due_date=2025-10-10` |
| `借出-应还日期:2026-10-30` | 1 | 同上 |
| `借出-应还日期:2026-10-12` | 1 | 同上 |
| `借出-应还日期:2016-07-01` | 1 | 同上 |

**应还日期直接内嵌在状态串里**——访客视角就能拿到，比浙图（拿不到）强。日期可为
过去（如 2016-07-01，疑似长期未还），原值照登不做判断。

未观测到的值一律保守判不可借、`status` 原值照登（同重庆口径）。

## 数据边界

- 检索结果的 `publisher` 可为 `null`（老书目），`BookSummary.publisher` 出空串。
- 详情 `cnb03` 无出版社段时（`北京,2017`）只解析得出出版年。**出版地不等于出版社**：
  实抓 `重庆,2016.6` 只有出版地没有出版社，`publisher` 出空串，不拿出版地冒充。
- **年份可带月份**：检索 `publishYear` 与详情 `cnb03` 都实测出过 `2016.6`
  （三体典藏版 764039）。归一为四位年份（同青岛/重庆/宁波口径），不做换算猜测。
- **`cnb04` 可重复且首条可能没有 ISBN**：实抓 764039 依次是
  `'/271.00 (8册)'`（纯定价行）与 `'978-7-229-10062-9/271.00 (8册)'`。
  照单取首条会把 ISBN 解析成空串——取首个切出的非空 token。
- `cnb67` 可多条，`call_number` 取首条。
- **检索索引与馆藏端点会不一致**：实抓 143656（《活着》李玉霄版）索引 `physicalCount=1`
  且 `onShelfCountI=null`，而 `groupItemsByLibCode`、`physical/groupitems`、
  `getCatalog` 三种取法全返回空。**馆藏端点为准**，适配器如实返回空列表；
  `availability_summary` 因缺 `onShelfCountI` 留空串，不拿索引计数编造。
  注意 `onShelfCountI=null` 本身**不**等于无馆藏（311140 同样为 null 却有 1 册）。
- 可借概况：检索结果提供 `physicalCount`（总册）与 `onShelfCountI`（在架），
  站点 UI 即以此显示「纸本(5) / 可借(4)」；`availability_summary` 由此二值拼装。

## 多源预留

无锡市图书馆（主馆）后续接入，届时在本适配器内作第二数据源、按 ISBN 归并
（天津口径）。`book_id` 从第一天就带 `WXXW:` 源前缀，故新增源不改变既有 id 契约。
预留源码 `WXST`，优先级排在新吴区之前（主馆在前）。

## fixture 清单

| 文件 | 内容 |
|---|---|
| `search_santi.json` | `POST /find/unify/search` 检索「三体」，numFound=66 |
| `search_shangyin.json` | 同上检索「上瘾」，numFound=83 |
| `detail_shangyin.json` | `GET getBookDetail?recordId=703048`（《上瘾》） |
| `detail_sikao.json` | 同上 recordId=829436（《思考上瘾》，cnb03 带出版社段） |
| `detail_santi_death.json` | 同上 recordId=764039（三体典藏版：cnb04 重复、年份带月、无出版社段） |
| `holdings_shangyin.json` | `POST groupItemsByLibCode` recordId=703048，5 册 |
