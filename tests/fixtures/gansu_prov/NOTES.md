# 甘肃省图书馆 SirsiDynix iLink 实抓侦察记录

实抓时间：2026-10-03，来源 http://search.gslib.com.cn/uhtbin/cgisirsi/x/x/0/49/
（会话入口，返回「快速检索」首页；表列入口 `http://search.gslib.com.cn/uhtbin/cgisirsi/`，
适配器统一打前者）。检索词「三体」，短语 `"三体"`、字段「所有字段」。

系统：**SirsiDynix iLink**（与大连 `adapters/cn/dalian.py` 同一产品线、页面同构）。
甘肃省图是这套 iLink 实例的主站，同时还挂天水/张掖/武威/陇南/甘南等地市州县馆
（入口「馆别」下拉），本适配器 `library_code="甘肃馆"` 只查省馆馆藏。

## 检索通道与会话（ps token 每响应变）

1. `GET /uhtbin/cgisirsi/x/x/0/49/` → 「快速检索」首页，含 `searchform`
   （action 形如 `/uhtbin/cgisirsi/?ps={token}/甘肃馆/{seq}/123`）与 `srchfield1` /
   `library` 下拉；落会话 cookie。
2. 检索是 **POST** 到 `searchform` 的 action，字段 `searchdata1` / `srchfield1` /
   `library`（馆别）/ `sort_by`（入口页 hidden 为 `TI`）。
3. 结果页 title「目录检索结果 - 所有字段 '三体'」；空结果页 title「目录检索结果」、
   summary 为 `&nbsp;`、无 hitlist。
4. 翻页/详情走结果页 `hitlist` 表单（action `…/{seq}/9`）：翻页 POST
   `form_type=JUMP^{start}`（start=(page-1)*20+1），详情 POST `VIEW^{N}=详细资料`
   （N 为命中集全局序号）。
5. **ps token 逐步解析**，绝不硬编码拼 URL；全程同一 CookieJar 串行、节流 ≥4 秒/host。

## srchfield1 / library（实抓）

- 检索字段下拉同大连：`GENERAL^SUBJECT^GENERAL^^所有字段`、`AU…`、`TI^TITLE^SERIES^^题名`、
  `SU…`、`SER…`、`PER…`；无 ISBN 专用字段。
- `library`（馆别）含 `ALL` 与各成员馆码：`甘肃馆`（甘肃省馆）、`陇南馆`、`甘南馆`、
  `秦州馆`、`麦积馆`、`张掖馆`、`武威馆`… 适配器按城市固定传馆别码。

## 检索语义（同大连）

- 实抓 `"三体"` 短语（所有字段）→ `检索到 101 题名`，20 条/页（hitlist
  first_hit=1/last_hit=20，p2 为 21/40），共 6 页（ceil(101/20)）。
- 适配器沿用大连口径：一律按 ASCII 双引号短语下发，短语 0 命中或源站拒答时退回裸词。
- 首条为《2016文化观察选粹 专著 金浪主编》（题名含「三体」相关，非唯一命中）。

## 详情页与馆藏（关键结构差异）

- 详情页 title「馆藏显示」，简要 `<dl>` 的 dt/dd：`题名`（拼串原值）、`著者`、`出版者:`、
  `出版日期:`、`面页册数:`、`ISBN:`（dt 文本带尾冒号，family `detail_field` 兼容）。
- **甘肃馆藏表没有 `id="display_holdings_table"`**（大连有），故家族 `holdings_rows`
  改为全页扫描 `td.holdingslist` 数据行，用单枚 `th.holdingsheader[align=left]` 表头行
  跟踪分馆（列头行有多枚 th，据此区分）。
- 数据行列序：索书号 / 复本号 / 馆藏类型 / 馆藏位置；**后续复本的索书号格是 `&nbsp;`**，
  家族按分馆分组沿用上一行索书号（大连实现会据空值过滤掉这些行，甘肃变体需保留）。
- `copy_info`（`<dd class="copy_info">`）是本页可借信号：
  - `N 件馆藏在架上 {分馆}.` → `status="在架上"`、`available=True`。
  - `N 馆藏于 {分馆}.` → 仅表位置，`status="馆藏于"`、`available=False`（保守，不猜）。
- 匿名视图无单册条码、无独立应还日期字段（`到期:` 文本落在馆藏位置列，原值照登），
  故 `item_id`/`due_date` 恒空串。

## fixture 清单

- `entry_raw.html`：「快速检索」首页（含 searchform / srchfield1 / library 下拉 / hidden sort_by）。
- `search_prov.html`：省馆 `"三体"` 结果页（101 命中，20 条/页）。
- `search_p2.html`：JUMP^21 翻到的第 2 页（first_hit=21/last_hit=40）。
- `search_empty.html`：空结果页（乱串，summary `&nbsp;`、无 hitlist）。
- `detail_prov.html`：《2016文化观察选粹》详情（copy_info「1 馆藏于 甘肃省馆.」，
  馆藏表 3 复本，可用性保守 False）。
- `detail_onshelf.html`：《不要回答 Vol.01 红岸》详情（copy_info「1 馆藏于 甘肃省馆.」，
  馆藏表 3 复本）。

## 数据边界

- 馆藏到**索书号级**，无单册条码/应还日期；无明确「在架上」词时全部 `available=False`，
  `status` 原值照登，不做「馆藏于＝可借」预设。
- 列表页每条亦带 `holdings_statement`（如「1 馆藏于 甘肃省馆 在 社科闭架」），
  `search_books` 用作 `availability_summary`（原值照登）。
