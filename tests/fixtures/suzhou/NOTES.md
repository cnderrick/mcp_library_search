# 苏州图书馆 OPAC 页面结构侦察（2026-10-03 实抓）

站点：`https://reader.szlib.com/opac/index`（图创 Interlib；页面标题「检索系统」，
`<meta name="keywords">` 自报「图创, interlib, 图书检索, 借书, , 苏州图书馆」，
页内馆名「苏州图书馆」；首页含高新区/钟楼/北馆等自助馆与「集群图书馆」字样）。
抓取全部只读 GET，共 6 次请求（index 1、搜索页 1、空结果页 1、详情页 1、馆藏 JSON 1，
另一次对无馆藏书目的馆藏探测），间隔 ≥2 秒，全程无 401／验证码／JS 质询。

入口登记与立项依据见 [docs/data-sources/cn.md](../../../docs/data-sources/cn.md) 总览表苏州行
（2026-10-03 实抓「三体」232 条、24 页）。

## Fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `index.html` | `GET /opac/index` | 首页指纹（标题、meta keywords） |
| `search_p1.html` | `GET /opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1` | 搜索第 1 页，10 条结果（检索到: 232 条结果，共 24 页） |
| `search_empty.html` | 同上，`q=azbycxq不存在xyz` | 生造关键词，0 条结果 |
| `detail.html` | `GET /opac/book/1006489923` | 《三体：图像小说》详情页 |
| `holding.json` | `GET /opac/api/holding/1006489923?limitLibcodes=&isCluster=` | 馆藏 JSON，8 条单册（2 在馆 6 借出） |

## 与广州基准（tests/fixtures/guangzhou/NOTES.md）的对照结论

**同构、家族 parser 直接可用**的部分（10/10 条搜索记录与详情、馆藏全字段实测解析无误）：

- 搜索页：`bookmeta` 容器带 `bookrecno`（即 book_id，本站为 7～10 位数字，如
  `1006489923`）、title-link/author-link/publisher-link class 锚点、
  `检索到: 232 条结果`（千分位正则兼容）、分页区「共 24 页」+「下一页」锚点、
  条目后随 expressServiceTab 的 `express_bookrecno`/`express_isbn` 属性。
- 详情页：`bookInfoTable` 两列表格（leftTD 标签/rightTD 值），标题在 data-sort=0
  行首个 `<h2>`；**同样没有独立索书号字段**，`call_number` 取「中图分类法」值
  （`I247.55`），完整索书号 `I247.55/1121` 在馆藏 JSON 的 `callno` 里。
- 馆藏：走 Ajax JSON `/opac/api/holding/{bookrecno}`，顶层字段与广州完全一致
  （holdingList/libcodeMap/localMap/holdStateMap/loanWorkMap/…）；单册字段
  state/callno/curlib/curlocal/barcode/loan 同构。
- 应还日期：`loanWorkMap[barcode].returnDate`（epoch 毫秒，UTC+8）实测借出样例
  归一为 `2026-04-13`/`2026-10-03`/`2026-10-31` 等，原值照登不判断。
- stale-label 缺陷（tagTr「没有标签」污染）在苏州记录上未触发：两册详情 author
  均为正确值「刘慈欣」，家族修复后无差异。

**差异点（均不需要新 quirk 字段）**：

1. 站点是**默认（非 pro2018）模板**：搜索页 `bookmeta` 容器、无 `libBookLi`／
   `bkTxtTit`，与广州基准同代，`InterlibConfig.pro2018` 保持默认 False。
2. 站点**不需要 curlibcode**：检索/详情/馆藏裸参数均通，`InterlibConfig.curlibcode`
   保持默认空串（广州行为）。
3. **馆藏走 `jsessionid` 与 `isCluster=false`**：详情页内嵌的馆藏请求 URL 形如
   `/opac/api/holding/{bookrecno};jsessionid=…?limitLibcodes=&isCluster=false`。
   家族 `get_holdings` 走 `isCluster=`（空）实测同样返回完整 holdingList，
   不依赖会话，故不新增字段。
4. libcodeMap 仅 4 项（`ST=苏图`、`999=中心馆`、`zd=职大分馆`、`GS=姑苏区分馆`），
   localMap 250 项；馆名翻译走家族既有回退逻辑，原值照登（主馆译名缩写「苏图」）。
5. 部分书目（如《三体：典藏版》1006429505）`holdingList` 为空但 maps 齐全，
   属**记录级数据事实**（无实体单册），返回空馆藏列表正确，非站点故障。

## 状态词表（实抓 holdStateMap 全量 25 态，原值照登）

`0=流通还回上架中、1=编目、2=在馆、3=借出、4=丢失、5=剔除、6=交换、7=赠送、
8=装订、9=锁定、10=预借、12=清点、13=闭架、14=修补、15=查找中、16=重复锁定、
31=运回中、32=已签收、33=已通还、34=报废、35=丢失赔书、36=已装订、66=调拨、
67=锁定查找中、68=共享还回中`

家族 `is_available_status` 对苏州 25 态的判定：**只有「在馆」→可借**；
含不可借词的（借出/丢失/剔除/编目/预借/闭架/交换/赠送/丢失赔书/流通还回上架中/
装订/已装订/锁定/重复锁定/清点/修补/查找中/锁定查找中/运回中/调拨/共享还回中）
按词命中不可借；词表外的（已签收/已通还/报废/馆际丢失等）按「都不中保守判不可借」
兜底——不对「已通还＝在架」之类做预设，读者侧不会白跑。
钉在 `tests/test_suzhou_parse.py`。

## 其他事实

- 检索「三体」总数 232 条、共 24 页（rows=10），`total_results` 可解析为真实值。
- 详情页 interlib 指纹存在（页内 `/opac/media/*` 静态资源、meta keywords 自报）。
- 未发现反爬：无验证码、无 401、无 JS 质询；UA 用家族 client 内置浏览器 UA 即可。
