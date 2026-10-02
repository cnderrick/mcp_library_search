# 合肥双源实抓侦察记录（2026-10-02）

两源合并（照天津「一城多源」范本）：

| 源 | 前缀 | 入口 | 技术组件 |
|---|---|---|---|
| 安徽省图书馆 | `AH` | https://opac.ahlib.com/opac/index | 图创 Interlib（与穗杭同模板） |
| 合肥市图书馆 | `HF` | https://opac.hflib.org.cn/lib2/ | 图创 Interlib（同模板，上下文路径不同） |

全部只读 GET，间隔 ≥2 秒，未遇 401/验证码。

## Fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `ah/search_p1.html` | `GET https://opac.ahlib.com/opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1` | 292814 字节，10 条，检索到 208 条 / 共 21 页 |
| `ah/detail.html` | `GET /opac/book/1901181704` | 《三体》重庆出版社 2008 详情页 |
| `ah/holding.json` | `GET /opac/api/holding/1901181704?limitLibcodes=&isCluster=` | 馆藏 JSON，19 册 |
| `hf/search_p1.html` | `GET https://opac.hflib.org.cn/lib2/search?q=三体&…`（同上参数） | 219515 字节，10 条，检索到 143 条 / 共 15 页 |
| `hf/detail.html` | `GET /lib2/book/1001460005` | 《三体》重庆出版社 2008 详情页 |
| `hf/holding.json` | `GET /lib2/api/holding/1001460005?limitLibcodes=&isCluster=` | 馆藏 JSON，21 册 |

## 可达性与上下文路径（HF 的关键差异）

- AH：`/opac/index` 200（107883 字节）。上下文路径 `/opac`，与家族默认一致，
  检索/详情/馆藏三端点全部穗式路径直连可用。
- HF：`/lib2/` 200（142222 字节）。**上下文路径是 `/lib2` 不是 `/opac`**：
  首页检索表单 `action="search"`（相对 `/lib2/`），静态资源全在 `/lib2/media/`；
  `/opac/search` 探测 → **nginx 500**（579 字节，nginx/1.30.4 错误页），`/opac` 在 HF 主机不可用。
  → 家族三原语硬编码 `/opac` 前缀，HF 不能直接套用；适配器按源上下文拼路径
  （`_Source.ctx`），HTTP 层与解析器仍复用家族 `interlib.client` / `interlib.parser`。
- HF 偶发不可达有前科（用户曾报「暂时无法打开」）：本次抓 fixture 期间 1 次
  25 秒超时、1 次 TLS 重置（SSL_ERROR_SYSCALL），重试即成功——与广州
  「TLS 偶发重置，重试即可」同款，非封禁信号。抓取全程未见验证码/401。

## 搜索页（两源与广州同构，家族 parse_search 直接可用）

- `bookmeta` 容器 + `bookrecno`、title-link/author-link/publisher-link 锚点、
  `express_bookrecno`/`express_isbn` 属性（ISBN 每条目可得，归并依赖）全齐。
- 「检索到: N 条结果」（AH 208 / HF 143）、「共 N 页」（21 / 15）、「下一页」锚点均在，
  total_results / total_pages / has_next 全部可解析，无 quirk 调整。
- 两源均无需 `curlibcode`（单租户独立站点，三端点直连 200）。
- 「三体」检索的跨源 ISBN 交集（复合 id 真网样本）：
  - `978-7-5366-9293-0`：AH 1901181704、1901137700（源内重复）/ HF 1001460005
    → 复合 `AH:1901181704+HF:1001460005`；
  - `978-7-229-15100-3`：AH 1900823256 / HF 1001515793、1001613715（源内重复）
    → 复合 `AH:1900823256+HF:1001515793`。
  两源 10 条全部带合法 ISBN；源内同 ISBN 重复（AH 2 条、HF 3 组）归并保留首条。

## 详情页

- 两源与广州同构：`bookInfoTable` leftTD/rightTD 两列、标题在首个 `<h2>`、
  ISBN/出版发行/中图分类法锚点都在，家族 parse_detail 字段可齐。
- **两源均无「内容提要」行 → summary=""（原值如实）**。「附注」行存在
  （AH/HF 均为「"地球往事"三部曲之一」），家族不映射附注，与穗杭行为一致，不特调。
- **HF 有真实「索书号」行**（如 `I427.55/40:1/2016`，即馆藏 callno 原值）；
  家族标签表不识别「索书号」，`call_number` 仍取「中图分类法」值（I247.55），
  与穗杭口径一致（穗杭页面无索书号行，HF 有但不特调，保持家族统一行为）。
- AH 出版发行「重庆 : 重庆出版社, 2008 2017重印」→ year 正则取首个 2008，符合预期。

### tagTr 坑：AH 的 author 会被「没有标签」覆盖（家族解析器潜在缺陷）

两源详情页都有读者个人标签行：

```html
<tr id="tagTr" data-sort="98">
  <td> <div align="left">标签:</div> </td>          <!-- 裸 td，无 leftTD 类 -->
  <td class="rightTD" id="tagTd"> <label>没有标签</label> </td>
</tr>
```

家族 `_DetailParser` 的 `_label` 只在 leftTD 结束时更新，裸 td 不更新标签 →
tagTd 的 rightTD 值会与**上一个残留标签**配对。各站表现：

- **AH**：「豆瓣内容简介/豆瓣著者简介」两行在 HTML 注释里（解析器跳过），
  tagTr 前的残留标签＝「主要责任者」→ `author` 被覆盖成「没有标签」
  （值单元无 `<a>`，走 `value.split()[0]` 兜底路径）。**实测复现**。
