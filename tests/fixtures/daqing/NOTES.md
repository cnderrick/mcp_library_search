# 大庆市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://111.43.226.77:8091/`（图创 Interlib，页标题「检索系统」，
meta keywords 自报「opac, 图创, interlib, 图书检索, 借书, …, 大庆市图书馆」）。
抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`、`ctx=""`。

- **应用上下文是根路径 `""`（非 `/opac`）**：`/opac/index`、`/opac/search`、
  `/opac/api/*` 一律 HTTP 404；正确的入口是 `/`（或 `/index`），检索 `/search`，
  详情 `/api/book/{recno}`，馆藏 `/api/holding/{recno}`。登记的
  `http://111.43.226.77:8091/opac/index` 已修正为根路径。

## 检索：HTML 检索页直连

`GET /search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认模板结果页（`bookmeta` 容器）。实抓「三体」共 29 条、2 页。

## 详情与馆藏

- **详情**：`GET /api/book/{recno}` JSON（`api_detail=True`），实抓首条
  《三体》中的物理学》（273681），ISBN `978-7-5364-8068-1`。
- **馆藏**：`GET /api/holding/{recno}` JSON，家族 parser 零改动。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹（`/`） |
| `search_p1.html` | HTML 检索「三体」，29 条、2 页 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/{recno}`（273681） |
| `holding.json` | `GET /api/holding/{recno}` |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
