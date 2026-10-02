# 重庆适配器（InDigLib）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `chongqing` 城市适配器：InDigLib「集群数字图书馆」会话流检索、详情与单册馆藏，接入 `_ADAPTERS`。

**Architecture:** `adapters/chongqing.py` 照 shenzhen.py 模式独立实现：cookie jar 会话 client（先 GET 简单检索页建立 JSESSIONID，再 POST `simpleSearch.action`；会话失效重建一次），限速 3 秒/请求，验证码页抛错。

**Tech Stack:** Python 3.12+ / urllib / pytest。

**Spec:** `docs/superpowers/specs/2026-10-02-tianjin-chongqing-adapters-design.md`

## Global Constraints

同 `2026-10-02-tianjin.md` 的 Global Constraints（不打真网、全角标点、不自动提交、限速、fixture 为准）。

## Review Focus

1. 首页表单的 action（`opacSearch.action`）是假端点；真端点 `OpacMarcSearchSolr!simpleSearch.action` 由 search.js 改写（本计划侦察已确认；用户独立验证过 `opacSearch` 亦可——实现时若 `simpleSearch` 返回异常，按 NOTES 的实抓为准切换到 `opacSearch`，改动仅限端点常量）。
2. 会话失效特征：响应为检索首页/登录页 → 重建会话重试一次，二次失败报错。
3. 单册馆藏状态字段未完全确认（`showAsset` 参数）；解析失败时 holdings 返回空列表 + NOTES 记录，不让 search/detail 一起失败。
4. `select1` 映射：默认 `all`，ISBN 形态 `isbn`（与深圳不同，无需整参集）。

---

### Task 1: 重庆 fixture 实抓与 NOTES

**Files:**
- Create: `tests/fixtures/chongqing/session.html`、`search.html`、`search_p2.html`、`detail.html`、`detail_asset.html`、`NOTES.md`

- [ ] **Step 1: 实抓（每请求间隔 ≥4 秒，cookie jar 保会话）**

```python
# 流程照 spec：GET frontV2/SearchIndex!simple.action?opacType=local（存 cookie）
# → POST OpacMarcSearchSolr!simpleSearch.action（select1=title&text1=三体）→ 存 search.html
# → 同会话抓第 2 页（翻页参数以结果页分页控件实抓为准，存 search_p2.html）
# → GET frontV2/BookDetail.action?metaid={N}&metatable=i_biblios → detail.html
# → 带 showAsset=true 再抓一次 → detail_asset.html
# → ISBN 验证：select1=isbn&text1=9787508687193，确认命中（select1 原值支持 isbn）
```

- [ ] **Step 2: NOTES.md 记录** — 真端点确认（simpleSearch vs opacSearch 两枚都试，记录哪个返回结果页）、翻页参数、`metaid` 提取位置、单册馆藏结构（detail_asset 与 detail 的差异、状态字段名与词表原值）、总计数文本位置（结果页「共 N 条」形态）。
- [ ] **Step 3: 向用户报告，确认后提交** — `重庆 fixture：InDigLib 实抓样本与字段侦察记录`

---

### Task 2: client 会话流与检索解析

**Files:**
- Create: `src/mcp_library_search/adapters/chongqing.py`（骨架 + `_open`/`_ensure_session`/`_parse_search`）
- Test: `tests/test_chongqing_search.py`

**Interfaces:**
- Produces: `_Client.search(keyword, page, limit)` → `_SearchResult`（record_id=`i_biblios:{metaid}`）；模块级 `_open(req, timeout)` 为 HTTP 入口（monkeypatch 点）。

- [ ] **Step 1: 写失败测试** — mock `_open`：首次 GET 会话页、POST 带 cookie；断言 POST 体含 `select1=title`（或 `isbn`）与 `text1`；`_parse_search(search.html)` 返回 ≥1 条、首条 `record_id` 以 `i_biblios:` 开头、`statistics.total_results` 与 fixture 的「共 N 条」一致；会话失效（响应为 session.html 特征）时重建会话重试一次。

- [ ] **Step 2: 跑测试确认失败。**
- [ ] **Step 3: 实现** — 骨架照 shenzhen.py 头部（`_UA`/`_HEADERS`/`_BASE="http://222.177.237.197:8080"`/`_SearchResult`/`_Book`）；`_open` 持 opener+CookieJar+3 秒节流；`_ensure_session` 访问 `InDigLib/frontV2/SearchIndex!simple.action?opacType=local` 建立会话；`_parse_search` 按 NOTES 结构提取条目（`BookDetail.action?metaid=N&metatable=i_biblios` 链接 + 题名/著者/出版社文本）与总数。

- [ ] **Step 4: 测试通过 + 全量。**
- [ ] **Step 5: 向用户报告，确认后提交** — `重庆：会话 client 与检索解析`

---

### Task 3: 详情与单册馆藏解析

**Files:**
- Modify: `src/mcp_library_search/adapters/chongqing.py`
- Test: `tests/test_chongqing_detail.py`

- [ ] **Step 1: 写失败测试** — `_parse_detail(detail.html, book_id)` 提取 title/author/publisher/publish_year/isbn；`_parse_holdings(detail_asset.html)`（或 NOTES 确认的结构）返回 `_Holding` 列表，status 为页面原值；若 fixture 确认无单册状态字段，断言 holdings 解析为空列表且不抛错。
- [ ] **Step 2: 跑测试确认失败。**
- [ ] **Step 3: 实现** — 字段提取照 NOTES；可借判定：状态词含「可借/在架」→ True，含「借出/阅览/不可借」→ False，其余保守 False（词表入 NOTES）；应还日期字段按实抓归一（YYYYMMDD → YYYY-MM-DD，照深圳 `_normalize_date`）。
- [ ] **Step 4: 测试通过 + 全量。**
- [ ] **Step 5: 向用户报告，确认后提交** — `重庆：详情与单册馆藏解析`

---

### Task 4: 模块原语与注册

**Files:**
- Modify: `src/mcp_library_search/adapters/chongqing.py`、`src/mcp_library_search/adapters/__init__.py`
- Test: `tests/test_adapter_contract.py`（自动覆盖）

- [ ] **Step 1: 写失败测试** — `chongqing` 出现在 `adapters._ADAPTERS`；契约三测绿。
- [ ] **Step 2: 跑测试确认失败**（未注册 KeyError/缺失）。
- [ ] **Step 3: 实现** — 模块级 `search_books/get_holdings/get_book_detail` 照 shenzhen.py 尾段（含 item_id→`get_return_date` 分支；重庆单册若无 item_id 则真网不触发，方法定义照天津模式）；`__init__.py` 注册 `"chongqing": chongqing`。
- [ ] **Step 4: 全量测试通过。**
- [ ] **Step 5: 向用户报告，确认后提交** — `重庆：模块原语与注册`

---

### Task 5: 真网验证

- [ ] **Step 1: 限速真网抽查**（≤8 次请求）：`search_books("三体")`、ISBN 检索、`get_holdings`、`get_book_detail`；与浏览器比对。
- [ ] **Step 2: 差异记入 NOTES.md**，向用户报告。
- [ ] **Step 3: 用户确认后提交** — `重庆：真网验证记录`
