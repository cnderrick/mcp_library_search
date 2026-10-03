# 六盘水市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://111.85.91.253:8088/opac/index`（图创 Interlib，页标题「检索系统」，
meta keywords 自报「opac, 图创, interlib, 图书检索, 借书, …, 六盘水市图书馆」）。
抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。裸 IP ＋
HTTP 明文，无验证码、无 pro2018。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认模板结果页（`bookmeta` 容器）。实抓「三体」11 条、共 1 页；生造关键词 0 条。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓首条
  《《三体》中的物理学》（recno 900084227）ISBN `978-7-5710-0148-3`、索书号 `O4-49`、
  出版年 2019。相关度首条为评论/衍生书，原值照登。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 2 条
  （1 在馆 ＋ 1 借出），馆名「六盘水市图书馆」、位置「中文书库」、索书号 `O4-49/863`。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 11 条 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/900084227`（《三体》中的物理学） |
| `holding.json` | `GET /api/holding/900084227`（2 条） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
