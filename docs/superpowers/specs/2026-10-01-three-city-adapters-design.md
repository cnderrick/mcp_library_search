# 三城适配器设计：广州、杭州（Interlib 家族）、深圳

日期：2026-10-01
状态：已与项目负责人在对话中确认（分支隔离 + 整体合流发版）

## 背景与目标

mcp_library_search 已接入上海（VuFind，vendored 第三方爬虫）。调研与境内实测确认：

- 广州图书馆、杭州图书馆同为**图创 Interlib 系统**，URL 结构同构，可共享一个参数化家族模块；
- 深圳图书馆为自研 JSON API（"图书馆之城"统一平台，167 馆），免登录、无验证码，三个端点覆盖全部需求。

目标：新增 `guangzhou` / `hangzhou` / `shenzhen` 三个城市适配器，全部通过契约测试与真网冒烟。

成功标准：

1. 三城 `search_books` / `find_book_availability` / `get_book_detail` 真网冒烟通过（含分页、馆藏状态、深圳应还日期）；
2. `tests/test_adapter_contract.py` 自动覆盖三城（注册即校验）；
3. README 支持情况表加三行，发布 0.2.0。

## 架构

```
server.py（不动）
adapters/__init__.py（各 agent 加一行注册，冲突由集成者合流时解决）
adapters/guangzhou.py ─┐
adapters/hangzhou.py ──┤──▶ interlib/（家族模块，一方代码，不放 vendor/）
adapters/shenzhen.py ──┴──────（独立，不依赖家族模块）
```

vendor/ 只收第三方代码（NOTICE 约定），家族模块是一方代码，位于 `src/mcp_library_search/interlib/`。

### 家族模块对外接口（Agent 杭州的编程契约，冻结）

```python
# src/mcp_library_search/interlib/__init__.py 导出：

@dataclass(frozen=True)
class InterlibConfig:
    city: str       # 城市标识，如 "guangzhou"
    name_cn: str    # 报错与文档用的中文名，如 "广州图书馆"
    base_url: str   # 不含末尾斜杠，如 "https://opac.gzlib.org.cn"
    # 城市差异（quirk）只允许以"带默认值的 config 字段"形式新增，
    # 默认值即广州行为；禁止改变下列函数签名。

def search_books(cfg: InterlibConfig, keyword: str, page: int = 1, limit: int = 20) -> SearchPage: ...
def get_holdings(cfg: InterlibConfig, book_id: str, only_available: bool = True) -> list[Holding]: ...
def get_book_detail(cfg: InterlibConfig, book_id: str) -> BookDetail: ...
```

返回类型即 `adapters/base.py` 的 TypedDict，契约不变。家族模块内部自行处理 HTTP、HTML 解析（Python 标准库 HTMLParser，与 vendor 上海代码同风格）、错误转换。杭州若发现非 quirk 字段不可覆盖的差异，不改动家族模块，在最终报告中留"合流 TODO"，由集成者补。

错误约定：三个函数失败时抛 `RuntimeError`，消息含中文馆名与原因（如 `"广州图书馆搜索失败：超时"`）。

### 三城 adapter 形态

- `adapters/guangzhou.py` / `adapters/hangzhou.py`：持有各自 `InterlibConfig`，薄包装调用家族模块三函数；
- `adapters/shenzhen.py`：独立实现，模块内自带轻量 client（JSON API，无 HTML 解析）。

## 已验证数据事实（实现依据）

### Interlib 两城共有

- 搜索：`GET {base}/opac/search`，参数 `q=关键词&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=N`（两城实测 200；广州另支持 `kw=` 简写，不用）；
- 结果页每条书目锚点 `bookDetail({bookrecno},...)`，`bookrecno` 为稳定书目 ID，`book_id = str(bookrecno)`；
- 详情：`GET {base}/opac/book/{bookrecno}`，服务端渲染，含"馆藏浏览"、索书号（`callno`）、分馆、馆藏地点、在馆状态（两城已确认字段存在，DOM 细节由 Agent 广州实抓解析）；
- 免登录、无验证码；分页控件形态由 Agent 广州实抓确认。

### 深圳（www.szlib.org.cn，全部 GET 返回 JSON）

