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
