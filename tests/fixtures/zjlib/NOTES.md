# 浙江图书馆（www.zjlib.cn）fixture 说明

抓取日期：2026-10-02。站点：`https://www.zjlib.cn`，API 基址 `/bff-api/`（BFF 网关）。
全部 HTTP 200，POST JSON，无需鉴权；共 8 个请求（含 3 个探针）。
必带请求头：`Content-Type: application/json`、`BFF-ORG-ID: 1916318653650423810`、
`Accept-Language: zh-CN;q=0.9`、常规 Chrome UA。

| 文件 | 来源 |
|---|---|
| `search.json` | `POST /bff-api/search-admin-service/open-api/search/pageList`，body `{"metadataType":"work","current":1,"size":10,"query":[{"key":"","value":"三体","condition":"and","match":"phrase_fuzzy"}],"sortBy":[]}`（total=1811） |
| `search_empty.json` | 同上，`value="azbycxq不存在xyz"`（records=[]，total=0，pages=0） |
| `detail.json` | `POST /bff-api/portal-admin-service/portal-pc-api/search/getWorkById`，body `{"bibliosId":"11000002313805","orgId":"1916318653650423810"}`（《三体》重庆出版社 2008） |
| `holdings.json` | `POST /bff-api/portal-admin-service/portal-pc-api/search/resourceList`，body `{"id":"60204f08e60757b629109b158cfbf13f","sourceType":"0"}`（同上书的单册列表，28 条） |
| `probe_page2.json` | pageList `current=2`（分页探针） |
| `probe_resourcelist_originalid.json` | resourceList 误传 originalId 的探针 |
| `probe_detail_notfound.json` | getWorkById 不存在 id 的探针 |
| `probe_isbn.json` | pageList 任意词检索 ISBN 探针 |

## 与调研笔记（docs/team/research/2026-10-02-spa-nblib-xwnd-zjlib.md）的出入

以本 NOTES 为准（实抓优先）：

1. **详情响应是嵌套的**：书目字段在 `data.record` 下（`data` 只含 `fields` 与 `record`
   两个键），调研笔记写成了字段直接在 `data` 下。
2. **详情的 `originalId` 是数组**：一个 work 可聚合多个书目实例
   （实测 `["11000002313805","110000011987311"]`），`workId` 是裸字符串。
3. `description` 是数组（每元素一段，实测单元素 `["“地球往事”三部曲之一"]`）；
   `descriptionAbstract` 实测 `[""]`。
4. 状态码 33（已通还）实测样本：`local_name` 与 `districtId` 均为 null（见下）。

## 检索 pageList

- 响应顶层 `{code, data, desc, success}`，`code=200`/`success=true` 为正常；
  `data` 含 `records/total/size/current/pages/fields/searchCount/orders`。
- **total 是真实总数**（1811），`pages`=总页数（182），`total_results`/`total_pages` 直取。
- **分页 `current` 真实生效**（probe_page2：current=2 与第 1 页记录零重叠）。
- record 字段（`id` 为裸字符串，其余均为数组、通常单元素）：
  `title`、`creator`（带责任方式后缀原值，如「刘慈欣著」）、`publisher`、`dateIssue`
  （脏值如 `"2019."`，年份按 `(?:19|20)\d{2}` 提取）、`identifierIsbn`、`originalId`
  （稳定记录号，作 book_id）、`instanceId`（带 `_cat` 后缀）、`id`（workId，检索系统
  内部 hash）、`docId`（1=图书）、`sourceType`（"0"=纸本）、`hasElectronicResource`、
  `available_on`、`sort`、`sourceId`。
- **identifierIsbn 有脏值**：实测 `"9784152098702 :"`（尾缀 " :"）、`"7-117-00998-5"`
  （10 位老 ISBN）、空串。展示原值照登；ISBN 归并键需从脏串按形态提取
  （`(?:97[89]\d{10}|\d{9}[\dXx])` 带数字边界断言）。
