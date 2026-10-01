# 杭州图书馆 OPAC fixture 说明

抓取日期：2026-10-02。站点：`https://my1.zjhzlib.cn`（`www.hzlib.net` 不可达，base_url 必须用 `my1.zjhzlib.cn` 子域）。全部 HTTP 200，只读 GET。

| 文件 | 大小 | 来源 |
|---|---|---|
| `search_p1.html` | 210444 字节 | `GET /opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1` |
| `search_empty.html` | 90049 字节 | 同上，`q=azbycxq不存在xyz` |
| `detail.html` | 107550 字节 | `GET /opac/book/2007002340`（《三体漫画．起源》，从 search_p1 取第一个 bookrecno） |

## 搜索页结构

- 每条结果锚点 `bookDetail(<bookrecno>)`，`bookrecno` 是稳定书目 ID（`book_id = str(bookrecno)`）。search_p1 含 31 处，search_empty 含 0 处。
- 总数内联可解析：`检索到: 265 条结果`，且 JS 里带 `numFound=265`。
- 分页控件齐全：`page=1` 到 `page=10` 的链接（`sortWay=score` 排序下共 10 页）。
- **quirk**：空结果页仍含一行 JS 函数定义 `function bookDetail(bookrecno,index,flag){`（第 1671 行），因此裸字符串 `bookDetail(` 在空页也出现 1 次。家族解析器必须按「`bookDetail(` 后跟数字」匹配（`bookDetail(数字`），否则会把空页误判为有结果。`bookDetail(数字` 在 search_empty 里是 0 次。

## 详情页结构

### 书目元数据（服务端内联渲染，喂 `get_book_detail`）

`/opac/book/{bookrecno}` 返回的 HTML 里，书目字段是一张 `<table>`，行标签与值内联：

- `题名/责任者:` → 题名 + 作者（`三体漫画 / 刘慈欣原著 , 蔡劲，戈闻頔，薄暮改编`）
- `ISBN:` → `978-7-5339-7402-2`，同行带 `价格：CNY36.00`
- `出版发行:` → `杭州 : 浙江文艺出版社, 2024`
- `主要责任者:` / `次要责任者:` → 作者
- `标签:`、`简介`（6 处，含内容简介区块）

即：题名、作者、出版社、出版年、ISBN、简介都在详情页 HTML 里，可直接解析。

### 馆藏数据（不在详情页 HTML 里，单独 JSON 接口，喂 `get_holdings`）

详情页是个 JS 壳，馆藏表格由 dojo/dgrid 前端渲染，数据来自：

```
GET /opac/api/holding/{bookrecno}?limitLibcodes=&isCluster=false
```

返回 JSON，顶层字段：

- `holdingList[]`：馆藏数组。单条字段 `barcode`、`callno`（索书号）、`curlib`（所在馆代码）、`curlocal`（馆藏地点代码）、`state`（状态整数）、`stateStr`（JSON 里恒为 null，别用）、`shelfno`、`orglib`、`orglocal`、`indate` 等。
- `libcodeMap`：馆代码 → 分馆中文名（如 `0000` → `杭州图书馆`，`0200` → `萧山图书馆`）。`holdingList[i].curlib` 是代码，展示名要从这个 map 查。
- `localMap`：地点代码 → 馆藏地点中文名（如 `19010399` → `九堡镇红苹果社区`）。`curlocal` 是代码，展示名要从这个 map 查。
- `holdStateMap`：状态整数 → 中文状态名（`2` → `在馆`，`3` → `借出`，`13` → `闭架`，另有编目/丢失/剔除/锁定/预借等）。
- `loanWorkMap`：按 `barcode` 的借阅流水，`returnDate` 是 epoch 毫秒（绝对应还时间）。
- `libcodeDeferDateMap`：馆代码 → 应还天数（如 `0000` → `0`，`0900` → `3`，部分分馆 `7`）。

实测 `holdingList` 43 条：`state` 分布 2（在馆）25 条、3（借出）17 条、13（闭架）1 条；`curlib` 跨 16 个分馆（`0000` 杭州图书馆最多）。

### 详情页里的标记词（grep 计数）

| 标记 | detail.html 计数 | 说明 |
|---|---|---|
| 馆藏浏览 | 0 | 杭州无此锚点 |
| 馆藏地 / 馆藏地点 | 7 / 5 | 只在 JS 表格列定义与筛选 UI 里，不是数据本身 |
| 索书号 / callno | 2 / 7 | 同上，JS 列定义 |
| 在馆 / 借出 | 14 / 1 | JS 注释与提示文案 |
| 应还日期 | 0 | 不在 HTML，在馆藏 JSON（`loanWorkMap[].returnDate` / `libcodeDeferDateMap`） |
| ISBN / 简介 | 4 / 6 | 服务端内联，真实书目字段 |

## 杭州与广州的结构异同结论

同（支持「同属 Interlib 家族、可共用解析器」的判断）：

- 搜索 URL 结构、`bookDetail(<bookrecno>)` 锚点、`numFound` 总数、页码分页控件与广州一致（spec 已列，杭州实测复现）。
- 详情页书目表格（题名/责任者、ISBN、出版发行、简介）服务端内联，与 spec 描述一致。
- 详情页 JS 里有 `convertShelfno` 的广州分支（`P2GD020003` → `convertShelfnoForGuangzhou`），证明两城跑同一套 Interlib 前端模板。

异（杭州 quirk，家族模块需注意）：

1. **馆藏数据源**：杭州馆藏不在详情页 HTML 内联，而是单独的 JSON 接口 `/opac/api/holding/{bookrecno}`。spec 原文「详情页服务端渲染含馆藏」对杭州不成立。若广州详情页同样走这个 JSON 接口，家族模块应统一实现；若广州是内联 HTML，则杭州需要 quirk 字段指明 holdings 数据源。
2. **「馆藏浏览」锚点缺失**：杭州用「馆藏地点」表述，且只出现在 JS 里。家族模块不要依赖「馆藏浏览」这个字面量。
3. **应还日期**：不在 HTML。绝对应还时间是 `loanWorkMap[barcode].returnDate`（epoch 毫秒），另有 `libcodeDeferDateMap[libcode]` 给应还天数。`Holding.due_date` 要转成 `YYYY-MM-DD`。
4. **空页 JS 函数定义**：空结果页含 `function bookDetail(bookrecno,index,flag){`，解析器须按 `bookDetail(数字` 匹配书目锚点。
5. **状态与名称都是代码**：`state`、`curlib`、`curlocal` 都是代码，中文名分别查 `holdStateMap`、`libcodeMap`、`localMap`；`stateStr` 字段在 JSON 里恒为 null，不可用。

## 合流 TODO

- 家族模块 `get_holdings` 需确认杭州/广州是否都要打 `/opac/api/holding/{bookrecno}` 接口；若是，实现一次即可覆盖两城。
- 应还日期解析与状态归一化按上面第 3、5 点实现（epoch 毫秒 → 日期字符串；state int → 中文状态 → `available`）。
- 这些差异默认都是「家族模块的正常实现内容」，不需要杭州专属 quirk 字段——除非广州分支实抓后确认广州详情页是内联 HTML 馆藏，那才需要给杭州加「holdings 走 JSON 接口」的 quirk。
