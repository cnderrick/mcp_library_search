# 中山市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`https://opac.zslib.cn/opac/index`（图创 Interlib，页标题「检索系统」，meta keywords 自报
「opac, 图创, interlib, 图书检索, 借书, , 中山市公共图书馆」）。抓取只读 GET。
注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **pro2018模板**。本城配置：`pro2018=True`、`api_detail=True`。

## 检索

`GET /opac/search` 直连可用，返回 **pro2018 模板**结果页（条目 `li.libBookLi`、
总数在 `schResNumIn`、分页走 JS 变量 `totalPage`/`currentPage`）。实抓「三体」142 条、共 8 页。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓首条
  《三体：图像小说》（902101273）、ISBN `978-7-5753-0280-7`、索书号 `J228.2`。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 4 条，
  含「中山纪念图书馆」「南区图书馆」「学校图书馆」「神湾图书馆」。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | pro2018 检索「三体」，检索到 142 条、共 8 页 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/902101273`（三体：图像小说） |
| `holding.json` | `GET /api/holding/902101273`（4 条，含借出） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
- 首条《三体：图像小说》为图像小说（索书号 `J228.2`），非原著；原值照登。
