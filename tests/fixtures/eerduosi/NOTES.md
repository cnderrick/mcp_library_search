# 鄂尔多斯市图书馆 tcc-opac 侦察（2026-10-03 实抓）

站点页面：`http`。技术组件 **图创 tcc-opac**（Java/Spring＋Vue2 SPA，纯 JSON＋JWT
访客令牌），与宁波市图书馆同款，协议与解析已上收 `tccopac/` 家族。API 根为
`{host}/api/tcc-opac/{first-path-segment}`（前端 `getBaseUrl()` 逆向，见
tests/fixtures/ningbo/NOTES.md）。

## 实测

- 令牌 `POST /system/user/getOpenApiAccessToken`（匿名 `{}` → `data.token`）。
- 检索 `POST /search/`（`hasholding=1` 只看有馆藏）：实抓「三体」`numFound=//1.183.72.92`，
  首条 `8089/ordoslib`《253》。
- 详情 `POST /service/biblios/getbyid?id=&fields=`；馆藏 `POST /service/hold/pagelist`：
  实抓 834992670938284143:三体：三体:1 册在馆。状态词表同宁波（在馆可借／借出，词表外保守不可借）。

| 文件 | 说明 |
|---|---|
| `token.json` | 访客令牌响应 |
| `search_santi.json` | 检索「三体」，numFound=//1.183.72.92 |
| `search_empty.json` | 生造关键词，numFound=0 |
| `detail.json` | `getbyid?id=8089/ordoslib` |
| `holdings.json` | `pagelist` 单册列表 |

## 数据边界

- 同宁波（检索条目无馆藏概况；聚合条目无本地书目；馆藏一页 500 册封顶）。
