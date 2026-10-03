# 石家庄市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://120.211.62.194:8087/opac/index`（图创 Interlib，页标题「检索系统」，meta keywords 自报
「opac, 图创, interlib, 图书检索, 借书, …, 石家庄市图书馆」）。抓取只读 GET。注册登记见
docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认（非 pro2018）模板结果页（`div.bookmeta` 容器）。实抓「三体」154 条、
共 8 页；首条《三体》（刘慈欣著，2010）。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓《三体》
  ISBN `978-7-229-03093-3`、中图分类法 ``、内容提要长度 0。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 6 条、
  3 条在馆；馆名：正定图书馆、藁城图书馆、高新区图书馆。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 154 条、共 8 页 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/{recno}`（三体） |
| `holding.json` | `GET /api/holding/{recno}`（6 条） |

## 数据边界

- 详情 JSON 的 `classNo` 为空（该记录无中图分类号），`call_number` 留空串属记录级数据事实。
- 检索总量 154 条、8 页，为本批最大；馆藏分布在各县区馆（正定/藁城/高新区），属全市联合目录。
- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
- 内容提要缺失时 `summary` 空串，属记录级数据事实。