- **ISBN 形态关键词无需专门路由**：任意词（key=""，match=phrase_fuzzy）直接命中
  （probe_isbn：`9787536692930` → total=1 精确命中）。带连字符形态未实测。
- 检索 record 无可借性字段 → ZJ 成员 `availability_summary` 恒空串（数据边界，
  可借数在详情 `availableCount`，不为列表逐条加请求）。

## 详情 getWorkById

- 请求 `{"bibliosId": originalId, "orgId": "1916318653650423810"}`。
- 响应 `data.record` 字段多为单元素数组：`title/creator/publisher/publisherPlace/
  dateIssue/identifierIsbn/identifierIsbnPure/subjectClassica（中图分类法，作
  call_number）/language/formatPage/price/subject`；裸值：`workId/checkoutCount/
  itemCount/availableCount`。
- `identifierIsbnPure` 是站点自身的去连字符形态；详情 isbn 展示优先取
  `identifierIsbn` 原值，空则回退 Pure。
- **不存在/异常统一形态**：HTTP 200 + `{"code":500,"success":false,
  "desc":"服务器繁忙，请稍后重试"}`（probe_detail_notfound）——「记录不存在」与
  「真服务器忙」不可区分，desc 原值照登进报错。

## 馆藏 resourceList

- 请求 `{"id": workId, "sourceType": "0"}`；**id 必须是 workId**（检索 record 的
  `id` / 详情的 `workId`）。误传 originalId → HTTP 200 + `data["0"]=[]` 静默空
  （probe_resourcelist_originalid），**不报错**——因此 ZJ 成员馆藏链路是两跳：
  `getWorkById(originalId) → workId → resourceList(workId)`。
- 响应 `data` 按 sourceType 分桶，`data["0"]` 是纸本单册数组（实测 28 条）。
- 单册字段：`callno`、`local_name`（分馆/室名原值，如「之江馆文学借阅区」
  「曙光路馆中文文学图书借阅室」「安吉县天荒坪镇分馆」）、`state`（整数）、
  `state_name`（中文）、`barcode`、`checkout_count`、`districtId`（馆区，可为
  null）、`cur_local_id`/`org_local_id`、`vol_info`（卷册，实测 null；统一模型
  无对应字段，不输出）、`shelf_mark`（书架定位，实测全空）、
  `instance_original_id`、`holdingTotalCount`（字符串）、`id`（实例 id 带 `_cat`）。
- **字段映射**：`library` = 馆区名（districtId 查下表，查不到回退码原值，null →
  空串，与家族 libcodeMap 口径一致）；`location` = `local_name` 原值；
  `call_number` = `callno`；`status` = `state_name` 原值（缺失回退 state 码）；
  `due_date` 恒空串（见数据边界）。
- 馆区字典（调研实测，接口 `/portal-admin-service/portal-pc-api/search/staff-lib-district/list`）：

| districtId | 名称 |
|---|---|
| 1916325141324353538 | 之江馆区 |
| 1916325244624236545 | 曙光路馆区 |
| 1960228014308634625 | 大学路馆区 |
| 1960237529544437762 | 孤山路馆区 |
| 1960238282716921857 | 嘉业堂藏书楼 |
| 1953763801877389313 | 其他（分馆） |

## 状态码与可借判定（实测分布：3×20、2×5、16×1、9×1、33×1）

| state | state_name | 可借性 |
|---|---|---|
| 2 | 在馆 | ✅ 可借 |
| 3 | 借出 | ❌ |
| 9 | 锁定 | ❌ |
| 16 | 馆内阅览 | ❌ |
| 33 | 已通还 | ❌（保守；该样本 local_name/districtId 均为 null，疑似在途） |

词表外状态码一律保守判不可借；`status` 原值照登。

## 数据边界

- **应还日期**：访客视角拿不到（resourceList 无 due_date 字段，借出单册只给
  state_name；应还日期属读者级接口，需登录）→ 一律空串，不猜。
- `state=33`（已通还）语义未获官方确认，保守不可借。
- 无验证码、无限速墙实测；适配器仍按 ≥2 秒/host 节流（保守）。
