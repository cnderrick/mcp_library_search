# 重庆 InDigLib 实抓侦察记录

实抓时间：2026-10-02，来源 `http://222.177.237.197:8080/InDigLib`（用户确认为重庆馆实际使用的系统）。
注意：根路径 `/InDigLib/` 打开是登录页（6455 字节，与 get_asset_anonymous.html 同一张），
使用者入口是 `frontV2/SearchIndex!simple.action?opacType=local`（「opac查询页」）。

## 会话流程

1. `GET frontV2/SearchIndex!simple.action?opacType=local` 建立 JSESSIONID（session.html）。
2. `POST OpacMarcSearchSolr!simpleSearch.action`，字段 `select1` + `text1`。
3. 详情 `GET frontV2/BookDetail.action?metaid={N}&metatable=i_biblios`。

首页表单的 action（`OpacMarcSearchSolr!opacSearch.action`）是假入口，search.js 会改写到上面的
simpleSearch（实抓验证：opacSearch 不接受这些参数）。

## select1 取值

`all` / `title` / `isbn` / `author` / `callno` / `subject` / `classno` / `publisher` /
`pubdate` / `lang`。`select1=isbn` 原生支持，实抓 9787508687193 → 《上瘾》命中
（search_isbn.html）。

## 分页

- POST 表单里的 `page` 字段**无效**（search_p2.html 与第 1 页逐字节相同）。
- 真实分页参数是 **GET `pageNo`**：结果页翻页链接形如
  `OpacMarcSearchSolr!simpleSearch.action?pageNo=2&select1=title&text1=...`。
- 实现翻页时把检索改为 GET（或带 querystring 的 POST），携带 `pageNo`。

## 详情页结构

- 书目字段直接渲染在 HTML（著者/出版社/出版年等，detail.html，metaid 2649440 = 《三体》）。
- `showAsset=true` 参数是**无效参数**：detail_asset.html 与 detail.html 逐字节相同。
- 「馆藏信息」tab：只有分馆名列表（本例仅「重庆图书馆」，li 的 `metas="i_biblios-2649440"`），
  内容区 `<div class="sub_con">` 为空、由 JS 懒加载。

## 单册状态：根路径 GetAsset.action 匿名可通（关键结论，2026-10-02 修正）

- 懒加载端点 `POST GetAsset.action`（参数 `metatables` + `metaids` + `type=map`
  + `orderType=`），返回 JSON `{list:[…], map:{分馆:[…]}}`，单册字段 barcode/
  callno/curlocal(local)/cursublib(sublib)/status/cirtype/loandate/retudate/readerno。
- **两个门，命运不同**：
  - 根路径 `InDigLib/GetAsset.action`：**匿名可通，无需会话**。双重实证——用户
    游客模式浏览器 200 JSON；脚本零 cookie 裸 POST → HTTP 200、9664 字节 JSON
    （get_asset.json，《上瘾》metaid=2925752，5 册）。响应自带 JSESSIONID
    Set-Cookie，但非前提。
  - `frontV2/GetAsset.action`：**登录拦截**。2026-10-02 三次实测（含完整复刻
    浏览器链路：SearchIndex → BookDetail → frontCloud 登录 iframe → GetAsset，
    带 Referer），全部 302 到登录页（get_asset_anonymous.html，6455 字节）。
- 初版「需读者登录，匿名拿不到」的结论只测了 frontV2 那道门，是错的。教训：
  被 302 拦截时先试根路径同名 action。
- 详情页内另一 ajax `GetCurrentBorrow.action` 是读者登录后功能（判断是否借阅该书
  以下载随书光盘），不是公开馆藏接口。
- 检索结果页没有任何单册状态词（search.html 全文无 在架/可借/借出/复本）。

**可借口径统一保守**（用户定调：只干确定事儿，不确定的统一处理）：源站无明确
「可借/在架」状态词。确定的只有借出（status 含「借出」，带 loandate/retudate）
→ `available=False` + `due_date=retudate`；其余一切状态（入藏、保存本 cirtype、
未见过的值）统一 `available=False`，status 原值照登，**不做「入藏＝在架」预设**。

## 适配器设计约束（由此推导）

- `search` / `get_book_detail`：按公开 HTML 正常解析。
- `get_holdings`：先根路径 GetAsset 单册级（library=cursublib、location=curlocal、
  call_number=callno、status 原值、全部 available=False、借出带 due_date）；
  GetAsset 不可用（请求失败/响应非 JSON，如哪天换回登录页）→ 回退详情页
  馆名级（library=馆名，其余字段空，status=""、available=False）。
  item_id 恒空串（barcode 不当 item_id 用，避免触发契约的归还日期查询分支，
  due_date 直接由 retudate 填）。`only_available=True` 时重庆恒返回空列表——
  这是源站数据边界，不是故障。
- 不对 frontV2 GetAsset 做读者登录（无凭据、且属个人数据边界）。

## 真网验证（2026-10-02，适配器实调，6 项全过）

- `search_books("三体")`：20 条/页，total_pages=1630，has_next=True。
- `search_books("9787508687193")`：ISBN 路由生效，命中《上瘾 · 1 · 选择一座城市，
  选择一种人生》（i_biblios:2313420）。
- `search_books("三体", page=2)`：GET pageNo=2 翻页生效，与第 1 页无重复；
  实测第 2 页返回 10 条（少于 pageSize，源站行为，原值记录）。
- `search_books("三体", limit=5)`：pageSize 被源站接受，返回 5 条。
- `get_book_detail("i_biblios:2649440")`：《三体》字段与浏览器一致（isbn
  9787229166922，call_number 空，summary 空）。
- `get_holdings("i_biblios:2925752", only_available=False)`（GetAsset 接入后）：
  5 册单册数据，索书号 TS976.15/585，地点含 重庆馆通借库/重图基藏库(四楼)/
  重图在线借阅，1 册「普通借出」due_date 2026-08-17，全部 available=False；
  全程仅 1 个请求（无需先建会话）。

## 其它

- 详情页**无索书号字段**（检索条目里有，如 I247.59/2376，详情页不显示），
  `get_book_detail` 的 call_number 恒为空串。
- POST 检索是否接受 `pageSize` 参数未实测（实抓只带 select1/text1，默认每页 20 条）；
  Task 5 真网验证点：limit≠20 时条目数是否随之变化，被忽略则退回 20。
- 翻页 GET 整串参数（pageNo/select1/text1/pageSize/lastSearchValue 等）取自结果页
  分页链接原样，pageNo=2 的 GET 实抓未成功（当时按错误参数 page 抓的），Task 5 一并验证。

- 未发现验证码机制（当天十余次请求未触发），限速仍按 spec 保守 3 秒。
- `front/opac/Search!search.action`（云检索，opacType=cloud 分支）实测 200 但结果页
  无状态字段，不值得切换。
- `222.177.237.215:8080/bookcd`（页面 JS 变量里的资产主机）直接访问断开连接。
