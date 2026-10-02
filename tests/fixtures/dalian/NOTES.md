# 大连 SirsiDynix iLink 实抓侦察记录

实抓时间：2026-10-02，来源 http://ykt.dl-library.net.cn/ （大连地区网上联合目录查询系统，
官网 www.dl-library.net.cn「馆藏资源」外链；超星 dl.superlib.net 仍 IP 白名单硬墙，弃用）。
系统：**SirsiDynix iLink**（原 Sirsi WebCat，本仓库首见的新家族），匿名可用、无验证码、无 IP 墙。

## 编码

页面 charset＝**utf-8**（HTML meta 与实测一致）；初始 302 重定向页的 HTTP 头可能标
`iso-8859-1`，**以内容为准**，统一 utf-8 解码、errors=replace。

## 会话流程（ps token 每响应都变，全程同一 CookieJar 串行）

1. 根路径 `GET http://ykt.dl-library.net.cn/` 是 112 字节的 **meta-refresh** 到
   `/uhtbin/cgisirsi/x/x/0/49/`（urllib 不跟 meta-refresh，适配器直接打后者）。
2. `GET /uhtbin/cgisirsi/x/x/0/49/` → 302 → `/uhtbin/cgisirsi/?ps={token}/DALIANLIB/X/60/1182/X`
   「快速检索」首页（entry_raw.html）；落 cookie `session_security` + `session_number`（HttpOnly）。
3. 检索是 **POST** 到首页 `searchform` 的 action（形如
   `/uhtbin/cgisirsi/?ps={token}/DALIANLIB/X/123`），字段：
   - `searchdata1`＝关键词
   - `srchfield1`＝检索字段（见下）
   - `library`＝`ALL`（或分馆码，见下）
   - `sort_by`＝`ANY`
4. 结果页（search.html）title＝`目录检索结果 - 题名 '三体'`；空结果页（search_empty.html）
   title＝`目录检索结果`、正文含 `没找到所需文献`、无 hitlist 表单。
5. **token 逐步解析**：每个响应里的 form action / 链接都带**当次新生成**的 ps token
   （同一页内不同 form 的 token 各不相同）。适配器一律从上一步响应解析下一步 action，
   绝不硬编码拼 URL。陈旧 token 会被 302 到新 token（同 CookieJar 下 urllib 自动跟随、自愈）。

## srchfield1 下拉取值（实抓，无 ISBN 选项）

```
GENERAL^SUBJECT^GENERAL^^所有字段   → 所有字段
AU^AUTHOR^AUTHORS^Author Processing^著者
TI^TITLE^SERIES^Title Processing^题名
SU^SUBJECT^SUBJECTS^^主题
SER^SERIES^SERIES^Title Processing^丛书
PER^PERTITLE^SERIES^Title Processing^期刊名
```

**无 ISBN 专用字段**。ISBN 形态关键词走最接近的通用检索 `GENERAL`（所有字段）：
实测 `9787229100629` 与带连字符 `978-7-229-10062-9` 均命中《三体 Ⅲ 死神永生》
（检索到 2 题名、目标在第 1 位）。通用关键词同样走 `GENERAL`（所有字段，最宽）。
详情重定位用 `TI`（题名）字段——题名最specific、能把目标 catkey 稳定带回首页。

## 检索语义：裸词＝逐字 AND，引号＝短语检索（实网实测，浏览器可复现）

源站检索不做分词、无相关度排序，**裸词按单个汉字取交集**：

| 字段 | 查询 | 命中 | 首条 |
|---|---|---|---|
| 所有字段 | `三` / `体` | 218148 / 241303 | — |
| 所有字段 | `三体` | **27944**（＝上两行交集） | 《船舶结构与设备 专著…》 |
| 所有字段 | `中国` | 1031335 | 《水宝宝的奇妙之旅…》 |
| 题名 | `三体` | 862 | 《腾格里沙漠的造林人…》（含「三」「体」二字） |
| 所有字段 | `9787229100629` | 2 | 《三体 Ⅲ 死神永生》 |

**ASCII 双引号才是短语检索**，结果立刻相关：

| 字段 | 查询 | 命中 | 首条 |
|---|---|---|---|
| 所有字段 | `"三体"` | **132** | 《赡养人类》刘慈欣 |
| 题名 | `"三体"` | **63** | 《三体 Ⅲ 死神永生》 |
| 所有字段 | `"9787229100629"` | 2 | 《三体 Ⅲ 死神永生》 |

- 多词/长词引号与否无差别（题名 `三体 刘慈欣` 与 `"三体 刘慈欣"` 均 20 条；
  题名 `刘慈欣` 与 `"刘慈欣"` 均 291 条）——逐字 AND 在词长够时已能自然收敛。
