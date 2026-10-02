# 黑龙江省图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://lib.hljlib.org.cn:2333/opac/index`（图创 Interlib，页标题「检索系统」）。抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`＋ `solr_search=True`。

## 检索：HTML 检索页被滑动验证码拦截，改走站点内嵌 Solr

搜索页 `/opac/search` 返回滑动验证码页（`slideVerify`，~3.3KB「opac验证」），
但站点内嵌 Solr 后端 `GET /opac/api/search` 开放且不经验证码（同青岛通道）：
参数 `q`/`rows`/`page`/`wt=json`，命中数 `response.numFound`，书目
`response.docs[]`（`title_meta`/`author_meta`/`publisher_meta`/`pubdate_meta`/
`isbn_meta`），稳定 id 为 `docs[].id`。`InterlibConfig.solr_search=True`。
实抓「三体」70 条。fixture：`search_solr.json` / `search_solr_empty.json`。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓《三体．上》ISBN `978-7-5002-7757-6`。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 1 条，1 条在馆。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_solr.json` | Solr 检索「三体」，numFound=70 |
| `search_solr_empty.json` | 生造关键词，numFound=0 |
| `detail_api.json` | `GET /api/book/{recno}`（三体．上） |
| `holding.json` | `GET /api/holding/{recno}`（1 条） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 Solr 通道下为空串。
