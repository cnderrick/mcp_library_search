# 普宁市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://www.pnlib.com:8088/opac/index`（图创 Interlib，页标题「检索系统」，meta keywords 自报
「opac, 图创, interlib, 图书检索, 借书, , 普宁图书馆」）。抓取只读 GET。
注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`、`solr_search=True`。

## 检索

检索页 `/opac/search` 被「opac验证」滑动验证码拦，改走站点内嵌 Solr
`GET /opac/api/search`（`q`/`rows`/`page`/`wt=json`），家族 `parser.parse_solr` 零改动。
实抓「三体」11 条、共 1 页。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓首条
  《三体》（200226）、ISBN `978-7-5366-9293-0`、索书号 `I247.5`。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 11 条，
  均为「普宁市图书馆」。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_solr.json` | Solr `GET /opac/api/search`（「三体」，11 条） |
| `search_solr_empty.json` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/200226`（三体） |
| `holding.json` | `GET /api/holding/200226`（11 条，含借出） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
- HTML 检索页被「opac验证」拦，改走内嵌 Solr。
