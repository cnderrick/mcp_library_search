# 黄冈市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://58.19.210.60:8081/opac/index`（图创 Interlib，页标题「检索系统」，meta keywords 自报
「opac, 图创, interlib, 图书检索, 借书, , 黄冈市图书馆」）。抓取只读 GET。
注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认（非 pro2018）模板结果页（`bookmeta` 容器）。实抓「三体」152 条、共 16 页。

- **分页锚点 quirk（家族通用）**：只要命中数 > 0，页内「下一页」锚点恒渲染（末页
  也 `has_next=True`），调用方应以 `total_pages` 为准；0 结果页无该锚点、`has_next=False`。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓首条《三体》（4005106334，2017），
  ISBN `978-7-5366-9293-0`、索书号 `I247.55`、出版年 `2017`。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 6 条，
  3 在馆 / 3 借出，网点含「蕲春县图书馆」「红安县图书馆」等（全市联合目录口径）。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 152 条、共 16 页 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/4005106334`（三体） |
| `holding.json` | `GET /api/holding/4005106334`（6 条） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
