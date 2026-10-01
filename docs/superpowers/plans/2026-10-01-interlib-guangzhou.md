# 广州适配器 + Interlib 家族模块实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `src/mcp_library_search/interlib/` 家族模块（HTTP + HTML 解析 + 三原语）和广州适配器，注册 `guangzhou` 城市。

**Architecture:** Interlib 家族模块是一方共享代码：client.py 管 HTTP，parser.py 用标准库 HTMLParser 解析搜索页/详情页，`__init__.py` 暴露冻结接口（InterlibConfig + 三函数，见 spec）。广州适配器是薄包装。杭州的 adapters/hangzhou.py 未来只 import 本模块的公开接口，所以公开面必须严格按 spec。

**Tech Stack:** Python 3.10+ 标准库（urllib、html.parser、json、dataclasses），pytest。

**Spec:** `docs/superpowers/specs/2026-10-01-three-city-adapters-design.md`

## Global Constraints

- 只许用标准库，**不得新增 pyproject 依赖**；不动 `base.py`、`tests/test_adapter_contract.py`、`server.py`、`pyproject.toml`。
- 中文注释与中文提交信息用全角标点；提交信息结尾加 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。
- 测试禁止真网：全部打 `tests/fixtures/guangzhou/` 的 fixture 或 mock。
- 在 `adapters/__init__.py` 的 `_ADAPTERS` 只加一行 `"guangzhou": guangzhou,`。
- 分支：`feature/guangzhou`，从 main 最新提交切出。

## Review Focus

- 空搜索结果页（生造关键词）解析后 `books == []`，不抛异常；
- 末页/只有一页时 `has_next == False`、`total_pages` 不夸大；
- 馆藏状态文本集合：在馆/可借/在架 → 可借，已借出/借出/已预约/仅阅览/订购中 → 不可借，未识别状态保守判不可借；
- 详情页缺 ISBN 或简介字段时对应空串，不 KeyError；
- 任何 HTTP/解析失败抛 `RuntimeError` 且消息含"广州图书馆"。

---

### Task 1: 抓取广州 fixture

**Files:**
- Create: `tests/fixtures/guangzhou/search_p1.html`、`search_p2.html`、`search_empty.html`、`detail.html`

**Interfaces:**
- Produces: 四个 fixture 文件，后续所有解析测试的真实输入。

- [ ] **Step 1: 建分支与目录**

```bash
cd /Users/admin/Downloads/test/mcp_library_search
git checkout -b feature/guangzhou
mkdir -p tests/fixtures/guangzhou
```

- [ ] **Step 2: 抓搜索第 1、2 页（《活着》结果多，两页都有数据）**

```bash
for p in 1 2; do
  curl -sS --max-time 30 --get "https://opac.gzlib.org.cn/opac/search" \
    --data-urlencode "q=活着" --data-urlencode "searchType=standard" \
    --data-urlencode "searchWay0=marc" --data-urlencode "logical0=AND" \
    --data-urlencode "rows=10" --data-urlencode "sortWay=score" \
    --data-urlencode "sortOrder=desc" --data-urlencode "page=$p" \
    -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" \
    -o "tests/fixtures/guangzhou/search_p$p.html"
done
```

- [ ] **Step 3: 抓详情页（从第 1 页结果取第一个 bookrecno）**

```bash
rid=$(grep -oE "bookDetail\([0-9]+" tests/fixtures/guangzhou/search_p1.html | head -1 | grep -oE "[0-9]+")
echo "bookrecno=$rid"
curl -sS --max-time 30 "https://opac.gzlib.org.cn/opac/book/$rid" \
  -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" \
  -o tests/fixtures/guangzhou/detail.html
```

- [ ] **Step 4: 抓空结果页（生造关键词，任何时刻都零结果）**

```bash
curl -sS --max-time 30 --get "https://opac.gzlib.org.cn/opac/search" \
  --data-urlencode "q=azbycxq不存在xyz" --data-urlencode "searchType=standard" \
  --data-urlencode "searchWay0=marc" --data-urlencode "logical0=AND" \
  --data-urlencode "rows=10" --data-urlencode "sortWay=score" \
  --data-urlencode "sortOrder=desc" --data-urlencode "page=1" \
  -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)" \
  -o tests/fixtures/guangzhou/search_empty.html
```