- **索引不收的字符会让短语 0 命中或源站拒答**：题名 `"三体 Ⅲ 死神永生"` 回
  `Error message` 页（“您的登录会话已处于非活动状态…”，8285 字节，非结果页）；
  题名 `三体 Ⅲ` 裸词 862 条（Ⅲ 被忽略）。
- 适配器取舍：一律按短语下发；短语 0 命中或回 Error 页时退回裸词再试一次。
  `Error message` 页**不是**会话失效（会话失效是跳回「快速检索」首页形态），
  故详情候选梯度遇 Error 页换下一候选、不重建会话。

## library 下拉（分馆码，节选）

`ALL`（全馆，默认）+ 各分馆码，如 `DALANLIB-S`＝大连中心馆、`SHAOERLIBS`＝少儿分馆、
`ZHLIB-S`＝庄河分馆、`KFQLIB-S`＝开发区分馆、`LSLIB-S`＝旅顺分馆、`PLDLIB-S`＝普兰店分馆、
`CHLIB-S`＝长海分馆、`GXLIB-S`＝高新凌水街道分馆、`LUXUNLIB-S`＝鲁迅路分馆 等（含多个专业分馆）。
适配器检索固定用 `ALL`；分馆名在馆藏里以中文原值出现（见下）。

## 总数与分页

- 总数在 `searchsummary`：`题名 "三体" 检索到 862 题名.` → `检索到 (\d+)`＝**862**（total_results 取真值，不编造）。
- 空结果页 searchsummary 为 `&nbsp;`、正文 `没找到所需文献` → total_results＝0。
- **每页固定 20 条**（hitlist 表单 first_hit=1 / last_hit=20），源站**无每页条数参数** → limit 不生效。
- 翻页：结果页 hitlist 表单（action `/uhtbin/cgisirsi/?ps={token}/DALIANLIB/X/9`）POST
  `form_type=JUMP^{start}`（start＝(page-1)*20+1）+ first_hit/last_hit。实测 JUMP^21 取第 2 页
  （first_hit=21/last_hit=40，search_p2.html），与第 1 页 ckey 无重叠，summary 仍为 862。

## book_id 与详情/馆藏获取（关键：无 catkey 直链）

- 每条命中的 **catkey** 在结果页 JS `keep_ckeys_array.push("{catkey}")` 与
  `put_keepremove_button('{catkey}',…)` 里，按命中顺序（1-based）。
- 详情**没有可直接 GET 的 catkey URL**：详情页是 hitlist 表单里「详细资料」按钮
  （submit `VIEW^N`）POST 到 hitlist action（`/X/9`）的响应，N＝命中序号（会话内位置）。
  POST body＝`first_hit=1&last_hit=20&form_type=&VIEW^N=详细资料`。响应 title＝`馆藏显示`。
- **catkey 不可检索**：GENERAL 检索 catkey `3305715` 实测 0 命中（summary=&nbsp;）。
- 因此 `book_id = "{catkey}:{题名}"`（题名＝hitlist `dd.title` 原值，是拼串）。get_book_detail /
  get_holdings 用题名走 **TI 字段重检索** → 命中列表按 catkey 定位序号 N → POST `VIEW^N` 取详情页。
- **整串题名不可检索（详情链路失败的根因）**：短语检索
  `"船舶结构与设备 专著 Ship structure and equipment 中英 肖仲明主编 eng"` 与裸词均 0 命中。
  **截断到资料类型词（「 专著」等）之前**才对：`"船舶结构与设备"` 命中 24 条、目标 catkey
  在第 1 位、`VIEW^1` 取到详情页（著者「肖仲明 主编」、大连海事大学出版社、
  ISBN 9787563247721、索书号 I247.55/9275-PT）。
- 含罗马数字的题名短语会被源站拒答（`"三体 Ⅲ 死神永生"` 回 Error 页），裸词截断题名可用
  （`三体 Ⅲ 死神永生` 命中 6 条、目标第 1 位）。故适配器按**候选梯度**下发：
  短语截断题名 → 裸截断题名 → 裸整串 → 短语首段 → 裸首段，取第一个能把目标 catkey
  带回命中列表的候选。
- **VIEW^N 的 N 是命中集全局序号，不是页内序号**（实测：《上瘾》题名检索 56 条，
  catkey 1919934 在第 2 页第 11 位；`VIEW^11`＋区间 21/40 取回第 1 页第 11 位的
  《成就上瘾》，`VIEW^31`（＝20＋11）才取回目标）。first_hit/last_hit 传当前页区间或
  1/20 结果一致，不影响 N。适配器按 `(页-1)×20＋页内序号` 换算。
