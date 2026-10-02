# 苏州工业园区图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://opac.sdll.cn:8088/opac/index`（页标题「检索系统」，
`<meta name="keywords">` 自报「opac, 图创, interlib, 图书检索, 借书, ,
苏州工业园区图书馆」）。图创 Interlib **默认（非 pro2018）模板**，裸域名
＋ HTTP ＋ 8088 端口。抓取全部只读 GET，间隔 ≥1 秒，无 401／验证码。

立项登记见 docs/data-sources/cn.md 总览表苏州工业园区行。

## Fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `index.html` | `GET /opac/index` | 首页指纹（标题、meta keywords） |
| `search_p1.html` | `GET /opac/search?q=三体&…&rows=10&page=1` | 默认模板搜索第 1 页（检索到 98 条、共 10 页） |
| `search_empty.html` | 生造关键词 | 0 条 |
| `detail.html` | `GET /opac/book/872372` | 《一说〈三体〉》详情页 |
| `holding.json` | `GET /opac/api/holding/872372?limitLibcodes=&isCluster=` | 馆藏 JSON，4 条单册（1 在馆 3 借出） |

## 与广州基准的对照结论

**同构、家族 parser 直接可用**（10/10 条搜索、详情、馆藏全字段实测解析无误）：

- 搜索页：`bookmeta` 容器带 `bookrecno`（即 book_id，数字）、title-link/
  author-link/publisher-link class 锚点、`检索到: 98 条结果`、分页「共 10 页」+
  「下一页」锚点、条目后随 expressServiceTab 的 `express_bookrecno`/`express_isbn`。
- 详情页：`bookInfoTable` 两列表格（leftTD/rightTD），标题在 data-sort=0 行首个
  `<h2>`；**无独立索书号字段**，`call_number` 取「中图分类法」值（`I207.425`）。
- 馆藏：`/opac/api/holding/{bookrecno}` JSON 与广州完全同构（holdingList/
  libcodeMap/localMap/holdStateMap/loanWorkMap/…）；借出单册
  `loanWorkMap[barcode].returnDate`（epoch 毫秒，UTC+8）→ `2026-10-21` 等。
- tagTr stale-label 缺陷未触发（author 取到正确值「王一」）。

**差异点（均不需要新 quirk 字段）**：

1. **默认（非 pro2018）模板**，与苏州图书馆、江阴同代，`pro2018` 保持默认 False。
2. **不需要 `curlibcode`**：检索/详情/馆藏裸参数均通。
3. 站点是 **HTTP ＋ 8088 端口**（非 HTTPS），家族 client 不挑协议，无影响。
4. libcodeMap 仅 5 项（`SDLL=工业园区图书馆`、`999=中心馆`、`DAYTON=馆藏业务处理馆`、
   `SIPDSH=东沙湖学校图书馆`、`SZCYS=重元寺`），馆名译名照登。
5. 分馆/网点含网借书库、星海高中、科技阅览室、东部市民中心分馆等（location 原值）。

## 状态词表（实抓 holdStateMap，原值照登）

家族 `is_available_status` 判定：**只有「在馆」→可借**；含不可借词的
（借出/丢失/剔除/编目/预借/闭架/交换/赠送/流通还回上架中…）按词命中不可借；
词表外的按「都不中保守判不可借」兜底。实抓 872372 含 `在馆`（可借）与
`借出`（不可借，带应还日期）。钉在 `tests/test_suzhou_sip_parse.py`。

## 其他事实

- 检索「三体」总数 98 条、共 10 页（rows=10）。
- 未发现反爬：无验证码、无 401、无 JS 质询。