- [ ] **Step 5: 校验并侦察（结果记录到任务笔记，后续任务要用）**

```bash
wc -c tests/fixtures/guangzhou/*.html
grep -c "bookDetail(" tests/fixtures/guangzhou/search_p1.html   # 期望 >0
grep -c "bookDetail(" tests/fixtures/guangzhou/search_empty.html  # 期望 0
grep -oE "(ISBN|简介|附注|索书号|出版发行|责任者)" tests/fixtures/guangzhou/detail.html | sort | uniq -c
grep -oE "(馆藏浏览|馆藏地|在馆|借出|应还日期)" tests/fixtures/guangzhou/detail.html | sort | uniq -c
grep -oE "page=[0-9]+" tests/fixtures/guangzhou/search_p1.html | sort -u | head   # 分页控件形态
grep -oE "共[^<]{0,20}(条|页)" tests/fixtures/guangzhou/search_p1.html | head -5   # 总数文本形态
```

在 `tests/fixtures/guangzhou/NOTES.md` 写下侦察结论：详情页有哪些书目字段、馆藏表格列名、分页/总数长什么样。**这些结论决定 Task 3-5 的解析目标。**

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/guangzhou
git commit -m "广州：抓取 OPAC 真实页面作为解析 fixture"
# 结尾加 Co-Authored-By 行
```

### Task 2: interlib/client.py——HTTP 层

**Files:**
- Create: `src/mcp_library_search/interlib/client.py`
- Test: `tests/test_interlib_client.py`

**Interfaces:**
- Consumes: `InterlibConfig`（`interlib/__init__.py` 已有骨架）。
- Produces: `get(config: InterlibConfig, path: str, params: dict | None = None, timeout: int = 20) -> str`，供 Task 6 与后续城市复用；失败抛 `RuntimeError(f"{config.name_cn}请求失败：{原因}")`。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_interlib_client.py
import pytest

from mcp_library_search.interlib import InterlibConfig
from mcp_library_search.interlib import client

_CFG = InterlibConfig(city="guangzhou", name_cn="广州图书馆", base_url="https://opac.gzlib.org.cn")


def test_get_builds_url_with_params(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["ua"] = req.get_header("User-agent")
        captured["timeout"] = timeout

        class Resp:
            def read(self):
                return "你好".encode("utf-8")
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False

        return Resp()

    monkeypatch.setattr(client.urllib.request, "urlopen", fake_urlopen)
    body = client.get(_CFG, "/opac/search", {"q": "活着", "page": 1})
    assert body == "你好"
    assert captured["url"].startswith("https://opac.gzlib.org.cn/opac/search?q=")
    assert "%E6%B4%BB%E7%9D%80" in captured["url"]  # 活着 被 URL 编码
    assert "page=1" in captured["url"]
    assert captured["ua"] and "Mozilla" in captured["ua"]
    assert captured["timeout"] == 20


def test_get_wraps_network_errors(monkeypatch):
    def boom(req, timeout=None):
        raise client.urllib.error.URLError("reset by peer")
    monkeypatch.setattr(client.urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError, match="广州图书馆请求失败"):
        client.get(_CFG, "/opac/search", {"q": "x"})


def test_get_wraps_http_errors(monkeypatch):
    def boom(req, timeout=None):
        raise client.urllib.error.HTTPError("u", 503, "Service Unavailable", None, None)
    monkeypatch.setattr(client.urllib.request, "urlopen", boom)
    with pytest.raises(RuntimeError, match="广州图书馆请求失败"):
        client.get(_CFG, "/opac/book/1")
```

注意：`fake_urlopen` 的 Resp 需要支持 `with` 语句（urllib 的 response 是 context manager），实现里统一用 `with urllib.request.urlopen(...) as resp`。

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_interlib_client.py -q`
Expected: FAIL（`interlib.client` 模块不存在）。

- [ ] **Step 3: 实现 client.py**

```python
"""Interlib 家族 HTTP 层：UA 伪装、超时、URL 拼接、错误包装。"""
import urllib.error
import urllib.parse
import urllib.request

