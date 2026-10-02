# 南京图书馆（江苏省立馆）ALEPH 实抓侦察记录

> 结论：**已立项接入**——2026-10-02 用户拍板，作为第二源并入 `nanjing`
> （金陵 `JL:` ＋ 南图 `NJL01:`），ALEPH 解析同时上收为 `aleph/` 家族模块。

实抓时间：2026-10-02 晚（用户浏览器手工过验证码解封本机 IP 后；实测解封持续 ≥10 分钟，
远长于页面提示的 300 秒，且无 UA 裸请求同样放行）。节流按家族口径 ≥4 秒/请求。

站点：https://opac.jslib.org.cn/F/ ，前端 `Server: openresty`，后端 Ex Libris ALEPH
`u20_1 / www_f_chi`（与天津主馆同版本、同皮肤）。此前进不了是 openresty 前置的
**按 IP 全局验证码墙**，与天津 401 同型；解封前站点行为未取得样本（HTTP 状态待补）。

## 会话形态

无 Set-Cookie。会话号写在 URL 路径里：`/F/<26 位 token>-<进程号>`，同一会话内每次
`func` 调用进程号自增（首页 …-17293，检索 …-17395，详情 …-17662），token 部分恒定。
即**同一 token 可跨请求复用**，无需 cookie jar；换 token 也能起新会话。

## 数据库代码（find-m 多库检索表单原值）

| 代码 | 库名 |
|---|---|
| `NJL01` | 中文文献库（默认勾选） |
| `NJL09` | 西文文献库（默认勾选） |
| `CNBOK` | 中文图书库 |
| `WWBOK` | 西文图书库 |
| `CNSER` | 中文期刊库 |
| `WWSER` | 西文期刊库 |
| `LCL52` | 拟订书目库 |
| `ZDMLK` | 征订目录库 |
| `UCS01F` | 国图联编中文文献库 |
| `UCS09F` | 国图联编外文文献库 |

## 检索 find-b

- URL：`/F/<token>?func=find-b&request={词}&find_code={索引}&local_base={库代码}`
- 索引代码与天津同表（WRD 全部词 / WTI 题名关键词 / WAU 著者 / ISB ISBN / CAL 索书号 / SYS 系统号…），
  表单 `<option>` 原值已由 findm_form.html 存档。
- 计数文本与天津同式：`记录 1 - 10 of 2745 (最大显示记录 1000 条)`。
- 翻页：页面上原生形态 `func=short-jump&jump={1 基记录偏移}`，
  `jump=11` → 记录 11–20（已验证），与天津 `_JUMP` 正则同构。
- 空检索对照：`request=zzzzqqqxxnomatch2026` → 记录数区回落到「记录数」浏览列表（findb_empty.html）。

## 详情 full-set-set

- URL：`/F/<token>?func=full-set-set&set_number={6 位}&set_entry={6 位}&format=999`
- publish section 注释块与天津同字段：`DOC-NUMBER` / `TITLE` / `AUTHOR` / `IMPRINT` /
  `CALL-NO` / `FIND-BASE`。
- **`doc_library` 与 `FIND-BASE` 可以不同**：CNBOK 检索命中的记录，
  其馆藏链接里 `doc_library=NJL01`（书目主库）而注释块 `FIND-BASE: CNBOK`。
  取馆藏须用 `doc_library` 的值，不能用 `find-b` 的 `local_base`。

## 馆藏 item-global

- URL：`/F/<token>?func=item-global&doc_library={doc_library}&doc_number={doc}&year=&volume=&sub_library={分馆代码}`
- **`sub_library` 不可省**：留空返回「在服务器上没有找到所要查询的文件」重复填充的错误页
  （本次误抓样本 4.9MB，已删除，不入档）。
- 表内注释标记与天津一致：`Loan status` / `Due date` / `Due hour` / `Sub-library` /
  `Collection` / `Location` / `Barcode` / `Description` 等（南图多一列 分馆/架位-2）。
- 实测分馆代码：`MBKDB` 采编部（订购加工）、`MCBKL` 中文图书借阅、
  `MCTBY` 典藏书库(保存本)、`STBCB` 视听文献保存本。
  `MBKDB` 页 0 条单册（订购加工中，无在架单册），属数据边界。

