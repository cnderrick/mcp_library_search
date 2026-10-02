# 丽水市公共图书馆 OPAC 页面结构侦察（2026-10-03 实抓）

站点：`http://60.190.125.252:8086/opac/index`（图创 Interlib；页面标题「检索系统」，
`<meta name="keywords">` 自报「opac, 图创, interlib, 图书检索, 借书, , 丽水市公共图书馆」）。
裸 IP ＋ HTTP。抓取全部只读 GET，共 5 次请求（index 1、搜索页 1、空结果页 1、详情页 1、
馆藏 JSON 1），间隔 ≥2 秒，全程无 401／验证码。

立项登记见 docs/data-sources/cn.md 总览表丽水行。

## Fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `index.html` | `GET /opac/index` | 首页指纹（标题、meta keywords） |
| `search_p1.html` | `GET /opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1` | pro2018 搜索第 1 页，10 条结果（检索到 535 条、共 54 页） |
| `search_empty.html` | 同上，`q=azbycxq不存在xyz` | 生造关键词，0 条结果 |
| `detail.html` | `GET /opac/book/2990906` | 《三体：新版》详情页 |
| `holding.json` | `GET /opac/api/holding/2990906?limitLibcodes=&isCluster=` | 馆藏 JSON，4 条单册（3 在馆 1 借出） |

## 与广州基准的对照结论

**pro2018 模板代**（与台州/成都/绍兴同代，相对广州默认基准的差异）：

- 搜索：条目在 `<ul class="libBookUL"><li class="libBookLi">`（**非** bookmeta 容器），
  页内也带 `bookrecno` 属性；家族按 pro2018 分支解析，10/10 条全字段正确。
  总数「检索到记录 --> 检索到: 535 条结果,」；分页走 JS 变量 `totalPage:`/`currentPage:`。
- 详情：`parse_detail_pro2018` 零改动可用（`a.bkTxtTit`＋`bkTxtLeft/bkTxtRight`）：
  标题「三体：新版」、作者「刘慈欣」、出版社、出版年、ISBN、中图分类法均正确；
  该记录无内容提要 → summary 空串（数据边界）。**不需要** `pro2018_cite_author`
  （author 直接取到「刘慈欣」，绍兴那种引文块兜底不触发）。
- 馆藏：`/opac/api/holding/{bookrecno}` JSON 与广州基准完全同构（holdingList/
  libcodeMap/localMap/holdStateMap/loanWorkMap/…），家族 parser 零改动。
  借出单册 `loanWorkMap[barcode].returnDate`（epoch 毫秒，UTC+8）→ `2026-08-07`。

**差异点（均不需要新 quirk 字段）**：

1. 站点是 **pro2018 模板**（`InterlibConfig.pro2018=True`），其余配置走默认。
2. **不需要 curlibcode**：检索/详情/馆藏裸参数均通（同台州/成都）。
3. 入口是**裸 IP ＋ HTTP**（无域名，非 HTTPS），家族 client 不挑协议，无影响。
4. 全市联合目录：libcodeMap 含丽水市图书馆（`lsslib`）与景宁/庆元/缙云/遂昌/
   松阳/云和/青田等县馆及乡镇分馆、城市书房、阅读驿站，馆名翻译走家族回退逻辑。
5. 实抓 181917（《三体X》）holdingList 为空而 maps 齐全——记录级数据事实（无实体
   单册），返回空馆藏列表正确。
6. 详情记录无内容提要时 summary 空串（记录级差异，非站点 quirk）。

## 状态词表（实抓 holdStateMap，原值照登）

家族 `is_available_status` 对丽水状态词的判定：**只有「在馆」→可借**；含不可借词的
（借出/丢失/剔除/编目/预借/闭架/交换/赠送/流通还回上架中…）按词命中不可借；
词表外的按「都不中保守判不可借」兜底。实抓 2990906 含 `在馆`（可借）与
`借出`（不可借，带应还日期 `2026-08-07`）。钉在 `tests/test_lishui_parse.py`。

## 其他事实

- 检索「三体」总数 535 条、共 54 页（rows=10）。
- 未发现反爬：无验证码、无 401、无 JS 质询；UA 用家族 client 内置浏览器 UA 即可。
