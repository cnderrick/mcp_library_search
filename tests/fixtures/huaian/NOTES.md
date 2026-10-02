# 淮安市图书馆 LibStar Find 侦察（2026-10-03 实抓）

站点：`https://findhastsg.pub.chaoxing.com`（页标题「统一检索」）。联合目录含
淮安市图书馆（主馆，libCode 10038200001）与淮安市清江浦区图书馆
（10038200003）等成员馆。立项登记见 docs/data-sources/cn.md 总览表淮安行。

技术组件：**图星 LibStar Find**（北京图星·超星集团），与无锡新吴、徐州同款，
协议（HTTP 层＋解析）见 `libstar/` 家族。信封 `{success, message, errCode, data}`。

## 网关：两个必需请求头（同家族，本城实测复现）

| 头 | 值 | 缺失后果 |
|---|---|---|
| `Referer` | 任意值（只校验存在） | 内容类端点回 `errCode:9999`「系统访问中断，请稍后再试！」 |
| `groupcode` | `100382` | HTTP 200 ＋ `success:true`，但 `numFound` 恒 0（静默空结果） |

对照实测：带两头的检索「三体」`numFound=3110`；去掉 `groupcode` 后同一请求
`numFound=0`、`searchResult` 空。

## 三原语接口形态

与无锡/徐州家族完全同构（详见 `tests/fixtures/wuxi/NOTES.md`）：
检索 `POST /find/unify/search`；详情 `GET /find/searchResultDetail/getBookDetail?recordId=`；
馆藏 `POST /find/physical/groupItemsByLibCode`。字段码 `cnb01`/`cnb03`/`cnb04`/
`cnb67`/`cnb96` 同形，家族 parser 零改动可用。

## 与无锡/徐州的差异点（均不需要新 quirk 字段）

1. **单实例、无多源归并**：所有分馆在同一 `sortedList` 多分组里，`book_id` 即裸
   `recordId`（数字字符串化）。
2. **主馆分组可为空**：实抓 733596（《三体：图像小说》）`淮安市图书馆` 主馆分组
   `phyItemVo` 为空，仅清江浦区馆 2 册（均借出）。
3. **域名是 `*.chaoxing.com` 而非 `*.libsp.com`**：同为图星 LibStar Find，接入
   不受影响（家族 client 只认 `LibStarConfig.base_url`）。
4. **索引可借概况与馆藏端点会不一致**（同无锡数据边界）：实抓 733596 索引
   `physicalCount=2, onShelfCountI=2`（`availability_summary`「纸本2，可借2」），
   而馆藏端点两册均 `借出`、`only_available=True` 返回空。索引计数与馆藏端点各自
   如实呈现，不互相编造。

## 状态词表（实抓样本）

同无锡：`在架`（可借）、`借出-应还日期:YYYY-MM-DD`（不可借，日期内嵌）。实抓
《围城》299475 的 8 册含 6 册 `在架` 与 2 册 `借出-应还日期:*`（2025-12-25、
2027-01-17）。未观测值一律保守判不可借、`status` 原值照登（同重庆口径）。

## 数据边界

- 检索结果 `publisher` 可为 null（老书目）→ 空串；`publishYear` 可带月份
  （实抓 `2025.01`）→ 取四位年份。
- 应还日期内嵌在 `processType` 里，访客视角即可拿到。
- 部分书目馆藏端点返回空（主馆无实体单册），属记录级数据事实。

## fixture 清单

| 文件 | 内容 |
|---|---|
| `index.html` | 站点首页（SPA 外壳，指纹「统一检索」） |
| `search_santi.json` | `POST /find/unify/search` 检索「三体」，numFound=3110 |
| `search_empty.json` | 生造关键词，numFound=0 |
| `search_santi_nogroup.json` | 同上「三体」但不带 groupcode 头，numFound=0（对照证据） |
| `detail_santi.json` | `GET getBookDetail?recordId=733596`（《三体：图像小说》） |
| `holding_santi.json` | `POST groupItemsByLibCode` recordId=733596，主馆空分组＋清江浦区 2 册借出 |
| `detail_weicheng.json` | 同上 recordId=299475（《围城》） |
| `holding_weicheng.json` | 同上 recordId=299475，8 册（6 在架 2 借出） |
