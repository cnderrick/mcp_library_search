# 咸阳市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://61.185.20.96:8082/opac/index`（咸阳市公共图书馆联盟，
meta keywords 自报「opac, 图创, interlib」）。图创 Interlib **默认（非 pro2018）**
模板。裸 IP ＋ HTTP。

## fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `search_p1.html` | `GET /opac/search?q=三体&…&rows=10&page=1` | 默认模板搜索第 1 页（79 条、共 8 页，`bookmeta` 容器） |
| `search_empty.html` | 生造关键词 | 0 条 |
| `detail_api.json` | `GET /opac/api/book/730219` | 书目 JSON |
| `holding.json` | `GET /opac/api/holding/730219?limitLibcodes=&isCluster=` | 馆藏 JSON，2 册在馆 |

## 与广州基准的差异（均以家族配置字段表达）

1. 详情走 `/api/book/{recno}` JSON（`api_detail=True`）。
2. 不需要 `curlibcode`；搜索/馆藏与广州基准同构，家族 parser 零改动。
3. 联盟含兴平图书馆等成员馆（馆藏译名照登）。
