# 安康市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://219.145.206.134:8082/opac/index`。图创 Interlib **pro2018 模板代**
（搜索条目 `libBookLi`、静态资源 `/opac/media/pro2018/…`）。裸 IP ＋ HTTP。

## fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `search_p1.html` | `GET /opac/search?q=三体&…&rows=10&page=1` | pro2018 搜索第 1 页（161 条、共 17 页） |
| `search_empty.html` | 生造关键词 | 0 条 |
| `detail_api.json` | `GET /opac/api/book/1983176` | 书目 JSON |
| `holding.json` | `GET /opac/api/holding/1983176?limitLibcodes=&isCluster=` | 馆藏 JSON，1 册借出（带应还日期） |

## 与广州基准的差异（均以家族配置字段表达）

1. **pro2018 模板**（`pro2018=True`）。
2. **详情页 HTML 被源站截断**（2026-10-03 实测：`GET /opac/book/{recno}` 稳定停在
   ~67597 字节、HTTP/1.0 与 chunked、curl/Python 均 `IncompleteRead`，且截断点前的
   内容不含 `bookInfoTable`/`bkTxtTit` 书目表）——**故详情改走 `/api/book/{recno}`
   JSON**（`api_detail=True`），该接口正常返回完整书目。
3. 馆藏 `/api/holding/{recno}` 正常（含译名映射），家族 parser 零改动；实抓含
   「汉滨区图书馆」借出册带应还日期 `2026-10-07`。
4. 不需要 `curlibcode`。
