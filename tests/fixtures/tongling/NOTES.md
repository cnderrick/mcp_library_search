# 铜陵市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://60.173.22.63:7075/opac/`（图创 Interlib，页标题「检索系统」，meta keywords 自报
「opac, 图创, interlib, 图书检索, 借书, , 铜陵市图书馆」）。抓取只读 GET。
注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。

## 检索

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认（非 pro2018）模板结果页（`bookmeta` 容器）。实抓「三体」61 条、共 4 页。

- **默认模板变体（本批首见）**：该站著者/出版社锚点**不带 `author-link`/`publisher-link`
  class**，只在前置文本里留「著者:」「出版社:」。家族 `_SearchParser` 已加「同层前置文本标签
  兜底」（值取紧随的无 class 锚点，标签所在 div 闭合即失效），广州等带 class 的城市仍优先按
  class 命中、不受影响；pin 在 `tests/test_interlib_search_parser.py::test_text_label_fallback_without_link_classes`。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓首条
  《三体》（334623）、ISBN `9787229151003`、索书号 `I247.5`。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 4 条，
  含「铜陵市图书馆」「中心馆」。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 61 条、共 4 页 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/334623`（三体） |
| `holding.json` | `GET /api/holding/334623`（4 条） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
