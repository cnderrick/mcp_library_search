# 蚌埠市图书馆 tcc-opac 侦察（2026-10-03 实抓）

入口：`http://58.242.164.105:8090/999`（页标题「图书馆」）。技术组件 **图创
tcc-opac**（Java/Spring＋Vue2 SPA，纯 JSON＋JWT 访客令牌），与宁波/济南/
鄂尔多斯/三亚同款，非图创 Interlib 产品线。

## 系统判据

- 首页 HTML 为 `opac-remould` SPA 壳（`<noscript>` 文案含 `opac-remould`），
  静态资源 `/static/js/app.*.js`、`/static/js/chunk-vendors.*.js`。
- 前端 `app.e36de216.js` 出现 `/api/tcc-opac`、`/system/user/getOpenApiAccessToken`。
- 前端 `getBaseUrl`：`{origin}/api/tcc-opac/{location.href 第 4 段}`；入口 `/999`
  → API 根 `http://58.242.164.105:8090/api/tcc-opac/999`，Referer 取入口页
  `http://58.242.164.105:8090/999`。

## 协议

- 令牌 `POST /system/user/getOpenApiAccessToken`（匿名 `{}` 即发，JWT，`expiresIn`
  秒级字符串）→ 请求头 `ACCESS-TOKEN`。
- 检索 `POST /search/`（尾斜杠，`hasholding=1` 只看有馆藏）；详情
  `POST /service/biblios/getbyid`；馆藏 `POST /service/hold/pagelist`。均由
  `tccopac/` 家族统一实现。

## 实抓结果

- 检索「三体」：`numFound=32`（7 页），首条 `id=992392878256480305`《三体》
  （刘慈欣著，重庆出版社 2008）。
- 详情：ISBN `978-7-5366-9293-0`；`shelfno` 为 null → `call_number` 空串
  （分类号不冒充索书号）；内容简介齐全。
- 馆藏 12 册：馆名「蚌埠市图书馆」、位置「文化广场馆-借阅中心」；状态「在馆」
  （可借）／「借出」（不可借，带 `returnTime` 应还日期，实抓 2026-10-12 等）。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | SPA 壳（指纹「图书馆」＋`opac-remould`） |
| `token.json` | 匿名访客令牌响应 |
| `search_santi.json` | 检索「三体」，numFound=32 |
| `search_empty.json` | 生造关键词，numFound=0 |
| `detail.json` | `POST getbyid` id=992392878256480305 |
| `holdings.json` | `POST hold/pagelist` bibliosId=992392878256480305，12 册 |

## 数据边界

- 检索条目 `availability_summary` 恒空串（家族口径）。
- `biblios.shelfno` 为 null 时 `call_number` 空串，属源站数据事实，非故障。
- 家族内置 ≥4 秒节流；本城实抓未命中滑块风控（code 43001/-1/-402）。
