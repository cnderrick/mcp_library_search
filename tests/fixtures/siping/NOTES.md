# 四平市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://111.26.111.223:8081/opac/index`（图创 Interlib，页标题「检索系统」，meta keywords 自报
「opac, 图创, interlib, 图书检索, 借书, …, 四平市图书馆」）。抓取只读 GET。注册登记见
docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认（非 pro2018）模板结果页（`div.bookmeta` 容器）。实抓「三体」19 条、
共 1 页；首条《三体世界观．科幻概念》（三体宇宙，2022）。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓《三体世界观．科幻概念》
  ISBN `978-7-5340-9471-2`、中图分类法 `I207.42`、内容提要长度 106。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 2 条、
  2 条在馆；馆名：四平市图书馆。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 19 条、共 1 页 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/{recno}`（三体世界观．科幻概念） |
| `holding.json` | `GET /api/holding/{recno}`（2 条） |

## 数据边界

- 相关度首条为《三体世界观．科幻概念》（三体宇宙编，衍生设定集），原值照登。
- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
- 内容提要缺失时 `summary` 空串，属记录级数据事实。
