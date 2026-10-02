# 金华 UILAS 实抓侦察记录

实抓时间：2026-10-02，来源 `http://202.101.180.43/ILASOPAC/Index?target=0`
（UILAS 知识检索平台，ILAS 家族 HTML OPAC，Tomcat/JSP）。裸 IP，**仅 HTTP**——
443 端口开放但证书已过期，别走 https。全程匿名零 cookie 实测可通（检索/翻页/详情
均 200），无验证码、无登录墙；共 9 个实抓请求（间隔 ≥4.5 秒）未触发任何限频。
解析器以本文件为准；与先期调研笔记（docs/team/research/2026-10-02-ilas-jinhua.md）
的出入在文末专列。

## fixture 清单

| 文件 | 内容 |
|---|---|
| search.html | POST 检索「三体」（searchType=text）首页：20 条，`共有 [665]条记录`，`页码: 1/34` |
| search_p2.html | 翻页 GET `nCurrentpage=2`（SearchKey 双重编码原样）：`页码: 2/34`，与首页 recno 无重叠 |
| search_isbn.html | `searchType=isbnsrh`，978-7-5728-2658-0 → `共有 [1]条记录`，recno 126657271 |
| search_empty.html | 空结果页：`共有 []条记录`（**括号空**）、`页码: 1/`（无总页数）、无条目 |
| detail.html | 《石经考》recno 125479764：单馆藏「入藏」、民国出版日期、ISBN「书号不详」、有附注提要 |
| detail_loan.html | 《三体：图像小说》recno 126174120：**两张馆藏表**（入藏＋借出各 1 册） |

## 检索 NTRdrBookRetr.do（POST 首页 / GET 翻页）

- POST 表单字段（Index 页表单实测核对）：`searchType`（name 书名/刊名【表单默认】、
  seriesbook、author、classno、**isbnsrh** ISBN/ISSN、callno、subject、publish、
  pubyear、**text** 任意词）＋`searchKey`＋`searchWay`（searchWayPrv 前方一致【默认】/
  searchWayLike 模糊）＋`pageNum`（10/20/50，默认 10）＋`matchType`（name/pubyear
  【默认】/publish/source）＋`matchSort`（desc【默认】/asc）＋可选 libid/libidName。
- 适配器口径：ISBN 形态关键词 → `searchType=isbnsrh`；其余一律 `searchType=text`
  （任意词，覆盖书名/作者等混合关键词）。其余参数取表单默认：searchWayPrv、
  pubyear、desc；`pageNum=limit` 原样透传。
- 总数锚点：`共有\s*\[(\d*)\]条记录`（「共有」与「[665]」之间实测有换行制表符，
  `\s*` 必须）。**空结果页括号里是空的**（`共有 []条记录`）→ 捕获组空 = total 0。
- 页码锚点：`页码:\s*(\d+)/(\d*)`；空结果页 `页码: 1/` 无总页数 → total_pages=1。
- 锚点整体缺失 = 不是结果页（如被打回 Index 首页），应当报错而不是当空结果。
- 结果页上下各渲染一次分页条与统计区（同款锚点出现两遍），正则取首个匹配即可。

## 翻页（重要 quirk：SearchKey 双重 URL 编码）

GET `NTRdrBookRetr.do?nCurrentpage=N&SearchType=…&SearchKey=…&PageNum=…&searchWay=…&matchType=…&matchSort=…`。
服务器生成的翻页链接里 **SearchKey 是双重 URL 编码**：`三体` →
`%25E4%25B8%2589%25E4%25BD%2593`（即把 `%E4%B8%89%E4%BD%93` 再整体编码一次）。
适配器照原样复刻：先 `quote(keyword, safe="")` 再交给 urlencode 二次编码。
实抓验证：nCurrentpage=2 返回 `页码: 2/34`，条目与首页无重叠。
参数名大小写以页内翻页链接原样为准（SearchType/SearchKey/PageNum 大写、
searchWay/matchType/matchSort 小写）。

## book_id 与条目结构

