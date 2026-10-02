# 丽江市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`https://www.ljstsg.cn/opac/index`（页标题「检索系统」，`<meta name="keywords">`
自报「opac, 图创, interlib, 图书检索, 借书, , 丽江市图书馆」）。图创 Interlib
**默认（非 pro2018）模板**。摸查与登记见 docs/data-sources/cn.md 总览表丽江行。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`
（详情走 `/api/book/{recno}` JSON）。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认模板结果页（`bookmeta` 容器）。实抓「三体」80 条、共 8 页。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓《三体：典藏版》
  ISBN `978-7-229-10060-5`，中图分类号 `I247.55`。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓
  首条（257370）1 册在馆（古城区图书馆·古城区外借室）。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 80 条 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/257370` |
| `holding.json` | `GET /api/holding/257370`（1 条单册） |

## 数据边界

- 全市联合目录：libcodeMap 含丽江图书馆（`LJ`）、古城区图书馆（`GCQTSG`）、
  玉龙县图书馆（`YLXTSG`）、宁蒗县图书馆（`NLXTSG`）、华坪县图书馆（`HPXTSG`）
  及各乡镇分馆、街道分馆、职工书屋等（约 60 项），馆名译名原值照登。
- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