- 公共参数：`client_id=t1`、`v_tablearray=bibliosm,serbibm,apabibibm,mmbibm`；
- 搜索：`/api/opacservice/getQueryResult`，参数 `v_value`、`v_index=title|isbn`、`pageNum`、`v_page`；返回 `data.numFound`（真实总数）与 `data.docs[]`（每条含 `recordid`、`tablename`、`title/author/publisher/publishyear/isbn/callno` 等）；
- 详情+馆藏：`/api/opacservice/getBookDetail`，参数 `metaTable`、`metaId`、`library=all`；返回 `CanLoanBook` / `OnlyReadBook` / `BorrowedBook` 三个分桶，单册含 `barcode`、`callno`、`local`（分馆+室）、`status`（在馆等）、`cirtype`，已借出含 `ReturnDate`；
- `book_id = f"{tablename}:{recordid}"`（详情接口需要 `metaTable`，必须与 recordid 成对携带）；适配器收到 book_id 自行拆分；
- 请求头：浏览器 UA + `Referer: https://www.szlib.org.cn/opac/`；
- 站点偶发 TLS 重置（国庆期间观测到，自愈），开发期重试即可。

## 契约与字段语义（base.py 不变）

- `total_results`：深圳填 `numFound` 真实值；Interlib 两城解析到总数就填，解析不到填 `None`（数据源不提供），不猜；
- `total_pages` / `has_next`：解析不到分页信息时，`total_pages` 取当前页、`has_next=False`（保守），不用 `total_results` 反推；
- `Holding.due_date`：深圳从 `BorrowedBook` 的 `ReturnDate` 填；Interlib 详情页若已借出条目带应还日期则解析，没有留空串；
- 排序统一：可借在前，同按 `library` 升序（Unicode 码位，与上海一致）；
- `only_available=True` 时不发任何额外请求（深圳无二次接口问题；Interlib 单详情页本来就含全量馆藏）。

## 测试策略

- 开发期实抓三城真实页面（只读 GET）存为 fixture（`tests/fixtures/{city}/`），提交进仓库；单测全部打 fixture、mock HTTP，**测试不打真网**（AGENTS.md 铁律）；
- Agent 广州：家族模块解析测试 + 广州 adapter 测试；
- Agent 杭州：杭州 adapter 测试（对家族模块接口 mock 或打 fixture，家族模块实现不在其分支）；
- Agent 深圳：深圳 adapter 测试（JSON fixture）；
- 各分支上契约测试的覆盖：各 agent 自行在 `_ADAPTERS` 注册自己的城市（一行），分支间冲突由集成者合流时解决；
- 真网冒烟：合流后人工执行，不进测试套件。

## 子 agent 分工与文件所有权

**前置步骤（spawn agent 之前，集成者先落 main）**：把家族模块的接口骨架（`interlib/__init__.py`：`InterlibConfig` 冻结 dataclass + 三个函数，函数体抛 `NotImplementedError`）作为独立提交落进 main。Agent 广州在自己的分支把骨架换成真实现；Agent 杭州的适配器从第一天就能 import、能跑测试。

| 分支 | Agent | 可改文件 | 禁改 |
|---|---|---|---|
| `feature/guangzhou` | 广州 | `interlib/**`、`adapters/guangzhou.py`、`tests/test_guangzhou_adapter.py`、`tests/test_interlib_*.py`、fixtures | `base.py`、契约测试、`server.py`、`adapters/__init__.py`（注册行除外） |
| `feature/hangzhou` | 杭州 | `adapters/hangzhou.py`、`tests/test_hangzhou_adapter.py`、fixtures | 同上 + **不动 `interlib/`** |
| `feature/shenzhen` | 深圳 | `adapters/shenzhen.py`、`tests/test_shenzhen_adapter.py`、fixtures | 同上 |

- 三方都不得改 `pyproject.toml`（版本号由集成者在合流时统一 bump 0.2.0）；
- README 支持表、AGENTS.md 架构节、NOTICE（无变更，全为一方代码）由集成者统一更新；
- 合流顺序：guangzhou → hangzhou → shenzhen，逐个 code review 后合入 main；
- **预期现象**：杭州分支上契约测试对 hangzhou 是红的（家族模块还是骨架），合流广州分支后转绿；深圳分支自绿。

## 发布

合流完成 → 三城真网冒烟 → README 加三行 → bump 0.2.0 → `uv build` / `uv publish` → tag `v0.2.0`（流程见 AGENTS.md 发布节）。

## 风险

1. 深圳 API 非官方，可能变更——接受；出错时错误信息会经 server 层透传给调用方；
2. Interlib 两城 DOM 细微差异——quirk config 兜不住时按"合流 TODO"流程处理；
3. 三城站点国庆期间偶发 TLS 重置——开发期重试，不做代码层容错。
