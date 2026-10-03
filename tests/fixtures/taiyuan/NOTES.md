# 太原市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://opac.tylib.org.cn/opac/index`（图创 Interlib，页标题「检索系统」）。
抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`、`solr_search=True`。

## 检索：HTML 页被验证码拦，改走内嵌 Solr

`/opac/search` 恒返「opac验证」滑动验证码页（目录 `slideVerify`，非限速型），
而站点内嵌的 Solr 后端 `GET /opac/api/search` 开放（与青岛及一批带验证码的
Interlib 站点同通道）。实抓「三体」共 179 条。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓首条《三体》
  （2002435398），ISBN `978-7-5366-9293-0`。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_solr.json` | Solr `GET /opac/api/search`（「三体」，179 条） |
| `search_solr_empty.json` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/{recno}`（三体，2002435398） |
| `holding.json` | `GET /api/holding/{recno}` |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 空串（Solr 通道无逐书目可借概况，同青岛）。
