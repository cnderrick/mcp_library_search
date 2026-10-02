# 津渝合流与 0.3.0 发布实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 天津、重庆两个适配器合入 main：全量回归、文档登记（data-sources.md、README）、版本 0.3.0，走完 tag → CI 可信发布流程。

**Architecture:** 无新代码结构；本计划是收尾：注册核对、文档、版本、发布。

**Tech Stack:** pytest / git / GitHub Actions（发布链路 0.2.0 已验证）。

**Spec:** `docs/superpowers/specs/2026-10-02-tianjin-chongqing-adapters-design.md`

## Global Constraints

- 全角标点、不加 Co-Authored-By；**推送与 tag 必须用户明确发令后执行**（0.2.0 的教训：提交也得用户点头）。
- data-sources.md 总览表省份分组规则沿用：直辖市在前（上海市、北京市、天津市、重庆市），省份在后；省份列只首行填写。
- 版本号同步三处：pyproject.toml、uv.lock（`uv lock` 刷新）、tag `v0.3.0`。

## Review Focus

1. README 支持表加城市时，天津一行要注明「三源合并」（主馆+少儿馆+中新友好），重庆一行注明 InDigLib——读者知情权。
2. data-sources.md 的天津小节是本项目里首个「一城多源」记录，写法会成为以后同类情况的范本。
3. 发布前必须用户本地验证通过（真网抽查两城各一次）。

---

### Task 1: 注册核对与全量回归

**Files:**
- Modify: `src/mcp_library_search/adapters/__init__.py`（若两个适配器计划未完成注册）

- [ ] **Step 1:** 确认 `tianjin`、`chongqing` 均在 `_ADAPTERS`；`uv run pytest -q` 全量绿（含自动扩展的契约测试）。
- [ ] **Step 2:** 向用户报告测试计数（预期既有 77 + 新增），确认后提交 —— `津渝：注册合流与全量回归`

---

### Task 2: 文档登记

**Files:**
- Modify: `docs/data-sources.md`、`README.md`

- [ ] **Step 1: data-sources.md** — 总览表直辖市组插入两行（北京行之后）：

```
| 天津市（直辖市） | 天津 | `tianjin` | http://opacwh.tjl.tj.cn:8991/F 等三个源（见下） | Ex Libris ALEPH ×2 + 图创 Interlib | `adapters/tianjin.py`（三源合并） |
| 重庆市（直辖市） | 重庆 | `chongqing` | http://222.177.237.197:8080/InDigLib/ | InDigLib 集群数字图书馆（Struts2+Solr） | `adapters/chongqing.py`（独立实现） |
```

新增「天津（三源合并）」小节：book_id 前缀与复合 id 规则、ISBN 归并优先级、验证码限频实测值、GBK/会话/set_number 要点、两 ALEPH 并行不通的证据；「重庆（InDigLib）」小节：会话流程、真假端点、select1 词表、单册状态字段结论。

- [ ] **Step 2: README.md** — 支持表加两行；天津行注「主馆+少儿馆+中新友好三源合并」。
- [ ] **Step 3:** 向用户展示文档 diff，确认后提交 —— `文档：登记天津（三源）与重庆（InDigLib）`

---

### Task 3: 版本 0.3.0 与发布

**Files:**
- Modify: `pyproject.toml`、`uv.lock`

- [ ] **Step 1:** pyproject `version = "0.3.0"` → `uv lock` → `uv run pytest -q` → 向用户报告并等待发布指令。
- [ ] **Step 2（用户发令后）:** 提交 `发布 0.3.0`（正文：新增天津三源合并、重庆 InDigLib；全文照 0.2.0 发布提交格式）→ 推 main → 打 `v0.3.0` → 盯 CI（测试 → 版本校验 → 构建 → PyPI，照搬 0.2.0 的轮询验证脚本）。
- [ ] **Step 3:** PyPI JSON 验证 0.3.0 与描述；`uvx` 抽查可装；向用户报告全链路结果。
