# 数据源清单

各城市图书馆的线上入口、系统技术组件与接入要点。**新增城市先在总览表登记一行**，实现细节追加到对应小节。

## 总览

同一省份的城市排在一起，省份列只在该省首行填写（视觉上等同于合并单元格），新增城市时接在本省行之后。

| 省份 | 城市 | 标识 | 线上图书馆入口 | 技术组件 | 适配层位置 |
|---|---|---|---|---|---|
| 上海市（直辖市） | 上海 | `shanghai` | https://vufind.library.sh.cn | VuFind（上海中心图书馆"一卡通"总分馆体系，900+ 网点） | `vendor/shanghai_library/` + `adapters/shanghai.py` |
| 北京市（直辖市） | 北京 | — | 待调研 | Ex Libris Primo（初判） | 🔜 搁置：站点 WAF 拦截程序化访问 |
| 广东省 | 广州 | `guangzhou` | https://opac.gzlib.org.cn | 图创 Interlib | `interlib/` 家族 + `adapters/guangzhou.py` |
|  | 深圳 | `shenzhen` | https://www.szlib.org.cn/opac/ | 图书馆之城自研 JSON API（后端 ILAS，167 馆统一平台） | `adapters/shenzhen.py`（独立实现） |
| 浙江省 | 杭州 | `hangzhou` | https://my1.zjhzlib.cn | 图创 Interlib（与广州同模板） | `interlib/` 家族 + `adapters/hangzhou.py` |

## 上海（VuFind）

vendor 组件 shanghai-library-book-search-python（Apache-2.0），细节与本地补丁记录见根 [NOTICE](../NOTICE)。

- 检索总条数：站点统计区不再输出（`total_results` 恒为 0），adapter 按"0 且当前页有结果 → 视为未知（null）"处理，不属于代码 bug。
- 简介：站点没有独立简介区块，内容简介以书目"附注"字段（MARC 500）形式给出，vendor 补丁将 summary 回退到附注（见 NOTICE 变更）。
- 应还日期：馆藏页不直接渲染归还日期，已借出馆藏的 `<a class="item-return-date">` 只带单册 `data-itemid`，需按条调用 `AJAX/JSON?method=itemReturnDate`（vendor 提供 `get_return_date`，adapter 负责逐个补 `due_date`）。
- 同步上游：上游是平铺 import，已改为包内相对导入；覆盖同名文件同步后必须重新应用该修改。本地补丁（parser 的 has_next、library_client 的 statistics）同步后检查是否需重打，并在 NOTICE 变更里记一笔。

## Interlib 家族（广州、杭州）

`src/mcp_library_search/interlib/` 是一方共享代码：`client.py`（HTTP）、`parser.py`（搜索页/详情页 HTML + 馆藏 JSON）、`__init__.py`（三原语，对外签名冻结）。结构事实以广州 fixture 为基准（`tests/fixtures/guangzhou/NOTES.md`），杭州的结构兼容性钉在 `tests/test_hangzhou_compat.py`。

- 搜索页：每条结果是 `bookmeta` 容器（`bookrecno` 即 `book_id`），字段按 class 锚点提取（title-link/author-link/publisher-link）；总数"检索到: N 条结果"（带千分位逗号）；分页"共 N 页" + 「下一页」锚点存在与否。
- 详情页：书目在 `bookInfoTable` 两列表格（leftTD 标签 / rightTD 值）；**没有独立索书号字段**，`call_number` 取"中图分类法"值；简介取"内容提要"；标题在首个 `<h2>`。
- 馆藏：不在详情页 HTML 内联，走 Ajax JSON 接口 `/opac/api/holding/{bookrecno}`；馆码/位置码/状态码分别经 `libcodeMap`/`localMap`/`holdStateMap` 翻译，查不到回退码本身。
- 应还日期：借出单册在 `loanWorkMap[barcode].returnDate`（epoch 毫秒，按 UTC+8 解释，与馆方系统时区一致），退回单册 `loan` 字段保守提取。
- 可借分类：`is_available_status` 状态词表——命中不可借词优先，命中可借词次之，都不中**保守判不可借**（未识别状态不让读者白跑）。
- 杭州差异（quirk）：与广州同模板（详情页 JS 甚至带广州分支函数）；「馆藏浏览」锚点缺失（用「馆藏地点」）；空结果页含 `bookDetail(` 的 JS 函数定义，解析必须按 `bookDetail(数字` 匹配，不能裸数出现次数。
- 新接同族城市：`adapters/<city>.py` 照广州/杭州同款 `_client` 形态 + 在 `adapters/__init__.py` 注册 + 在本文件总览表登记。城市差异以带默认值的 `InterlibConfig` 字段（quirk）表达，默认值即广州行为。

## 深圳（自研 JSON API）

`adapters/shenzhen.py` 独立实现（与 Interlib 无关），轻量 client（urllib + json）内置在模块内。

- 接口：`getQueryResult`（搜索，真实总数 `numFound`）、`getBookDetail`（书目详情 + 三桶馆藏）。`book_id = "{tablename}:{recordid}"`，详情接口需成对传 `metaTable`/`metaId`。
- 分页：与参数名直觉相反——`page → v_page`（页码）、`limit → pageNum`（每页条数）。实测结论钉在 `tests/fixtures/shenzhen/NOTES.md`。
- 三桶：`CanLoanBook`/`OnlyReadBook` 是 `list[group]`，`BorrowedBook` 是单个 group dict 或 `null`，容器形态不一须归一化；`OnlyReadBook`（仅阅览）判不可借。
- 馆名：可借/阅览组在 group 级 `serviceaddrnotes`，借出单册在单册 `libraryNotes`；单册的 `library` 是馆代码不是馆名。
- 应还日期：`BorrowedBook` 单册的 `ReturnDate`（`YYYYMMDD` → 归一 `YYYY-MM-DD`）。
- 公共参数 `client_id=t1` 由 client 层统一注入，业务函数不传。
- 注意：该 API 非官方公开接口，字段可能漂移；字段侦察结论见 `tests/fixtures/shenzhen/NOTES.md`，漂移时以实抓为准更新解析与 fixture。
