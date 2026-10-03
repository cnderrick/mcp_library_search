# 福州市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`https://opcs.fzlib.org:8082/opac/index`（图创 Interlib，页标题「检索系统」，
meta keywords 自报「opac, 图创, interlib, 图书检索, 借书, …, 福州地区图书馆联合检索平台」）。
抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。

> 可达性复核：旧批判「TLS 握手失败、域名解析至 198.20.2.5 停放段」已不成立。本批实测
> 域名现解析至 `198.20.2.211`，但返回真实馆方 OPAC（页标题「检索系统」、meta keywords
> 自报图创／interlib），非域名停放页；检索、详情、馆藏三通道全通。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认（非 pro2018）模板结果页（`bookmeta` 容器）。实抓「三体」138 条、共 7 页；
生造关键词 0 条。站点为「福州地区图书馆联合检索平台」联合目录口径。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓首条《三体》
  （recno 901104374）ISBN `978-7-5366-9293-0`、索书号 `I247.55`、出版年 2010。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 3 条，
  均在馆，馆名「马尾馆」、位置「中文书库」、索书号 `I247.55/115:3`。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 138 条 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/901104374`（三体） |
| `holding.json` | `GET /api/holding/901104374`（3 条，均在馆） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
- 实抓首条书目无内容提要，`summary` 为空串属记录级数据事实。
