# 德清县图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://opac.dqlib.com.cn/opac/index`（图创 Interlib）。抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`、`solr_search=True`。

## 检索

检索页不可用，改走站点内嵌 Solr `GET /opac/api/search`（`q`/`rows`/`page`/`wt=json`），
家族 `parser.parse_solr` 零改动；实抓「三体」共 55 条、3 页。

- **Solr 字段可为 null**：实抓含 `isbn_meta`/`pubdate_meta` 为 `null` 的文档，
  家族 `parse_solr` 已统一按空串处理（此前只对非空文档生效，本批暴露并修复）。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓首条
  《三体》（61754），实抓馆藏 11 条（德清图书馆、新市分馆等）。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_solr.json` | Solr `GET /opac/api/search`（「三体」） |
| `search_solr_empty.json` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/{recno}`（三体，61754） |
| `holding.json` | `GET /api/holding/{recno}`（11 条） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
- HTML 检索页被「opac验证」拦，改走内嵌 Solr；实抓含 `isbn_meta`/`pubdate_meta` 为 null 的文档（家族 parser 已按空串处理）。