## 与 ALEPH 家族解析器的兼容性（实跑后被采纳为家族成员）

南图接入时把天津内联的 ALEPH 解析与 HTTP 上收成 `aleph/` 家族模块
（`client.py` / `parser.py` / `__init__.py`），天津改为委托，南图直接复用家族原语——
**没有新写第二份本地解析副本**。家族函数实跑本目录 fixture 的结果：

| 函数 | 结果 |
|---|---|
| `parse_find` | NJL01 3192 条 / CNBOK 2745 条，题名·著者·索书号·出版社·年份均正确 |
| `parse_full_record` | 题名/ISBN/索书号正确（detail_entry2 索书号取到 `I207.411`，非空） |
| `parse_item_global` | 单册状态、分馆、馆藏地、索书号正确；`在架上` → available=True |
| `COUNT` / `JUMP` | 计数与翻页均匹配 |

南图给家族带来的两处差异，都落在 `AlephConfig`：

- `item_global_all_params=True`：`year/volume/sub_library` 必须出现在 URL 里（可留空），
  整个省略会返回「在服务器上没有找到所要查询的文件」错误页（误抓样本 4.9MB，已删）。
- `unblock_urls`：验证码墙按 host 独立，解封指引只列南图自己。

### 家族跨行吞值陷阱（本次暴露并修复）

字段取值正则原写 `\s*`，它会吃掉换行——字段为空时把**下一行**文本吞成值：

- `BRIEF_ISBN`：空 ISBN 记录（音像资料，NJL01:002910042）捕获到下一行
  `SET-NUMBER (3200)    = 002879`；
- `FULL_FIELDS`：古籍记录（NJL01:000942136，实抓 `detail_guji_empty_fields.html`）
  `ISBN:`/`IMPRINT:` 为空，详情页把 `TITLE: 續唐三體詩` 当成 ISBN、把
  `CALL-NO: GJ/806899` 当成出版社返回。

天津 fixture 各字段全非空，故从未暴露。已统一收紧为只吃同行空白
（`[^\S\n]*`），空字段如实回空串；回归断言钉在 `tests/test_nanjing_prov_recon.py`。

## 适配器形态

`adapters/nanjing.py` 双源：金陵 `JL:`（原有）＋ 南图 `NJL01:`（本次接入），
优先级 `("JL", "NJL01")`（市馆 > 省馆，同杭州 HZ > ZJ 口径）；详情与馆藏按成员前缀
路由到 `aleph.get_book_detail` / `aleph.get_holdings`。归并口径有一处**有意偏离天津范本**：
只有跨源命中的 ISBN 才合并，同源重复逐条原位保留（金陵联合目录同一本书常有
多条编目，按其口径只留首条会连馆藏一起丢）——见 `adapters/nanjing.py::_merge_books`。

## 同系/同墙站点当日状态（同一时段探测）

| 站点 | 结果 |
|---|---|
| 南京图书馆 opac.jslib.org.cn | ✅ 放行，全链路通（本记录） |
| 天津主馆 opacwh.tjl.tj.cn:8991 | ⛔ HTTP 401（本机 IP 仍在天津墙上；**分 host 独立封禁**） |
| 国家图书馆 opac.nlc.cn | ⛔ Empty reply（与既有登记一致） |
| 青岛 124.129.202.157/opac/search | ⛔ 3561B slideVerify 壳页（`/opac/index` 493KB 正常） |
| 北京 primo.clcn.net.cn | ⛔ 33KB「访问验证」WAF 页 |
| 扬州 ytlmopac.cn:8080 | ⛔ 2497B securitycam 壳页 |

结论：验证码墙**按 host 独立**，解南图不解天津；「同系统」不共享解封状态。

## 未取到的样本（换窗口再补）

- 解封前的失败态页面/状态码（本次只有解封后的样本）。
- 已借出单册（应还日期列渲染形态）——本次命中记录馆藏全部在架。
- 多库检索 `find-m` 的结果页：带 `find_base` 复选参提交仍回落表单页，提交参数形态待侦察。
