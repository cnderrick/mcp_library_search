# 宝鸡市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://1.82.133.119:8082/opac/`（宝鸡市公共图书馆集群信息化管理平台，
meta keywords 自报「opac, 图创, interlib」）。图创 Interlib **默认（非 pro2018）**
模板。裸 IP ＋ HTTP。

## fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `search_p1.html` | `GET /opac/search?q=三体&…&rows=10&page=1` | 默认模板搜索第 1 页（110 条、共 11 页，`bookmeta` 容器） |
| `search_empty.html` | 生造关键词 | 0 条 |
| `detail_api.json` | `GET /opac/api/book/900858229` | 书目 JSON |
| `holding.json` | `GET /opac/api/holding/900858229?limitLibcodes=&isCluster=` | 馆藏 JSON，2 册（1 在馆 1 借出） |

## 与广州基准的差异（均以家族配置字段表达）

1. 详情走 `/api/book/{recno}` JSON（`api_detail=True`）。
2. 不需要 `curlibcode`；搜索/馆藏与广州基准同构，家族 parser 零改动。
3. 网点含「宝图-工人文化宫分馆」等（馆藏译名照登）。
