# 来宾市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://180.141.168.199:8086/opac/index`（图创 Interlib，页标题「检索系统」，
meta keywords 自报「opac, 图创, interlib, 图书检索, …, 来宾市图书馆」）。抓取只读 GET。
注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认（非 pro2018）模板结果页（`bookmeta` 容器）。实抓「三体」15 条、共 1 页。

- **分页锚点 quirk**：只要命中数 > 0，页内「下一页」锚点恒渲染（末页指向同一
  `page=1`），故家族 `parse_search` 的 anchor 判定在末页也会给出 `has_next=True`。
  总数可解析（`total_results` 非 null），调用方应以 `total_pages` 为准。
  0 结果页无「下一页」锚点，`has_next=False`。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓《三体：新版》
  ISBN `978-7-229-16692-2`、索书号 `I247.55`。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 3 条，
  均在馆（`state=2`「在馆」），馆名「来宾市图书馆」。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 15 条、共 1 页 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/{recno}`（三体：新版，248234） |
| `holding.json` | `GET /api/holding/{recno}`（3 条，均在馆） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
- 实抓书目无内容提要，`summary` 为空串属记录级数据事实。
