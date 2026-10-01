# 广州图书馆 OPAC 页面结构侦察（2026-10-02 实抓）

站点：`https://opac.gzlib.org.cn`（图创 Interlib）。抓取命令见实施计划 Task 1，
全部只读 GET。TLS 偶发重置，重试即可。

## Fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `search_p1.html` | `GET /opac/search?q=活着&...&rows=10&page=1` | 搜索第 1 页，10 条结果 |
| `search_p2.html` | 同上 `page=2` | 搜索第 2 页，10 条结果 |
| `search_empty.html` | `GET /opac/search?q=azbycxq不存在xyz&...&page=1` | 生造关键词，0 条结果 |
| `detail.html` | `GET /opac/book/3004742677` | 《无论如何都要活著》详情页 |
| `holding.json` | `GET /opac/api/holding/3004742677?limitLibcodes=&isCluster=` | 馆藏 JSON（Ajax 接口，见下） |

## 搜索页结构

每条结果是一个 `<div class="bookmeta" bookrecno="{id}" booktype="...">` 容器，
内部分层如下（字段标签用全角冒号）：

- 标题：`<span class="bookmetaTitle"><a class="title-link" id="title_{id}">标题</a></span>`
- 作者：`<div>著者: <a class="author-link">作者</a></div>`（作者文本含 MARC 责任方式，
  如「朝井辽Ryo Asai著」）
- 出版社与出版年：`<div>出版社: <a class="publisher-link">出版社</a> 出版日期: 2021</div>`
- 文献类型：`<div>文献类型: ... 图书 ...</div>`（不解析）

`bookrecno` 即稳定书目 ID（`book_id = str(bookrecno)`）。同一结果里会出现多个
`bookDetail({id},...)` 锚点（标题链接、新窗口链接等），解析时以 `bookmeta` 容器为准，
不要数 `bookDetail(` 出现次数当条数。

- 总数：`检索到: 2,763 条结果`（带千分位逗号，可解析为 `total_results`）。
  空结果页是 `检索到: 0 条结果`。
- 分页：`<div class="meneame">` 内 `<span class="disabled">共 277 页</span>`，
  页码链接 `page=N`（当前页用 `<b>N</b>`），另有「首页 / 上一页 / 下一页 / 尾页」链接。
  `total_pages` 取「共 N 页」；`has_next` 取「下一页」链接是否存在。
- 空结果页：无 `bookmeta`、无 `meneame`，只有 `检索到: 0 条结果`。

## 详情页结构（`GET /opac/book/{bookrecno}`）

书目字段在 `<table id="bookInfoTable">`，每行 `<tr data-sort="N">`，两列
`<td class="leftTD">`（标签）+ `<td class="rightTD">`（值）：

| 标签（leftTD） | 字段 | 示例值 |
|---|---|---|
| `<h2>`（data-sort=0 行） | 标题 | 无论如何都要活著 |
| 主要责任者 | 作者（取第一个 `<a>` 文本） | 朝井辽 |
| ISBN | isbn（正则取 `[\d\-]{10,}`） | 978-986-507-471-5 |
| 出版发行 | 出版社（取 `<a>` 文本）+ 出版年（正则 `\d{4}`） | 采实文化事业股份有限公司 / 2021 |
| 内容提要 | 简介（summary，含 `<br/>`） | 收录六则短篇，…… |
| 中图分类法 | 索书号近似（取「版次」之前文本） | I313.45 |

说明：详情页**没有**独立「索书号」字段，只有「中图分类法」（`I313.45 版次： 5`）；
完整索书号（分类号+著者号，如 `I313.4/5376`）在馆藏接口的 `callno` 里。
`BookDetail.call_number` 现取「中图分类法」值。

## 馆藏：Ajax JSON 接口（不是静态 HTML）

详情页的「馆藏信息」tab 是 JS 异步加载，接口：

```
GET /opac/api/holding/{bookrecno}?limitLibcodes=&isCluster=
```

返回 JSON，顶层字段：`holdingList`（单册数组）、`libcodeMap`（馆码→馆名）、
`localMap`（位置码→位置名）、`holdStateMap`（状态码→`{stateType, stateName}`）、
`pBCtypeMap`、`barcodeLocationUrlMap`、`libcodeDeferDateMap`、`loanWorkMap`。

单条馆藏关键字段：

- `state`：数字状态码，经 `holdStateMap[state].stateName` 得到状态文本
- `callno`：索书号（如 `I313.4/5376`）
- `curlib`：所在馆码 → `libcodeMap[curlib]`（如 `GT`→广州图书馆）
- `curlocal`：所在馆位置码 → `localMap[curlocal]`（如 `CKWX01`→参考文献馆•港台书区）
- `shelfno`：架位号；`barcode`：条码号；`loan`：借出信息（可借时为 null）

状态码表（`holdStateMap`，29 项）：`2=在馆`、`3=借出`、`10=预借`、`13=闭架`、
`4=丢失`、`5=剔除`、`1=编目`、`0=流通还回上架中`…… 只有「在馆」判可借，其余保守不可借。

应还日期：本 fixture 只有一条「在馆」单册，无借出样例；借出单册的归还日期可能存于
`loan` 字段，字段名未验证（需真网冒烟确认）。当前 `parse_holdings` 对 `loan` 做
保守提取，取不到就留空串。

## 与 spec/计划的假设差异（实现期发现）

1. **馆藏是 Ajax JSON 而非详情页静态 HTML**——`get_holdings` 打的是
   `/opac/api/holding/{book_id}`，不是详情页。已新增 `holding.json` fixture。
2. **总数可解析**（`检索到: 2,763 条结果`），不是 spec 里「解析不到填 None」的情形；
   `total_results` 填真实值。
3. **详情页无独立简介区块，但有「内容提要」字段**——summary 取「内容提要」。
4. **契约测试（`tests/test_adapter_contract.py`，不可改）通过 monkeypatch 替换
   适配器模块级 `_client` 的 search/get_holdings/get_return_date/get_book_detail
   四个方法（上海 vendor 客户端形态）来校验输出模型**——因此广州适配器不能是
   对 interlib 三原语的纯薄包装，必须暴露同款 `_client`。详见广州适配器代码注释。
