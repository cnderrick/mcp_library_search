# 盐城市图书馆 LibStar Find 侦察（2026-10-03 实抓）

站点：`https://findyctsg.libsp.com`（页标题「统一检索」）。单实例——实抓馆藏
分组只有 `盐城市图书馆`（libCode 10002600001）。立项登记见
docs/data-sources/cn.md 总览表盐城行。

技术组件：**图星 LibStar Find**（北京图星·超星集团），与无锡新吴、徐州、淮安
同款，协议（HTTP 层＋解析）见 `libstar/` 家族。信封 `{success, message,
errCode, data}`。

## 网关：两个必需请求头（同家族，本城实测复现）

| 头 | 值 | 缺失后果 |
|---|---|---|
| `Referer` | 任意值（只校验存在） | 内容类端点回 `errCode:9999`「系统访问中断，请稍后再试！」 |
| `groupcode` | `100026` | HTTP 200 ＋ `success:true`，但 `numFound` 恒 0（静默空结果） |

对照实测：带两头的检索「三体」`numFound=857`；去掉 `groupcode` 后同一请求
`numFound=0`、`searchResult` 空。

## 三原语接口形态

与无锡/徐州/淮安家族完全同构（详见 `tests/fixtures/wuxi/NOTES.md`）：
检索 `POST /find/unify/search`；详情 `GET /find/searchResultDetail/getBookDetail?recordId=`；
馆藏 `POST /find/physical/groupItemsByLibCode`。字段码 `cnb01`/`cnb03`/`cnb04`/
`cnb67`/`cnb96` 同形，家族 parser 零改动可用。

## 差异点（均不需要新 quirk 字段）

1. **单实例单馆**：馆藏分组只有 `盐城市图书馆`，无多源归并，`book_id` 即裸
   `recordId`（数字字符串化）。
2. 其余与无锡/徐州/淮安一致：域名 `*.libsp.com`，状态词表 `在架`／
   `借出-应还日期:YYYY-MM-DD`，应还日期内嵌在 `processType` 里。

## 状态词表（实抓样本）

同无锡：`在架`（可借）、`借出-应还日期:YYYY-MM-DD`（不可借，日期内嵌）。实抓
671583（《三体：图像小说》）的 3 册：1 册 `在架`、2 册 `借出-应还日期:*`
（2025-11-23、2026-01-10）。未观测值一律保守判不可借、`status` 原值照登
（同重庆口径）。

## 数据边界

- 检索结果 `publisher` 可为 null（老书目）→ 空串；`publishYear` 可带月份
  （实抓 `2025.1`）→ 取四位年份。
- 应还日期内嵌在 `processType` 里，访客视角即可拿到。
- 索引可借概况与馆藏端点各自如实呈现，不互相编造（同无锡/淮安数据边界）。

## fixture 清单

| 文件 | 内容 |
|---|---|
| `index.html` | 站点首页（SPA 外壳，指纹「统一检索」） |
| `search_santi.json` | `POST /find/unify/search` 检索「三体」，numFound=857 |
| `search_empty.json` | 生造关键词，numFound=0 |
| `search_santi_nogroup.json` | 同上「三体」但不带 groupcode 头，numFound=0（对照证据） |
| `detail_santi.json` | `GET getBookDetail?recordId=671583`（《三体：图像小说》） |
| `holding_santi.json` | `POST groupItemsByLibCode` recordId=671583，3 册（1 在架 2 借出） |