- `book_id` = 裸 recno（纯数字，如 `125479764`），取自条目内
  `<input name="bookItemCheckbox" value="…">`（name 与 value 之间有换行，`\s+` 匹配），
  兜底取详情链接 onclick 的 `recno=` 参数。**无 tablename 前缀**（与深圳/重庆
  `{table}:{id}` 形态不同）；非纯数字的 book_id 直接报错。
- 条目以 `<h3 class="title">` 分块：块内含 checkbox＋标题链接
  `<a onclick="toLocation('/ILASOPAC/NTRdrBookRetrInfo.do;jsessionid=…?recno=…')">`；
  onclick 里嵌 jsessionid，剥掉即可——匿名直连详情页实测 200，无需会话。
- 字段在紧随的 `div.info` 内，形如 `作者：<span>…</span>`、`出版社：<span>…</span>`、
  `出版时间：<span>…</span>`、`ISBN/ISSN：<span>…</span>`、`丛书名`、`分类号`、
  `页数`、`价格`。解析按 h3 分块后块内取首个匹配，不会串条（每页 20 条实测
  20 块、无重复渲染；页面 JS 里也有 `bookItemCheckbox` 字样——杭州同款陷阱，
  必须锚定真实 h3.title 块，不能数裸字符串）。
- 列表页**没有任何单册状态词**（入藏/借出/可借/在馆/复本 全为 0）→
  `availability_summary=""`。
- 出版时间可能是民国纪年（「民国二十」）→ publish_year 按仓库口径提取公历
  `(?:19|20)\d{2}`（同重庆/Interlib），提不到则空串，不做朝代换算猜测。

## 详情 NTRdrBookRetrInfo.do?recno=<recno>&libid=

- 匿名 GET，无需会话。页面标记 `<title>书目详细信息</title>`（检索页无此标记，
  可用于走错页判定）。
- 标题：`h3.title` 第一个 `<a>` 文本（形态 `标题</a>/<a>作者`，只取第一段）。
  **详情页标题可能短于列表页**（《石经考》vs《石经考．汉石经残字考．魏三体石经遗字考》），
  两处均原值照登，不做对齐。
- 书目字段在 `<ul style="width: 50%">` 的 `<li>`：`作者：<a>…</a>`、`出版社：<a>…</a>`、
  `出版日期：…`（纯文本无链接，如「民国二十五年十二月[1936.12]」→ 提取 1936）、
  `ISBN/ISSN：<a>…</a>`（**查无 ISBN 时原值是「书号不详」，照登**）、
  `分类号：<a>…</a>`（= call_number）、另有 主题词/丛书/页码/价格/出版地/尺寸
  （契约模型不收，不解析）。各锚点全页仅出现一次（两份详情 fixture 实测）。
- **附注提要**：`<div class="infotip"><strong>附注提要</strong><div class="text">…`
  内联块，两份 fixture 均有实值（「石经考一卷,据借月仙房汇钞本影印…」/
  「Three-body problem」）→ summary 取它原值（上海「附注」回退同款思路）；
  无此块则 summary=""。站方 getBookCatalog.do AJAX 实测恒空（调研结论），不接。
- 页面 380–612KB（内联全部馆藏＋借阅统计脚本；调研记录最大 870KB），
  解析按锚点切片，返回结构只装字段文本，不把整页塞进去。

## 馆藏（详情页内联，div#BookHolding）

- 容器 `<div id="BookHolding">`。**CADAL 数字图书的两个 `table.table` 在
  BookHolding 之前**（showCadal div 内、tbody 空）——从 `id="BookHolding"` 起
  切片即天然排除；千万别全页数 `table.table`（调研笔记「两个 table.table＝
  可外借/不可外借」实际数到的是 CADAL 表，见文末出入清单）。
- 只有入藏复本的书：**单表**，`title_1` 标签显示「馆藏信息」（「可外借馆藏」
  字样留在 HTML 注释里）；有借出复本的书：**两表**——「馆藏信息」（入藏行）
  ＋「已外借馆藏」（借出行）。解析器遍历 BookHolding 下全部 `table.table` 合并行，
  不依赖表标题。
- 多成员馆时 infotitle 有 `<li title="磐安县图书馆(1)">` 分馆 tab；行级
  「当前所在馆」已是中文馆名（金华市图书馆/磐安县图书馆），无需码表，
  getAllLibraries.do 不接。