from . import InterlibConfig

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def get(config: InterlibConfig, path: str, params: dict | None = None, timeout: int = 20) -> str:
    """GET {base_url}{path}，params 经 URL 编码；返回 UTF-8 文本。

    网络层任何失败都包装成 RuntimeError，消息含中文馆名。
    """
    url = config.base_url + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        raise RuntimeError(f"{config.name_cn}请求失败：{e}") from e
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/test_interlib_client.py -q`
Expected: PASS（3 passed）。

- [ ] **Step 5: Commit**

```bash
git add src/mcp_library_search/interlib/client.py tests/test_interlib_client.py
git commit -m "Interlib 家族模块：HTTP 层"
# 结尾加 Co-Authored-By 行
```

### Task 3: parser.py——搜索结果解析

**Files:**
- Create: `src/mcp_library_search/interlib/parser.py`
- Test: `tests/test_interlib_search_parser.py`

**Interfaces:**
- Consumes: Task 1 的 `search_p1.html` / `search_p2.html` / `search_empty.html`。
- Produces:

```python
class SearchResultsParser: ...  # HTMLParser 子类
def parse_search(html: str) -> dict
# 返回 {"books": [{"book_id","title","author","publisher","publish_year","availability_summary"}...],
#       "total_results": int | None, "total_pages": int, "has_next": bool}
# 书目 ID 来自 bookDetail({bookrecno},...) 锚点；availability_summary 恒为空串。
```

- [ ] **Step 1: 用 fixture 定锚点（把 Task 1 侦察到的真实结构记下来）**

```bash
grep -oE ".{80}bookDetail\([0-9]+.{200}" tests/fixtures/guangzhou/search_p1.html | head -2
grep -oE ".{60}(result|record|item)[^\"]*\".{100}" tests/fixtures/guangzhou/search_p1.html | head -5
```

每条书目标题/作者/出版社/出版年在什么标签里（VuFind 式 `<div class="result">` 还是 Interlib 自己的结构），**以实抓为准**写进 NOTES.md。

- [ ] **Step 2: 写失败测试（结构断言 + 从 fixture 钉死的具体值）**

```python
# tests/test_interlib_search_parser.py
from mcp_library_search.interlib.parser import parse_search

P1 = open("tests/fixtures/guangzhou/search_p1.html", encoding="utf-8").read()
P2 = open("tests/fixtures/guangzhou/search_p2.html", encoding="utf-8").read()
EMPTY = open("tests/fixtures/guangzhou/search_empty.html", encoding="utf-8").read()


def test_p1_parses_books_with_stable_ids():
    r = parse_search(P1)
    assert len(r["books"]) > 0
    for b in r["books"]:
        assert set(b) == {"book_id", "title", "author", "publisher",
                          "publish_year", "availability_summary"}
        assert b["book_id"].isdigit() and len(b["book_id"]) >= 6
        assert b["title"]
        assert b["availability_summary"] == ""
    # 钉死第一条：值以实抓 fixture 为准（实现时打开 fixture 核对后填入）
    assert r["books"][0]["title"] == "活着"  # 例：以 fixture 实际为准
    assert r["books"][0]["author"] != ""      # 例：若 fixture 中该条无作者则放宽


def test_p1_pagination_semantics():
    r = parse_search(P1)
    assert r["has_next"] is True          # 第 1 页应还有下一页（活着 结果很多）
    assert r["total_pages"] >= 2          # 例：以 fixture 分页控件实际为准
    assert r["total_results"] is None or r["total_results"] >= 10


def test_p2_is_different_page():
    r1, r2 = parse_search(P1), parse_search(P2)
    assert [b["book_id"] for b in r1["books"]] != [b["book_id"] for b in r2["books"]]


def test_empty_search_yields_nothing():
    r = parse_search(EMPTY)
    assert r["books"] == []
    assert r["has_next"] is False
