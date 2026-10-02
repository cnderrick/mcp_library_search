# 徐州市图书馆 LibStar Find 侦察（2026-10-03 实抓）

站点：`https://findxz.libsp.com`（页标题「统一检索」）。同名多分馆——联合目录
含徐州图书馆（主馆，libCode 3203001001）与鼓楼区馆等成员馆（实抓馆藏分组见
`徐州图书馆`、`徐州鼓楼区`、`鼓楼图书馆黄楼分馆`）。立项登记见
docs/data-sources/cn.md 总览表徐州行。

技术组件：**图星 LibStar Find**（北京图星·超星集团），与无锡新吴同款，协议
（HTTP 层＋解析）抽到 `libstar/` 家族共用。信封 `{success, message, errCode, data}`。

## 网关：两个必需请求头（同无锡家族，本城实测复现）

| 头 | 值 | 缺失后果 |
|---|---|---|
| `Referer` | 任意值（只校验存在） | 内容类端点回 `errCode:9999`「系统访问中断，请稍后再试！」 |
| `groupcode` | `3203001001`（与主馆 libCode 同） | HTTP 200 ＋ `success:true`，但 `numFound` 恒 0（静默空结果） |

对照实测：带两头的检索「三体」`numFound=407`；去掉 `groupcode`（保留 Referer）
后同一请求 `numFound=0`、`searchResult` 空；去掉 `Referer` 后回 9999。

## 三原语接口形态

与无锡家族完全同构，详见 `tests/fixtures/wuxi/NOTES.md`：

- 检索 `POST /find/unify/search`，固定模板体，仅 `searchFieldContent`/`page`/`rows` 变；
- 详情 `GET /find/searchResultDetail/getBookDetail?recordId={数字}`（必须 GET）；
- 馆藏 `POST /find/physical/groupItemsByLibCode`，体 `{"recordId": "..."}`。

字段码（`cnb01` 题名/责任者、`cnb03` 出版发行项、`cnb04` ISBN及定价、`cnb67`
中图法分类号、`cnb96` 提要文摘附注）与无锡一致，家族 parser 零改动可用。

## 与无锡的差异点（均不需要新 quirk 字段）

1. **单实例、无多源归并**：本城所有分馆都在同一个 LibStar 实例里，由馆藏的
   `sortedList` 多分组承载（不像无锡预留了独立市图源）。适配器直接走家族单实例
   三原语，`book_id` 即裸 `recordId`（数字，字符串化使用）。
2. **馆藏主馆分组可能为空**：实抓 439114（《三体Ⅲ：死神永生》）`徐州图书馆`
   分组 `phyItemVo` 为空，仅 `鼓楼图书馆黄楼分馆` 有 1 册；家族按分组遍历，
   空分组自然贡献 0 条。
3. 详情响应 `errCode` 恒为 `9000124`（`success:true`），是源站该接口的固定返回码，
   非错误；家族 `check` 只认 `success`，不受影响。

## 状态词表（实抓样本）

| `processType` 形态 | 归一 |
|---|---|
| `在架` | `available=True` |
| `借出-应还日期:YYYY-MM-DD` | `available=False`，`due_date` 取该日期 |
| `本馆归还: 正在上架` | **保守判不可借**（`available=False`，`due_date=""`） |

实抓《活着》281453 的 20 册样本含以上三态：9 册 `在架`、10 册 `借出-应还日期:*`
（含 2021/2023 等过期值，原值照登）、1 册 `本馆归还: 正在上架`。未观测值一律
保守判不可借、`status` 原值照登（同重庆口径）。

## 数据边界

- 检索结果 `publisher` 可为 null（老书目）→ 空串；携带时原值照登。
- `publishYear` 可带月份（实抓 `2010.11`）→ 取四位年份。
- `physicalCount`/`onShelfCountI` 拼 `availability_summary`（如「纸本1，可借1」）；
  任一项缺失则留空串。
- 应还日期内嵌在 `processType` 里，访客视角即可拿到。

## fixture 清单

| 文件 | 内容 |
|---|---|
| `index.html` | 站点首页（SPA 外壳，指纹「统一检索」） |
| `search_santi.json` | `POST /find/unify/search` 检索「三体」，numFound=407 |
| `search_empty.json` | 生造关键词，numFound=0 |
| `search_santi_nogroup.json` | 同上「三体」但**不带 groupcode 头**，numFound=0（对照证据） |
| `detail_santi3.json` | `GET getBookDetail?recordId=439114`（《三体Ⅲ：死神永生》） |
| `holding_santi3.json` | `POST groupItemsByLibCode` recordId=439114，主馆空分组＋鼓楼黄楼 1 册 |
| `detail_huozhe.json` | 同上 recordId=281453（《活着》） |
| `holding_huozhe.json` | 同上 recordId=281453，20 册（在架/借出/正在上架三态） |
