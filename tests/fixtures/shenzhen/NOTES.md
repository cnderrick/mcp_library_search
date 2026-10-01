# 深圳 fixture 说明与字段侦察（2026-10-02）

本目录三个 JSON 文件均来自深圳图书馆自研 JSON API 的真实响应（开发期只读 GET，本次抓取均一次成功，未遇 TLS 重置）。抓取命令统一带浏览器 UA 与 `Referer: https://www.szlib.org.cn/opac/`。

## 抓取来源

- `search.json`：`GET /api/opacservice/getQueryResult`，参数 `v_value=活着、v_index=title、pageNum=20、v_page=1`。返回 `data.numFound=553`、`data.docs` 共 20 条。
- `search_empty.json`：同上，参数 `v_value=azbycxq不存在xyz`。返回 `data.numFound=0`、`data.docs=[]`。
- `detail.json`：`GET /api/opacservice/getBookDetail`，参数 `metaTable=bibliosm、metaId=1210013、library=all`（另带公共参数 `client_id=t1`）。对应 search 结果**第 2 条**（bibliosm:1210013，2008 年万卷版《活着活着就老了》）。

之所以 detail 不是 search 第 1 条：第 1 条（bibliosm:1083181，2010 年版）经查三桶均无借出（`BorrowedBook` 为空、`CanLoanBook` 3 组、`OnlyReadBook` 1 组），按计划换书重抓后取到本条第 2 条，其 `BorrowedBook` 含 1 条借出单册（`ReturnDate=20151222`）。

## 分页参数实测语义

| 参数 | 语义 | 实测 |
|---|---|---|
| `v_page` | 页码，1 起 | `v_page=1`（pageNum=1）返回第 1 条（recordid 6056898）；`v_page=3` 返回第 3 条（recordid 6056899） |
| `pageNum` | 每页条数 | `pageNum=1` 返回 1 条；`pageNum=2` 返回 2 条；`pageNum=20` 返回 20 条 |

即适配器映射应为：`limit → pageNum`、`page → v_page`。这与计划 Task 3 的猜测相反（计划猜 `pageNum=页码、v_page=每页条数`），实现已按实测调整。

## 响应结构与字段

### search（`getQueryResult`）

顶层有 `data` 包裹：`{data: {numFound, docs[]}}`。

- `numFound`：真实命中总数（int），`total_results` 直接用它。
- `docs[]`：每条是书目 dict，关键键：
  - `tablename`（str）、`recordid`（int）——`book_id = f"{tablename}:{recordid}"`；
  - `ptitle` / `title` / `u_title`——三者通常同值，`u_title` 可能带作者后缀（如 `活着活着就老了/冯唐著`）；取 `ptitle` 最干净，空则依次回退 `title`、`u_title`；
  - `author`（干净，如 `冯唐`）、`f_author`（list）；
  - `publisher`（干净出版社名，如 `万卷出版公司`）；
  - `publishyear`（纯 4 位年，如 `2008`）、`u_publish`（`城市:出版社,年份`，如 `沈阳:万卷出版公司,2008`）；
  - `isbn`（无连字符）、`u_isbn`（带连字符）、`callno`（可能多个索书号以空格分隔）；
  - 其它：`subject`、`classno`、`cover_path`、`library`、`local_children`、`serviceaddr`、`id`、`_version_`、`u_page`、`u_price`、`cirtype_l`。

### detail（`getBookDetail`）

顶层**没有** `data` 包裹，书目字段与三桶直接平铺（search 有 `data`、detail 没有，两接口不一致）。

书目字段：
- `title`（如 `活着活着就老了`）；
- `author`（**带“著”后缀**，如 `冯唐著`）；
- `publish` 与 `publishyear` **同值**，都是 `城市:出版社,年份` 全串（如 `沈阳:万卷出版公司,2008`），没有独立的纯出版社/纯年份字段；
- `isbn`（带连字符）、`callno`、`abstract`（内容简介，另有 `abstracts` 同值）、`subject`、`series`、`page`、`price`、`classno`。

### 三桶（CanLoanBook / OnlyReadBook / BorrowedBook）

三桶的**容器形态不一致**，实现必须各自归一化：

- `CanLoanBook`：`list[group]`（可多组，每组对应一个分馆/状态）；
- `OnlyReadBook`：`list[group]` 或 `null`；
- `BorrowedBook`：**单个 `group` dict**（不是 list）或 `null`；本 fixture 中为 `{notes, recordList, serviceaddr}`，`serviceaddr="borrowed"`。

`group` 结构（CanLoanBook/OnlyReadBook 组）：`{notes, recordList, serviceaddr, serviceaddrnotes}`；`recordList` 是 `list[单册]`。

单册关键键：
- `callno`（索书号）、`status`（`在馆` / `借出`）、`local`（馆内位置/调配点，如 `大学城中文图书`、`深图北馆密集架库（保障本区）`、`大学城自助借还书机`）；
- `location`（完整地址，仅可借/阅览单册有）、`library`（**分馆代码**，如 `044010`、`F44010`，不是馆名）、`serviceAddr`（代码）；
- `libraryNotes`（**馆名**，仅借出单册有，如 `深圳大学城图书馆（深圳市科技图书馆）`）；可借/阅览组的馆名在 group 级 `serviceaddrnotes`（如 `罗湖区图书馆`、`深圳图书馆（北馆）`，个别是状态文本如 `物流转运中（暂不外借）`）；
- `ReturnDate`（**仅借出单册有**，格式 `YYYYMMDD`，如 `20151222`，需归一化为 `YYYY-MM-DD`）。

## ISBN 索引（v_index=isbn）实测

- `v_index=isbn` 只在**完整参数集**下生效：`library=all`、`v_tablearray=bibliosm,serbibm,apabibibm,mmbibm,`、`sortfield=ptitle`、`sorttype=desc`、`cirtype=`、`v_secondquery=`、`v_startpubyear=`、`v_endpubyear=` 与分页参数 `v_page`、`pageNum` 同传。参数不全时 `v_index` 被静默忽略，返回全库命中（实测约 360 万条）。
- 带连字符的 ISBN（如 `978-7-5086-6831-4`）与去连字符形态（`9787508686314`）均可命中。
- 任意词索引（`v_index=all`）的字段集不含 ISBN，ISBN 形态关键词必须路由到 isbn 索引，代码层由 `_looks_like_isbn` 判断。
- 真网验证（2026-10-02）：`978-7-5086-6831-4` → `numFound=1`（《上瘾》埃亚尔等译，中信 2017，`bibliosm:3832412`），馆藏 71 条解析正常。

## 与 spec/计划假设不符之处（实现已按实测调整）

1. 分页：`v_page` 是页码、`pageNum` 是每页条数（计划猜反了）。
2. `BorrowedBook` 是单 group dict 而非 list；`OnlyReadBook` 可为 `null`。
3. detail 响应顶层无 `data` 包裹（search 有）。
4. 单册 `library` 是代码不是馆名；馆名在 group 级 `serviceaddrnotes` 或借出单册的 `libraryNotes`。
5. detail 的 `publishyear` 不是纯年份而是 `城市:出版社,年份` 全串，与 `publish` 同值；出版社与年份需从该串拆出。
6. `ReturnDate` 是 `YYYYMMDD` 而非 `YYYY-MM-DD`，需归一化；本 fixture 的值（2015）疑似陈旧，但为真实抓取数据，仅用于测试映射。
7. detail 书是 search 结果第 2 条（第 1 条无借出），非第 1 条。
