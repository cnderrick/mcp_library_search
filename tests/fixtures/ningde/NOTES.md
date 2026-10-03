# 宁德市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://220.161.205.210:82/opac/index`（图创 Interlib，页标题「检索系统」，
meta keywords 自报「opac, 图创, interlib, 图书检索, 借书, , 宁德市图书馆」）。抓取只读 GET。
注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认（非 pro2018）模板结果页（`bookmeta` 容器）。实抓「三体」23 条、共 3 页。

- **分页锚点 quirk（家族通用）**：只要命中数 > 0，页内「下一页」锚点恒渲染（末页
  也 `has_next=True`），调用方应以 `total_pages` 为准；0 结果页无该锚点、`has_next=False`。
- **首条为简编记录**：检索首条 recno 63099《三体》（著者「刘慈欣」）是馆方简编记录
  ——`/api/book/63099` 返回的 `biblios` 字段大量为 null（无 ISBN／出版社／出版年／
  索书号），馆藏 JSON 的 `holdingList` 为空。属记录级数据事实，原值照登。

## 详情与馆藏

首条简编记录无馆藏，故详情/馆藏 fixture 另取同页 recno 58950《三体：典藏版》
（ISBN `978-7-229-10060-5`、索书号 `I247.55`、出版年 2016），以覆盖馆藏解析路径。

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓 58950
  ISBN `978-7-229-10060-5`、索书号 `I247.55`、出版年 2016。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 6 条，
  全部不可借（3 借出 + 2 丢失 + 1 借出，馆名「宁德市图书馆」三楼藏书区）。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 23 条、共 3 页 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/58950`（三体：典藏版） |
| `holding.json` | `GET /api/holding/58950`（6 条，全部不可借） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，「借出」「丢失」等词表外/不可借词保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
- 首条简编记录字段残缺且无馆藏属记录级数据事实（非接口故障）；详情/馆藏 fixture
  因此取同页 recno 58950。
