# 天津三源实抓侦察记录

实抓时间：2026-10-02（用户浏览器过验证码解封 IP 后），限速 ≥8 秒/请求。
三源：TJL01 主馆（opacwh.tjl.tj.cn:8991）、TJC01 少儿馆（opacse.tjl.tj.cn:8991）、
中新友好图书馆 ZXYH（sm.interlib.cn:8104，Interlib 租户 STC001）。

## ALEPH 两源（TJL01 / TJC01，同版本 www_f_chi）

### 检索 find-b

- URL：`/F?func=find-b&request={词}&find_code={索引}&local_base={TJL01|TJC01}`。
- **索引代码是 ISB 不是 ISBN**：`find_code=ISBN` 返回「检索请求解析错误」+ 基本检索表单页
  （标题「中文文献库 - 基本检索」；该错误页样本已被后续 ISB 成功抓取覆盖，未留存）。表单下拉原值：
  WRD 所有字段 / WTI 题名关键词 / TIT 题名(精确匹配） / ETI 正题名(精确匹配） / WAU 著者 /
  WSU 主题词 / WPU 出版社 / ISS ISSN / **ISB ISBN** / CAL 索书号 / SYS 系统号 / BAR 条形码 /
  SUD Gov't Doc, No. / LCI LCCN / TXT 全文 / TAG 用户标签。
- 计数文本：`记录         1 -       10 of       156 (最大显示记录      1000 条)`，
  正则 `记录\s*(\d+)\s*-\s*(\d+)\s*of\s*([\d,]+)`。
- **ISB 单命中直接返回完整记录页**（标题「中文文献库 - 查看完整记录」，find_tjl01_isbn.html
  即此形态：ISBN 9787536692930 → 《三体》DOC-NUMBER 000856840），不是 brief 列表；
  多命中才是 brief 列表（TJC01 ISB 9787221179975 → `记录 1 - 7 of 7`，find_tjc01_isbn.html）。
  解析器必须同时处理两种形态。

### brief 条目结构（find_tjl01.html）

每条目前有一个 `<!-- publish section ... -->` 注释块，含结构化字段（原值）：

```
SET-ENTRY (2000)     = 000001
Z13-ISBN-ISSN (3100) = 978-7-5730-2384-1
SET-NUMBER (3200)    = 034908
DOC-NUMBER (3300)    = 002892667
Z05-BASE (3400)      = TJL01
TOTAL-NUMBER-OF-ITEMS (3500) =      3
TOTAL-NUMBER-OF-LOANED-ITEM (3600) =      0
```

可见区：`<div class=itemtitle><a href=...full-set-set...>题名&nbsp;:&nbsp;副题名</a>`，
字段表 `作者：/索书号：/出版社：/年份：`（td class=label1 + td class=content），
`func=item-global&doc_library=TJL01&doc_number=N` 单册链接。
**每页固定 10 条**；页面共 13 个 publish section 但只有 10 个 itemtitle——
以 itemtitle 所在块为准（含 `class=itemtitle` 的 chunk 才是真条目），并按 DOC-NUMBER 去重。

### 翻页：short-jump 是记录偏移，不是页码

- 结果页 JS 分页控件：`paginate(156, 1, 10, "http://.../F/VV1DY...-08005?func=short-jump&jump=1")`。
- **jump=N 的含义是「跳到第 N 条记录」**：实测同会话 `jump=2` 返回 `记录 2 - 11 of 156`，
  与第 1 页重叠 9/11 条（find_tjl01_p2.html）。页码 P 对应 `jump=(P-1)*10+1`。
- **必须用页内会话 URL**（`F/VV...` 前缀）：裸 `F?func=short-jump&jump=2` 丢会话，
  返回 10915 字节的空壳页（r2 抓取失败样本，已被 r3 覆盖）。
- set_number 绑定会话：翻页、详情、单册都要与首搜同 cookie 会话。

### 详情 full-set-set（detail_tjl01.html，format=999）

页首 `<!-- publish section -->` 注释块字段（原值）：

```
ISBN: 978-7-5730-2384-1
TITLE: 宇宙是巧合吗？ :如何轻松理解熵、三体及更多随机性问题
AUTHOR: 艾格纳
IMPRINT: 海南出版社
CALL-NO: P159/88
DOC-NUMBER: 002892667
BASE:       TJL01
FIND-REQUEST: WRD = ( 三体 )
```

### 单册 item-global（item_tjl01.html）

表头列序（原值）：`描述 | 单册状态 | 应还日期 | 分馆 | 馆藏地 | 架位 | 请求数 | 架位导航 | 条码 | OPAC注释 | SFX`。
实测行：`阅览 | 在架上 | 文化中心中图基藏 | （空） | P159/88`——
**「在架上」出现在应还日期列、「阅览」在单册状态列**（列名与内容语义错位，原值照录）。
可借判定按词不按列：含「在架」→ 可借；本书 3 册全在架，**无借出行样本**，
借出行的应还日期格式待真网验证（Task 9 补）。
行内还有 `func=item-global-exp&item_sequence=NNNNNN&sub_library=XXX` 详细链接（含条码列）。

### 编码与验证码

- GBK 抽查：「在架上」「在架」在 item 页均为 **UTF-8 字节**（GBK 不命中）；
  「借出」两不中（本书无借出单册，非编码问题）。页面按 UTF-8 处理。
- **验证码墙**：约 8 次/几分钟的快速请求触发 HTTP 401+「请验证验证码」，按 IP 封、
  跨会话跨 cookie 持续；2026-10-02 两次触发，均由用户在浏览器过一次验证码解封。
  抓取与适配器必须 ≥4 秒/请求、检出验证码页立即抛错不重试。

## ZXYH 中新友好（Interlib 租户，与穗杭同模板）

- 检索页与穗杭完全同构：`<div class="bookmeta" bookrecno="217795" booktype="1">`、
  title-link/author-link/publisher-link、`共 3 页`、下一页锚点；
  **无「检索到 N 条」文本 → total_results=None**（family parser 原生支持）。
  条目 div 还带 express_isbn/express_title/express_author 属性（ISBN 每条目可得）。
- 检索必须带 `curlibcode=STC001`（interlib 家族 quirk，已实现）。
- **详情必须带 curlibcode**：`GET /opac/book/217795`（穗杭形态）→ **HTTP 500**；
  `GET /opac/book/217795?curlibcode=STC001` → 200（detail_zxyh.html，99537 字节）。
  family parse_detail 直接可用：三体/刘慈欣/重庆出版社/2008/978-7-5366-9293-0/I247.55。
  → interlib 家族需把 curlibcode quirk 扩展到详情 URL。
- **馆藏 JSON 不需要 curlibcode**：`GET /opac/api/holding/217795?limitLibcodes=&isCluster=`
  → 200 JSON（holding_zxyh.json），顶层键与穗 holding.json 相同（多一个 shelfnoUrlMap）。
  family parse_holdings 直接可用，实测条目：
  `{library: 中新友好图书馆, location: 3F 3区, call_number: I247.55/107, status: 借出, due_date: 2024-09-15}`
  （due_date 来自 loanWorkMap[barcode].returnDate epoch 毫秒）。
- 页面自带的 `/opac/book/holdingpreview/{recno}` XML 端点返回空 `<records></records>`，不用。
- holdStateMap 22 项，为穗 29 项的子集，同码异名（如 15：查找中 vs 穗「暂停服务」）；
  可借判定按响应自带词表 + family 词表，未识别保守不可借。
- 馆名证据：检索/详情页均含「中新友好图书馆」「生态城」字样（防张冠李戴）。

## 分馆覆盖（TJL01）

find-b 表单的分馆下拉原值含：天津图书馆（复康路/海河园/文化中心各室区）、
通借通还行业分馆、和平/河西/河东等 16 区馆借阅室——即 TJL01 一个 base 覆盖全市网络
（完整列表见 find_tjl01.html 内嵌检索表单的分馆下拉）。TJC01 独立 base。

## ISBN 归并口径（三源合一的 book_id 形态）

- 归一键：ISBN 去连字符与空白、转大写后校验形态（13 位 978/979 开头或 10 位末位可 X）；
  脏值与无 ISBN 一律不参与归并，各自成条。
- 跨源同 ISBN 合并为一条，复合 record_id 按优先级 TJL01 > TJC01 > ZXYH 以 `+` 连接
  （如 `TJL01:A+TJC01:B+ZXYH:C`），书目字段取优先级最高成员原值。
- **源内**同 ISBN 多条只保留首条：find_tjc01.html 中 978-7-5133-5380-9 出现 4 次
  （多卷/重印，DOC-NUMBER 各不相同）——其余条目让位首条，spec 已接受该取舍。
  find_tjl01.html 的 978-7-5339-7735-1 出现 2 次是注释块伪影，
  DOC-NUMBER 去重后 10 条真实条目 ISBN 互不相同。
- fixture 佐证：find_tjl01.html 与 find_tjc01.html 的 ISBN 集合无交集、
  978-7-5366-9293-0 不在两份 WRD fixture 中——单测据此按源路由 fixture，
  保证跨源归并不会污染单源精确断言。

## 检索统计与容错口径

- `total_results`＝存活源合计；任一存活源不提供总数（ZXYH 无「检索到 N 条」）→
  如实 None，不编造。`total_pages`＝各源最大值，`has_next`＝任一源仍有下页
  （三源各自独立翻页，合并页只是并排展示）。
- 源级容错：≥1 源成功即返回存活源结果（数据原样，不标注残缺）；
  三源全失败 → RuntimeError 汇总各源错误（含「天津」）。
- 验证码墙例外：`_CaptchaError` 穿透源级容错立即上抛——它是按 IP 的全局限速
  信号，静默降级成「只有 ZXYH 的空结果」会误导调用方。
- get_holdings：首成员（目标源）失败报错（ALEPH 错误带馆名前缀），附属源失败
  跳过返回已查到部分；聚合序＝可借在前、馆名升序。
- get_book_detail：复合 id 取优先级最高成员，record_id 保留查询原样；
  ALEPH 详情走 **SYS 系统号检索**（`F?func=find-b&request={doc_number}&find_code=SYS`，
  单命中直出完整记录页，无会话可用，真网实测 73893 字节样本 detail_tjl01_sys.html）；
  无会话直连 `F?func=full-set-set&doc_library=…&doc_number=…&format=999` **不可用**
  （响应无书目字段），页内 full-set-set 链接是 set_number 会话形态。
- 天津馆藏不带 item_id：模块级 get_holdings 的归还日期补查分支真网永不触发
  （ALEPH 应还日期在单册页直取，ZXYH 在馆藏 JSON loanWorkMap）。

## 真网验证记录（2026-10-02，解封后共约 10 个 ALEPH 请求，间隔 ≥6 秒）

- `search_books("三体")`：total_results=213（TJL01 156 + TJC01 32 + ZXYH 25 三源合计，
  ZXYH 本次给出了「检索到 25 条」——总数并非恒为 None，取决于检索词；两种形态代码均兼容）；
  35 条＝TJL01 10 + TJC01 5 + ZXYH 20。TJC01 页内 10 条 brief 因同 ISBN 多卷集
  源内去重只剩 5 条（如 978-7-5133-5380-9 重复 4 次）——归并口径的已接受取舍。
- brief 条目「作者：」列真网原值即空（`<td class=content><BR>`），检索结果 author=""
  如实；作者信息在详情/ISB 单命中完整记录页才有。
- `search_books("9787536692930")`：三源各 1 条命中，归并成复合 id
  `TJL01:000856840+TJC01:000178012+ZXYH:217795`，total_results=3，
  字段取主馆完整记录页原值（三体/刘慈欣/重庆出版社；IMPRINT 无年份 → publish_year=""）。
- `get_holdings(复合 id)`：52 条跨三源聚合（TJL01 全市通借网络约 47 条，含 16 区馆；
  TJC01「天津少儿馆通借通还E」4 条；ZXYH 1 条），可借在前、馆名升序。
  已借出行应还日期列＝日期（如 2026-10-23），归一化成功——借出行推定结构获真网证实。
  词表外状态：分配中/编目中/物流中（两列同值，status 拼接已去重），保守不可借。
- `get_book_detail(复合 id)`：取 TJL01 成员走 SYS 检索，三体/刘慈欣/重庆出版社/
  I247.55/235/978-7-5366-9293-0，year 与 summary 空（页面无该数据，原值如实）。
- 验证期间 IP 曾再次 401 封禁（用户浏览器手动解封后继续）；`_open` 已把 HTTP 401
  映射为带「手动解封」指引的 _CaptchaError，穿透源级容错直达调用方。