- 表头 10 列：条码号/索书号/当前所在馆/当前所在地点/馆藏状态/流通类别/
  预借/卷册说明/架位号/定位。**第 7 列 th 文案两表不一（入藏表「预借」、
  借出表「预约」）**——按 th 标签建列位映射取数，不硬编码列号；
  「预借(点击)」「定位」是动作列不入数据。
- td 单元格有大量 JSP 模板空白与条件分支残留（「当前所在馆」格实测裹着几十行
  空白才到馆名），去标签后必须压缩空白再取文本。
- 字段映射：library=当前所在馆、location=当前所在地点（分支/地点名，如
  江南街道悦读吧/市馆外借部/民国古书）、call_number=索书号、status=馆藏状态原值。
- **状态词表仅「入藏」（→ available=True）与「借出」（→ False）**；词表外
  一律保守不可借（用户定调口径）。
- **无应还日期**：表头无「应还」列，全文 returnDate/loanDate 均 0（两 fixture
  复核）→ 借出单册 `due_date=""` 恒空。数据边界，非故障，不猜。
- 备用 GetholdingShow.do 不接（调研实测偶发超时且依赖会话；内联解析单请求够用）。
- 行级去重防御：library/call_number/status 全空的行跳过（模板空行防御，
  实抓未见空行）。

## 节流与风险

- 节流 **4 秒/host**（天津 ILAS 家族经验安全线；调研实测 1 秒×5 连发未触发，
  但不试探下限）。
- 裸 IP 无域名，IP 变更即失效；前端 2016–2018 年代码，结构稳定但需警惕改版。
- jsessionid 会出现在页面生成的链接里，但**匿名访问不依赖它**（全程零 cookie 实测）。

## 真网验证（2026-10-02，适配器实调，7 项全过）

- `search_books("三体")`：total_results=665、20 条/页、页码 1/34、has_next=True。
- `search_books("三体", page=2)`：双重编码 GET 翻页生效，与第 1 页 recno 重叠 0。
- `search_books("978-7-5728-2658-0")`：isbnsrh 路由命中 1 条（recno 126657271
  《我的三体漫画．第一辑．2》）。
- `get_book_detail("126174120")`：《三体：图像小说》，isbn 978-7-5753-0280-7、
  call_number I247.5、summary "Three-body problem"（附注提要原值）。
- `get_holdings("126174120", only_available=False)`：2 册（入藏·江南街道悦读吧／
  借出·市馆外借部），due_date 均空；`only_available=True` 过滤剩 1 册入藏。
- `search_books("zzz不存在关键词qqq9527")`：total_results=0、books=[]、
  total_pages=1、has_next=False。
- 冒烟中详情页出现过 1 次 30 秒偶发超时（同款 URL 数秒后即成功，非拦截、
  无 401/验证码）——大详情页（600KB＋）的瞬时网络现象，调用方重试即可；
  全程未见任何限频拦截。

## 与调研笔记（2026-10-02-ilas-jinhua.md）的出入

1. **馆藏表结构**：调研称「两个 table.table：表 1 可外借馆藏（入藏）、表 2
   不可外借馆藏（借出）」。实抓：全页那两个 `table.table` 是 BookHolding **之前**
   的 CADAL 数字图书表（空 tbody）；真实馆藏表在 `div#BookHolding` 内，标签是
   「馆藏信息」/「已外借馆藏」，且**只有入藏复本时仅一张表**。解析必须以
   BookHolding 锚点切片。
2. **简介**：调研称「简介恒空（getBookCatalog.do 未启用）」。实抓：详情页有
   内联「附注提要」块且两份 fixture 均有实值 → summary 取附注提要原值；
   getBookCatalog.do 恒空的结论不变（不接该端点）。
3. **空结果页形态**（调研未记录）：`共有 []条记录` 括号空、`页码: 1/` 无总页数。
4. **翻页 SearchKey 双重 URL 编码**（调研只记了参数大小写，未记双重编码）。
5. 其余（三原语端点、匿名可达、总数/页码锚点、ISBN 路由、无应还日期、
   状态词表、裸 recno book_id）与调研一致，实测复核通过。
