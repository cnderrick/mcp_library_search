# 武汉图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`https://opac.whlib.org.cn/opac/index`（图创 Interlib，页标题「检索系统」）。
抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认模板结果页（`bookmeta` 容器）。实抓「三体」共 263 条、14 页。

- **末页分页锚点 quirk**：命中数 > 0 时「下一页」锚点恒渲染（末页指向同页），
  末页 `has_next` 可能为 True；总数可解析，以 `total_pages` 为准。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓首条《三体》
  （1900722937）。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，263 条、14 页 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/{recno}`（三体，1900722937） |
| `holding.json` | `GET /api/holding/{recno}` |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