- **命中多于首页时需翻页定位**：截断题名越短命中越多（《上瘾》56 条 → 目标在第 2、3 页），
  适配器在候选内逐页 JUMP 找 catkey（上限 5 页），找到后按全局序号 VIEW^N。
- 老记录题名无「 专著」等资料类型分隔词（如「上瘾 辛卉著 陈毓华著 shang yin」），
  截断不生效、整串短语与裸词均 0 命中，需退到**首个空格段**（「上瘾」）才定位得到。

## 详情页（馆藏显示）结构

- 简要展示 `<dl>` 的 dt/dd 对（取首个）：`题名`（原值含「专著/典藏版/刘慈欣著」尾巴，
  iLink 把题名＋资料类型＋版本＋责任者拼成一串，**原值照登不猜**）、`著者`、`出版者`、
  `出版日期`、`面页册数`、`ISBN`（首个为纯 ISBN 9787229100629；MARC 区第二个带定价
  `978-7-229-10062-9 CNY48.00`，取首个）、`馆藏分布状况`（copy_info）。
- **无内容提要字段**（contentcfg-summary 是空 JS 配置）→ summary 恒空串。
- 索书号取自馆藏表首个数据行（详情页简要 dl 无独立索书号字段）。

## 馆藏表（display_holdings_table）与可借口径

- 匿名视图只到**索书号级**：表按分馆分组，`th.holdingsheader[align=left]`＝分馆名，
  数据行 `td.holdingslist`＝[索书号, 复本数, 馆藏类型, 馆藏位置]。
  例：`普兰店分馆 | I247.55/9275-PT | 2 | 流通图书 | 普成人外借`。
- **无单册条码、无应还日期** → `due_date` 恒空串、`item_id` 恒空串（数据边界，非故障）。
- 可借信号在 copy_info（`<dd class="copy_info">`，即「馆藏分布状况」）：
  - `{N} 件馆藏在架上 {分馆}.` → **明确在架**，判 available=True、status="在架上"。
  - `{N} 馆藏于 {分馆}.` → 仅表位置、**无明确在架词**，保守判 available=False、status="馆藏于"。
  - 词表外文案：原值照登、保守 available=False，**不做「馆藏于＝可借」预设**。
- hitlist 每条也有 `holdings_statement`（如 `2 件馆藏在架上 普兰店分馆` /
  `1 馆藏于 长海分馆 在 长海少儿库`），search_books 用作 availability_summary（原值照登）。

## fixture 清单

- `entry_raw.html`：会话入口「快速检索」首页（含 searchform / srchfield1 / library 下拉）。
- `search.html`：非空结果页（「三体」题名检索，862 命中，20 条/页）。**用 TI 字段抓**；
  结果页 DOM 与检索字段/引号无关，parser 通用。
- `search_p2.html`：JUMP^21 翻到的第 2 页（first_hit=21/last_hit=40）。
- `search_empty.html`：空结果页（乱串题名，`没找到所需文献`）。
- `search_phrase.html`：短语检索结果页（所有字段 `"三体"`，132 命中，20 条/页，
  首条《赡养人类》刘慈欣）。
- `error_message.html`：源站 Error 页（`Error message` title ＋ 会话非活动提示，
  8285 字节）。由题名短语 `"三体 Ⅲ 死神永生"` 触发的实抓响应；
  **非结果页也非入口页**，详情候选梯度据此判定「换候选」而非「会话失效」。
- `detail.html`：《三体 Ⅲ 死神永生》详情（馆藏显示，copy_info「2 件馆藏在架上 普兰店分馆」，
  索书号级单行）。
- `detail_located.html`：《腾格里沙漠的造林人…》详情（copy_info「1 馆藏于 长海分馆」，
  测 available=False 分支）。

## 请求计数（实抓阶段，dev 期一次性）

对 `ykt.dl-library.net.cn` 分阶段实抓（入口/检索/详情/翻页/ISBN 路由/题名重定位），
均节流 ≥4 秒、无验证码/封禁迹象。适配器真网冒烟另行 ≤14 请求（见交付报告）。

**2026-10-02 检索语义定位与修复验证**：分步探针约 80 次请求（字段对照、逐字 AND
判定、引号短语、候选梯度各分支），另修复后冒烟验证约 20 次请求（检索 132 条、
《三体 Ⅲ 死神永生》详情与馆藏、含罗马数字关键词兜底、两枚 fixture 采集），
全程只读、匿名、4 秒节流，无封禁迹象。

**2026-10-03 详情定位补测**（找《上瘾》时暴露）：实网约 30 次请求，确认 VIEW^N 为
全局序号、命中跨页需翻页定位、无资料类型词的老记录需首段兜底（证据见上文各条）。
