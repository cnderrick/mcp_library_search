# 三明市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://opac.fjsmlib.cn:6999/opac/index`（图创 Interlib，页标题「检索系统」，meta keywords 自报
「opac, 图创, interlib, 图书检索, 借书, …, 三明市图书馆」）。抓取只读 GET。注册登记见
docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认（非 pro2018）模板结果页（`div.bookmeta` 容器）。实抓「三体」71 条、
共 4 页；首条《三体》（刘慈欣(1963 );著，2008）。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓《三体》
  ISBN `978-7-5366-9293-0`、中图分类法 `I247.55`、内容提要长度 0。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 2 条、
  2 条在馆；馆名：三明市少儿馆。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 71 条、共 4 页 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/{recno}`（三体） |
| `holding.json` | `GET /api/holding/{recno}`（2 条） |

## 数据边界

- meta keywords 自报「三明图书馆总分馆」；首条馆藏挂「三明市少儿馆」，属总分馆口径。
- 首条著者原值含生卒年与多余空格「刘慈欣(1963 );著」，照登。
- 详情接口 `/opac/api/book/{recno}` 偶发 `RemoteDisconnected`／「Empty reply from server」（源站
  瞬时限流／不稳定），稍候重试即通；检索页与馆藏接口同期正常，属源站侧问题，非解析缺陷。
- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
- 内容提要缺失时 `summary` 空串，属记录级数据事实。
