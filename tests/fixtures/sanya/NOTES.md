# 三亚市图书馆 OPAC 结构侦察（2026-10-03 实抓）

入口：`https://opac.sanyalib.com:8888/opac/SY`（Vue SPA 壳，页标题「图书馆」）。
抓取只读 GET/POST。注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk：实为图创 tcc-opac，非 Interlib

本批按 Interlib 默认模板试探，实抓发现三亚 OPAC 是图创 **tcc-opac** 产品线
（与宁波/济南/鄂尔多斯同款，与穗杭的图创 Interlib 不同产品线）：SPA 壳在
`/opac/SY`（`opac-remould`，静态资源 `/opac/static/js/app.*.js`），真实后端在
`/api/tcc-opac/SY/*`，纯 JSON ＋ JWT 访客令牌（`ACCESS-TOKEN` 头）。故复用已上收的
`tccopac/` 家族，不在 `interlib/` 内新增 quirk。

- **库段（segment）**：前端 JS 常量 `var r=["SY","YCSTQG"], c="SY"`，默认 `SY`；
  API 前缀即 `{host}/api/tcc-opac/SY`。
- **本城配置**：`base_url="https://opac.sanyalib.com:8888/api/tcc-opac/SY"`、
  `referer="https://opac.sanyalib.com:8888/opac/SY"`，无新增 quirk 字段。

## 检索、详情、馆藏：tcc-opac 协议

- **令牌**：`POST /system/user/getOpenApiAccessToken`（匿名 `{}` 即发，
  `data.token`，`expiresIn` 秒级字符串）。
- **检索**：`POST /search/`（尾斜杠），body
  `{current,size,searchWay:"marc",sortWay:"score",sortOrder:"desc",hasholding:1,q}`。
  实抓「三体」`numFound="49"`；生造关键词 `numFound="0"`。
- **详情**：`POST /service/biblios/getbyid?id=&fields=300a,314a,327a,330a`（参数走查询串、
  空 body）。实抓首条《三体漫画．起源》（id 1983722455542755330）
  ISBN `978-7-5339-7402-2`、出版年 2024；`call_number` 为空串（`biblios.shelfno` 为
  null，`classno` 分类号不冒充索书号）。
- **馆藏**：`POST /service/hold/pagelist {current:1,size:500,bibliosId}`，单册级；
  实抓 8 条，馆名「三亚市图书馆」、位置「社会科学库」、索书号 `J228.2/2037:1`，
  状态「在馆」可借、「借出」不可借。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | SPA 壳指纹（`/opac/SY`，标题「图书馆」、`opac-remould`） |
| `token.json` | `POST /system/user/getOpenApiAccessToken` 响应 |
| `search_santi.json` | `POST /search/` q=三体，numFound=49 |
| `search_empty.json` | 生造关键词，numFound=0 |
| `detail.json` | `POST /service/biblios/getbyid`（三体漫画．起源） |
| `holdings.json` | `POST /service/hold/pagelist`（8 条） |

## 数据边界与风控

- 可借判定沿用 tcc-opac 家族口径：`statename=="在馆"` 才可借，词表外保守不可借。
- `availability_summary` 恒空串（源站检索条目不提供逐书目可借概况）。
- 检索首条为漫画改编本《三体漫画．起源》，原值照登。
- 滑块风控码 `43001/-1/-402` 命中即抛错停手（家族 `parser.check_search`），不破解。
- **源站偶发读超时**：本批实抓中令牌、`getbyid` 均出现过 TLS/读握手超时（重试即通），
  检索正常。家族 timeout 30 秒止损，不重试业务请求；调用方遇到超时错误重试即可。
- 域名 `opac.sanyalib.com` 解析至 `198.20.2.212`，但返回真实 tcc-opac 服务（非停放页）。
