# 江阴市图书馆 OPAC 页面结构侦察（2026-10-02 实抓）

站点：`http://libopac.jylib.cn:9090/opac/index`（图创 Interlib，页面标题「检索系统」，
页内馆名全称「江阴市图书馆」；馆藏 libcodeMap 里 JYLIB 的译名原值是「江阴图书馆」，
两个名字并存，原值照登）。自建单租户站点，检索/详情/馆藏均**不需要 curlibcode**。
抓取全部只读 GET，共 5 次请求（index 指纹 1、搜索页 1、详情页 1、馆藏 JSON 1、
空结果页 1），间隔 ≥2 秒，无 401/验证码。

## Fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `search_p1.html` | `GET /opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1` | 搜索第 1 页，10 条结果（检索到: 82 条结果） |
| `search_empty.html` | 同上，`q=azbycxq不存在xyz` | 生造关键词，0 条结果 |
| `detail.html` | `GET /opac/book/1139334` | 《三体》导读（《三体》的导读 companion 作品）详情页 |
| `holding.json` | `GET /opac/api/holding/1139334?limitLibcodes=&isCluster=` | 馆藏 JSON，8 条单册（6 在馆 2 借出） |

注：「三体」检索第 1 条命中的是导读作品 1139334 而非小说正主（正主「三体：典藏版」
是 1167504，同页命中）；fixture 按实抓原样保留。

## 与广州基准（tests/fixtures/guangzhou/NOTES.md）的对照结论

**同构、家族 parser 直接可用**的部分：

- 搜索页：`bookmeta` 容器带 `bookrecno`（即 book_id，7 位数字）、
  title-link/author-link/publisher-link class 锚点、`检索到: 82 条结果`
  （千分位正则兼容）、`meneame` 分页区「共 9 页」+「下一页」锚点、条目后随
  expressServiceTab 的 `express_bookrecno`/`express_isbn` 属性。10/10 条全部
  解析出 book_id/title/author/publisher/publish_year/isbn。
  （页内 title-link 出现 12 次＞10 条，同一条目可有多个 title-link，家族 parser
  以 bookmeta 容器定界、后值覆盖，实测标题无误。）
- 详情页：`bookInfoTable` 两列表格（leftTD 标签/rightTD 值），标题在 data-sort=0
  行首个 `<h2>`；leftTD 标签集：题名/责任者、ISBN、语种、载体形态、出版发行、
  内容提要、主题词、中图分类法、主要责任者（可多行）；同样**没有独立索书号字段**，
  `call_number` 取「中图分类法」值（`I207.4 版次： 5` → `I207.4`），完整索书号
  `I207.4/247` 在馆藏 JSON 的 `callno` 里。
- 馆藏：走 Ajax JSON `/opac/api/holding/{bookrecno}`，顶层字段与广州完全一致
  （holdingList/libcodeMap/localMap/holdStateMap/loanWorkMap/…）；单册字段
  state/callno/curlib/curlocal/barcode/loan 同构。
- 应还日期：`loanWorkMap[barcode].returnDate`（epoch 毫秒，UTC+8）实测两条借出
  样例 → `2024-10-06`（相对抓取日已过期，原值照登不判断）与 `2026-12-23`。
  广州 fixture 当时无借出样例，江阴补上了这一实证。

**差异点（均不需要新 quirk 字段）**：

1. 站点是 **HTTP 明文 + 9090 端口**（base_url=`http://libopac.jylib.cn:9090`），
   非 HTTPS；家族 client 不挑协议，无影响。
2. 与杭州一样**无「馆藏浏览」锚点**，详情页用「馆藏地点」表述（仅证据意义，
   家族解析不依赖该锚点）。
3. 空结果页**没有** `bookDetail(数字` 锚点，也没有杭州那种 `function bookDetail(`
   JS 函数定义，只有 `检索到: 0 条结果`；家族按 bookmeta 容器解析，天然兼容。
4. libcodeMap 含大量学校分馆/农家书屋/24H 自助点（cjzx=长泾中学分馆、
   njsw=农家书屋、YueCheng24H=月城水韵社区（24H）…localMap 468 项），
   馆名翻译走家族既定回退逻辑即可。

## 状态词表（实抓 holdStateMap 全量 23 态，原值照登）

`0=流通还回上架中、1=编目、2=在馆、3=借出、4=丢失、5=剔除、6=交换、7=赠送、
8=装订、9=锁定、10=预借、12=清点、13=闭架、14=修补、15=查找中、16=重复锁定、
31=运回中、32=已签收、33=已通还、34=报废、35=丢失赔书、36=已装订、40=馆际丢失`

家族 `is_available_status` 对江阴 23 态的判定：**只有「在馆」→可借**；
含不可借词的（借出/丢失/剔除/编目/预借/闭架/交换/赠送/丢失赔书/流通还回上架中）
按词命中不可借；词表外的（已签收/已通还/报废/装订/已装订/锁定/重复锁定/清点/
修补/查找中/运回中/馆际丢失）按「都不中保守判不可借」兜底为不可借——
不对「已通还＝在架」之类做预设，读者侧不会白跑。钉在
`tests/test_jiangyin_parser.py::test_availability_conservative_for_jiangyin_states`。

## 暴露的家族 parser 缺陷（stale-label，非江阴特有）

详情页 `tagTr`（标签行，data-sort=98）的标签单元格是裸 `<td>` **不带 leftTD**，
值单元格 `<td class="rightTD" id="tagTd">` 内容是 `<label>没有标签</label>`。
`_DetailParser` 的 `_label` 跨行残留：当「主要责任者」行与 tagTr 之间**没有**
其他带 leftTD 的行时（即记录无「次要责任者」等中间行，本 fixture 记录 1139334
即是），tagTd 的值会以残留标签「主要责任者」被误归 `author`，解析出
`author="没有标签"`。

- 广州 fixture 记录恰有「次要责任者」行重置了 `_label`，所以广州/杭州基准从未
  触发；这是**家族级潜在缺陷**，任何城市的无次要责任者记录都会命中，江阴只是
  首个暴露者。
- 三城模板的 tagTr 结构逐字节相同（已比对），差异只在中间行有无。
- 真网冒烟实证（2026-10-02）：第二条真实记录 1167504（三体：典藏版，同样无
  次要责任者行）经适配器 `get_book_detail` 也解析出 `author="没有标签"`，
  证明该缺陷在江阴真实数据上普遍可触发，不是单条 fixture 的偶发。
- 建议 patch（归 `interlib/parser.py`，本地无权改动；已在 /tmp 仿真验证：
  广州/杭州 detail 解析零差异，江阴 author 修正为「路姜波」）：
  `_DetailParser.handle_starttag` 开头加

  ```python
  if tag == "tr":
      # 行边界重置标签：同一行内没有 leftTD 的 rightTD（如 tagTr「标签」行）
      # 不得复用上一行残留标签
      self._label = ""
      return
  ```

- 在 patch 合入前，`tests/test_jiangyin_parser.py::test_detail_author_not_polluted_by_tag_row`
  以 `xfail(strict=False)` 钉住正确期望值「路姜波」；patch 合入后该测试自动转 xpass。

## 其他事实

- 检索「三体」总数 82 条、共 9 页（rows=10），`total_results` 可解析为真实值。
- 详情页 interlib 指纹存在（与杭州同款模板证据）。
- 未发现反爬：无验证码、无 401、无 JS 质询；UA 用家族 client 内置浏览器 UA 即可。
