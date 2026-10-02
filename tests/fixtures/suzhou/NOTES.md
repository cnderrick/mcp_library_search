# 苏州 Interlib 双源侦察（2026-10-03 实抓）

`adapters/cn/suzhou.py` 聚合两个独立 Interlib 系统，照天津「一城多源」范本：
**SZ＝苏州图书馆**（`https://reader.szlib.com`，主馆，优先级在前）＋
**SIP＝苏州工业园区图书馆**（`http://opac.sdll.cn:8088`）。两源均为图创 Interlib
**默认（非 pro2018）模板**、应用上下文 `/opac`，结构逐项同构；归并口径（同一 ISBN
跨源合成复合 book_id，成员按优先级 `+` 连接）见 docs/data-sources/cn.md
「一城多源合并」。抓取全部只读 GET，无 401／验证码。

子目录：`sz/`（苏州图书馆）、`sip/`（工业园区图书馆），各含
`index.html` / `search_p1.html` / `search_empty.html` / `detail.html` / `holding.json`。

## 两源公共结论（与广州基准对照）

- 搜索页：`bookmeta` 容器带 `bookrecno`、title-link/author-link/publisher-link
  class 锚点、「检索到: N 条结果」、「共 N 页」+「下一页」、expressServiceTab 的
  `express_isbn`。
- 详情页：`bookInfoTable`（leftTD/rightTD），标题在 data-sort=0 行首个 `<h2>`；
  **无独立索书号字段**，`call_number` 取「中图分类法」值。
- 馆藏：`/opac/api/holding/{bookrecno}` JSON 与广州完全同构；借出单册
  `loanWorkMap[barcode].returnDate`（epoch 毫秒，UTC+8）。
- tagTr stale-label 缺陷在两源记录上均未触发（author 正确）。

## SZ 苏州图书馆（`sz/`）

- 入口 `https://reader.szlib.com/opac/index`，页标题「检索系统」，meta keywords
  自报「图创, interlib…苏州图书馆」。HTTP 无 401。
- 实抓「三体」232 条、共 24 页。
- `detail.html` = 《三体：图像小说》1006489923；`holding.json` 8 册（2 在馆 6 借出）。
- libcodeMap 仅 4 项（`ST=苏图`、`999=中心馆`、`zd=职大分馆`、`GS=姑苏区分馆`，
  馆名译名缩写「苏图」原值照登）、localMap 250 项。
- 部分书目 `holdingList` 为空但 maps 齐全，属记录级数据事实（无实体单册）。

## SIP 苏州工业园区图书馆（`sip/`）

- 入口 `http://opac.sdll.cn:8088/opac/index`（裸域名＋HTTP＋8088 端口），页标题
  「检索系统」，meta keywords 自报「图创, interlib…苏州工业园区图书馆」。
- 实抓「三体」98 条、共 10 页。
- `detail.html` = 《一说〈三体〉》872372；`holding.json` 4 册（1 在馆 3 借出，
  借出带应还日期 `2026-10-21` 等）。
- libcodeMap 仅 5 项（`SDLL=工业园区图书馆`、`999=中心馆`、`DAYTON=馆藏业务处理馆`、
  `SIPDSH=东沙湖学校图书馆`、`SZCYS=重元寺`）；网点含网借书库、星海高中、
  科技阅览室、东部市民中心分馆等（location 原值）。

## 归并与容错口径

- `book_id`：`SZ:{recno}` / `SIP:{recno}`；跨源同 ISBN 命中合成复合 id
  （如 `SZ:1006429505+SIP:872372`），书目字段取优先级最高成员（SZ）原值。
- 源级容错照天津：检索 ≥1 源存活即返回；馆藏首成员失败报错、附属源失败跳过；
  任一存活源无总数则合计如实 None。