- HF：「主要责任者」后还有「附注」「索书号」两行 leftTD，残留标签不在映射表，
  author 幸免（刘慈欣）。
- 广州/杭州：残留标签是「次要责任者」，同样不在映射表，幸免——属布局巧合，
  缺陷类别相同（任何紧跟「映射表标签行」的无标签 rightTD 都会覆盖已解析字段）。

**修复状态（2026-10-02）**：家族 `_DetailParser._finish_value` 已合入「标签一对一
消费」修复（值单元结束后 `_label` 置空，江阴/温州独立实证同一缺陷，与本侦察
同日合流）——修复后 AH 详情页 author 直接解析为「刘慈欣」，实测通过。适配器
不再需要剔除 tagTr 行的规避；`tests/test_hefei_parse.py` 的
`test_ah_detail_author_not_clobbered_by_tag_row` 作为 AH 布局上的回归钉子保留。

## 馆藏 JSON（家族 parse_holdings 直接可用）

- 顶层键与广州一致（HF 多 `libLocalNavigatorMap`/`shelfnoUrlMap`，同 ZXYH，解析器不受影响）。
- AH：libcodeMap 5 馆（安徽省馆/中心馆/万科观山/安徽博物院/安徽艺术学院）；
  三体 19 册＝在馆 10 + 借出 9，本书馆藏全部在「安徽省馆」；
  借出册 `loanWorkMap[barcode].returnDate`（epoch 毫秒）→ due_date 全部归一成功
  （2026-03-13、2026-10-10 等）。
- HF：libcodeMap 140+ 馆（HT=合图、HST=合肥少儿图书馆、999=联盟中心馆，
  大量社区分馆/悦书房/24H 自助点——全市通借网络）；三体 21 册＝在馆 2 + 借出 19，
  本书馆藏全部在「合肥少儿图书馆」；due_date 全部归一成功（2026-07-18 等）。
- holdStateMap：AH 19 项，HF 23 项；**同码异名**：`31`＝AH「预处置」vs HF「运回中」；
  HF 独有 `34` 报废、`35` 丢失赔书、`36` 已装订、`40` 馆际丢失。
  词表判定核对：「运回中」含「还回」→ 不可借；报废/丢失赔书/馆际丢失/已装订/
  预处置/已签收/已通还/查找中均在词表外 → 保守不可借，符合「未识别不放行」口径。
- 单册字段集与广州一致（barcode/callno/curlib/curlocal/state/loan/shelfno/volInfo…），
  HF 多一个 `serial` 字段，解析器不受影响。

## 合并口径（照天津，实现于 adapters/hefei.py）

- book_id：单成员 `AH:{bookrecno}` / `HF:{bookrecno}`；跨源同 ISBN 命中合成复合 id，
  按优先级 AH > HF 以 `+` 连接，书目字段取最高优先级成员原值。
- ISBN 归并：去连字符与空白、校验形态后归并；脏值与无 ISBN 不参与、各自成条；
  源内同 ISBN 多条保留首条。
- `total_results`＝存活源之和；任一存活源无总数则如实 None，不编造。
  `total_pages`＝各源最大值，`has_next`＝任一源仍有下页。
- holdings/detail：按成员拆分路由后聚合（可借在前、馆名升序）；
  首成员（目标源）失败报错，附属源失败跳过返回已查到部分；detail 取最高优先级成员。
- 源级容错：≥1 源存活即返回（数据原样，不标注残缺）；两源全失败汇总报错（含「合肥」）。
- 两源均未观察到限频墙/验证码（与天津 ALEPH 不同），未加节流；家族 client 行为原样。

## 真网验证记录（2026-10-02，直接 import 适配器调三原语，共 7 个请求，间隔 ≥2 秒）

- `search_books("9787536692930")`：两源各 1 条命中，归并成复合 id
  **`AH:1135327+HF:1001460005`**（AH 的 ISBN 检索命中记录号 1135327，与关键词
  检索首条 1901181704 是不同书目记录——同书多条目原值如实），total_results=5
  （两源 ISBN 检索命中数之和），字段取 AH 原值：三体/刘慈欣/重庆出版社/2008。
- `search_books("三体")`：total_results=**351**（AH 208 + HF 143，与 fixture 一致），
  page 1（limit=20）合并后 22 条，其中复合 id 5 组：
  `AH:1901181704+HF:1001460005`、`AH:1900823256+HF:1001515793`、
  `AH:1900460010+HF:1000853803`、`AH:1900508911+HF:1000864651`、
  `AH:1901179835+HF:1001096470`；total_pages=11（各源最大值，AH 208/20 页）。
- `get_holdings("AH:1135327+HF:1001460005", only_available=False)`：跨两源聚合
  **91 条**，可借 32（冒烟输出未拆分源别计数，HF 成员与 fixture 同记录号）；
  排序＝可借在前、馆名升序
  （「合肥少儿图书馆」在「安徽省馆」前，码位序）；借出册 due_date 归一正常
  （2026-09-20、2026-11-10 等）。
- `get_book_detail("AH:1135327+HF:1001460005")`：只路由最高优先级成员 AH，
  返回 三体/刘慈欣/重庆出版社/2008/978-7-5366-9293-0/I247.55/summary=""，
  **author 未被「没有标签」覆盖**（家族修复真网生效）。
- 全程无 401/验证码/超时；HF 本次全程可达（抓取期 1 次超时 + 1 次 TLS 重置，重试即恢复）。