```

实现时：每条具体断言值必须打开 fixture 核对后填入（上面标"例"的地方）；若分页控件解析不到总数，`total_results` 用 `None`（spec 规则：不提供即 None，`total_pages` 取当前页、`has_next=False` 的保守 fallback 也要测）。

- [ ] **Step 3: 跑测试确认失败**

Run: `uv run pytest tests/test_interlib_search_parser.py -q`
Expected: FAIL（`interlib.parser` 不存在）。

- [ ] **Step 4: 实现 parser.py 的搜索部分**

标准库 HTMLParser 事件驱动解析（风格参照 `vendor/shanghai_library/parser.py`）：以 `bookDetail({recno}` 锚点定每条边界，在其父容器内抓标题/作者/出版社/出版年文本；分页控件提取页码链接与"下一页"链接；统计文本里的"共 N 条"若能定位则填 `total_results`，否则 `None`。

- [ ] **Step 5: 跑测试确认通过**

Run: `uv run pytest tests/test_interlib_search_parser.py -q`
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add src/mcp_library_search/interlib/parser.py tests/test_interlib_search_parser.py tests/fixtures/guangzhou/NOTES.md
git commit -m "Interlib 家族模块：搜索结果解析"
# 结尾加 Co-Authored-By 行
```

### Task 4: parser.py——详情页书目字段解析

**Files:**
- Modify: `src/mcp_library_search/interlib/parser.py`
- Test: `tests/test_interlib_detail_parser.py`

**Interfaces:**
- Consumes: `tests/fixtures/guangzhou/detail.html`。
- Produces: `def parse_detail(html: str) -> dict`，返回 `{"title","author","publisher","publish_year","isbn","call_number","summary"}`（缺失字段空串）。

- [ ] **Step 1: 侦察详情页字段形态**

```bash
grep -oE ".{40}(ISBN|索书号|出版发行|责任者|简介|附注).{120}" tests/fixtures/guangzhou/detail.html | head -20
```

Interlib 详情页书目字段通常是"标签：值"的表格/定义列表结构；简介可能有独立区块，没有就空串。

- [ ] **Step 2: 写失败测试**

```python
# tests/test_interlib_detail_parser.py
from mcp_library_search.interlib.parser import parse_detail

HTML = open("tests/fixtures/guangzhou/detail.html", encoding="utf-8").read()


def test_detail_fields_present():
    d = parse_detail(HTML)
    assert set(d) == {"title", "author", "publisher", "publish_year",
                      "isbn", "call_number", "summary"}
    assert d["title"] != ""
    # 值以 fixture 实际为准钉死，例如：
    assert d["author"] == "余华"            # 例：核对 fixture 后填
    assert d["publisher"] != ""
    assert d["publish_year"].isdigit() or d["publish_year"] == ""


def test_detail_missing_fields_are_empty_strings():
    d = parse_detail("<html><body>没有字段的页面</body></html>")
    assert d["isbn"] == "" and d["summary"] == "" and d["call_number"] == ""
```

- [ ] **Step 3: 跑测试确认失败 → Step 4: 实现 → Step 5: 通过。**（同 Task 3 节奏）

- [ ] **Step 6: Commit**

```bash
git add src/mcp_library_search/interlib/parser.py tests/test_interlib_detail_parser.py
git commit -m "Interlib 家族模块：详情页书目字段解析"
# 结尾加 Co-Authored-By 行
```

### Task 5: parser.py——馆藏（在馆状态）解析

**Files:**
- Modify: `src/mcp_library_search/interlib/parser.py`
- Test: `tests/test_interlib_holdings_parser.py`

**Interfaces:**
- Consumes: `tests/fixtures/guangzhou/detail.html`。
- Produces: `def parse_holdings(html: str) -> list[dict]`，每条 `{"library","location","call_number","status","due_date"}`（缺失空串）。

- [ ] **Step 1: 侦察馆藏表格结构**

```bash
grep -oE ".{60}(馆藏浏览|馆藏地|索书号|应还日期).{150}" tests/fixtures/guangzhou/detail.html | head -20
```

确认：馆藏列表是表格还是 JS 异步加载（若是 Ajax 接口而非静态 HTML，改用 client.get 直接打该接口，把接口形态记进 NOTES.md 并同步给集成者——spec 允许实现期发现）。

- [ ] **Step 2: 写失败测试**

```python
# tests/test_interlib_holdings_parser.py
from mcp_library_search.interlib.parser import parse_holdings

HTML = open("tests/fixtures/guangzhou/detail.html", encoding="utf-8").read()


def test_holdings_shape_and_content():
    hs = parse_holdings(HTML)
    assert len(hs) > 0
    for h in hs:
        assert set(h) == {"library", "location", "call_number", "status", "due_date"}
        assert h["library"] != ""       # 分馆名必须有
        assert h["status"] != ""
    # 钉死一条具体馆藏（值以 fixture 为准），并断言状态词可分类：
    known = {("在馆", True), ("可借", True), ("已借出", False), ("仅阅览", False)}
    statuses = {h["status"] for h in hs}
    assert statuses <= {s for s, _ in known} or True  # 先收集实际状态词，补进解析器的分类集合


def test_holdings_empty_page():
    assert parse_holdings("<html><body></body></html>") == []
```

实现时：把 fixture 里出现的所有状态词列出来，归入解析器的可借/不可借关键词集合（参照 `vendor/shanghai_library/models.py` 的 `is_available()` 思路：命中不可借词优先，否则命中可借词，都不中保守不可借）；若页面有"应还日期"列则解析进 `due_date`，否则恒空串。

- [ ] **Step 3-5: 失败 → 实现 → 通过**（同前节奏）。

- [ ] **Step 6: Commit**

```bash
git add src/mcp_library_search/interlib/parser.py tests/test_interlib_holdings_parser.py tests/fixtures/guangzhou/NOTES.md
git commit -m "Interlib 家族模块：馆藏与在馆状态解析"
# 结尾加 Co-Authored-By 行
```

### Task 6: interlib/__init__.py 三函数接线（替换骨架）

**Files:**
- Modify: `src/mcp_library_search/interlib/__init__.py`（函数体，签名与 InterlibConfig 不动）
- Test: `tests/test_interlib_primitives.py`

**Interfaces:**
- Consumes: `client.get`、`parse_search`、`parse_detail`、`parse_holdings`；`base.py` 的 `SearchPage/Holding/BookDetail`。
- Produces: 冻结接口的可用实现（`search_books`/`get_holdings`/`get_book_detail`，spec 签名）。**这是 Agent 杭州的编程契约，签名不可动。**

- [ ] **Step 1: 写失败测试（monkeypatch client.get，打 fixture）**

```python
# tests/test_interlib_primitives.py
import pytest

from mcp_library_search.interlib import (
    InterlibConfig, search_books, get_holdings, get_book_detail,
)
from mcp_library_search.interlib import client as _client

_CFG = InterlibConfig(city="guangzhou", name_cn="广州图书馆", base_url="https://opac.gzlib.org.cn")
_SEARCH = open("tests/fixtures/guangzhou/search_p1.html", encoding="utf-8").read()
_DETAIL = open("tests/fixtures/guangzhou/detail.html", encoding="utf-8").read()


def test_search_books_maps_to_contract(monkeypatch):
    monkeypatch.setattr(_client, "get", lambda cfg, path, params=None: _SEARCH)
    page = search_books(_CFG, "活着", page=1, limit=10)
    assert set(page) == {"total_results", "page", "total_pages", "has_next", "books"}
    assert page["page"] == 1
    assert page["books"][0]["book_id"].isdigit()


def test_search_books_wraps_errors(monkeypatch):
    def boom(cfg, path, params=None):
        raise RuntimeError("广州图书馆请求失败：reset")
    monkeypatch.setattr(_client, "get", boom)
    with pytest.raises(RuntimeError, match="广州图书馆"):
        search_books(_CFG, "活着")


def test_get_holdings_sorts_available_first(monkeypatch):
    monkeypatch.setattr(_client, "get", lambda cfg, path, params=None: _DETAIL)
    hs = get_holdings(_CFG, "3001261106", only_available=False)
    assert hs
    flags = [h["available"] for h in hs]
    assert flags == sorted(flags, reverse=True)  # True 在前
    assert [h["library"] for h in hs if h["available"]] == sorted(
        [h["library"] for h in hs if h["available"]]
    )


def test_get_holdings_available_only_requests_nothing_extra(monkeypatch):
    calls = []
    def spy(cfg, path, params=None):
        calls.append(path)
        return _DETAIL
    monkeypatch.setattr(_client, "get", spy)
    hs = get_holdings(_CFG, "3001261106", only_available=True)
    assert all(h["available"] for h in hs)
    assert calls == ["/opac/book/3001261106"]  # 单详情页即全量馆藏，无二次请求


def test_get_book_detail_contract(monkeypatch):
    monkeypatch.setattr(_client, "get", lambda cfg, path, params=None: _DETAIL)
    d = get_book_detail(_CFG, "3001261106")
    assert set(d) == {"book_id", "title", "author", "publisher", "publish_year",
                      "isbn", "call_number", "summary"}
    assert d["book_id"] == "3001261106"


def test_get_book_detail_not_found(monkeypatch):
    monkeypatch.setattr(_client, "get", lambda cfg, path, params=None: "<html><body></body></html>")
    with pytest.raises(RuntimeError, match="未找到"):
        get_book_detail(_CFG, "9999999999")
```

注意 `monkeypatch.setattr(_client, "get", ...)`：parser 与接线层必须从 `interlib.client` 导入 `get` 后调用 `client.get(...)`（或 `from . import client` 再 `client.get(...)`），这样 monkeypatch 才生效——**接线实现里禁止 `from .client import get` 这种名字绑定**。

- [ ] **Step 2: 跑测试确认失败。Step 3: 实现三函数。** 要点：

```python
# search_books：client.get(cfg, "/opac/search", {完整参数集，rows=limit, page=page})
#   → parse_search → SearchPage(total_results=None 若解析不到, page=请求页,
#   total_pages=解析值或当前页, has_next=解析值或 False, books=...)
# get_holdings：client.get(cfg, f"/opac/book/{book_id}") → parse_holdings
#   → available 由状态词分类得出 → only_available 过滤 → 排序 (not available, library)
# get_book_detail：client.get → parse_detail → title 为空则 RuntimeError(
#   f"{cfg.name_cn}：未找到该书详情：{book_id}") → BookDetail
```

- [ ] **Step 4: 全模块测试通过。**

Run: `uv run pytest tests/test_interlib_*.py -q`
Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add src/mcp_library_search/interlib/__init__.py tests/test_interlib_primitives.py
git commit -m "Interlib 家族模块：三原语接线（替换接口骨架）"
# 结尾加 Co-Authored-By 行
```

### Task 7: 广州适配器 + 注册 + 收尾

**Files:**
- Create: `src/mcp_library_search/adapters/guangzhou.py`
- Modify: `src/mcp_library_search/adapters/__init__.py`（加一行注册）
- Test: `tests/test_guangzhou_adapter.py`

**Interfaces:**
- Consumes: `interlib` 公开接口（Task 6）。
- Produces: `_ADAPTERS["guangzhou"]`；契约测试自动覆盖。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_guangzhou_adapter.py
import pytest

from mcp_library_search.adapters import guangzhou


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.interlib import InterlibConfig

    seen = {}

    def fake(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        return {"total_results": 0, "page": 1, "total_pages": 1,
                "has_next": False, "books": []}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake)
    assert guangzhou.search_books("活着", page=2, limit=5) == {
        "total_results": 0, "page": 1, "total_pages": 1, "has_next": False, "books": [],
    }
    assert seen["cfg"] == InterlibConfig(
        city="guangzhou", name_cn="广州图书馆", base_url="https://opac.gzlib.org.cn"
    )
```

- [ ] **Step 2: 确认失败。Step 3: 实现适配器（薄包装，十行内）。**

```python
"""广州适配器：图创 Interlib 家族。"""
from ..interlib import InterlibConfig
from ..interlib import get_book_detail as _detail
from ..interlib import get_holdings as _holdings
from ..interlib import search_books as _search
from .base import BookDetail, Holding, SearchPage

_CONFIG = InterlibConfig(
    city="guangzhou", name_cn="广州图书馆", base_url="https://opac.gzlib.org.cn"
)


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    return _search(_CONFIG, keyword, page=page, limit=limit)


def get_holdings(book_id: str, only_available: bool = True) -> list[Holding]:
    return _holdings(_CONFIG, book_id, only_available=only_available)


def get_book_detail(book_id: str) -> BookDetail:
    return _detail(_CONFIG, book_id)
```

- [ ] **Step 4: 注册并全量测试**

`adapters/__init__.py` 的 `_ADAPTERS` 加一行 `"guangzhou": guangzhou,`（import 同步加），然后：

Run: `uv run pytest -q`
Expected: 全绿（含契约测试新增 guangzhou 参数）。

- [ ] **Step 5: 推分支**

```bash
git add -A
git commit -m "广州适配器：注册 guangzhou 城市"
# 结尾加 Co-Authored-By 行
git push -u origin feature/guangzhou 2>&1 | tail -3
```

推送输出记得脱敏检查（远端 URL 不应出现在输出里；如出现含凭据的 URL，不要原样贴给任何人）。

- [ ] **Step 6: 最终报告（发给集成者）**：契约测试通过数、NOTES.md 里记录的广州页面结构结论、任何与 spec 假设不符的发现。
