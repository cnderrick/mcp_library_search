# 毕节市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://220.172.207.114:8001/opac/`（图创 Interlib，页标题「检索系统」，
meta keywords 自报「opac, 图创, interlib, 图书检索, 借书, …, 毕节图书馆」）。
抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。裸 IP ＋
HTTP 明文，无验证码、无 pro2018。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认模板结果页（`bookmeta` 容器）。实抓「三体」31 条、共 2 页；生造关键词 0 条。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓首条
  《三体．Ⅱ，黑暗森林》（recno 900137858）ISBN `978-7-5366-9396-8`、
  索书号 `I247.55`、出版年 2008。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 3 条，
  均在馆，馆名「毕节图书馆」，位置含「百里杜鹃图书馆」「金海湖锦绣金海分馆」
  （联合目录/分馆口径），索书号 `I247.55/771(2)/:2`。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 31 条 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/900137858`（三体．Ⅱ，黑暗森林） |
| `holding.json` | `GET /api/holding/900137858`（3 条，均在馆） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- 馆名译名「毕节图书馆」（无「市」字），原值照登。
- `availability_summary` 在 HTML 通道下为空串。
