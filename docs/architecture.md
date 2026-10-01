# 架构

## 分层

- `server.py` 是薄层：只做参数传递与异常包装，业务逻辑、第三方代码 import 一律不进这层。
- `adapters/`：每座城市一个模块，实现 `search_books` / `get_holdings` / `get_book_detail` 三个原语，返回结构对齐 `base.py` 的 TypedDict（由契约测试强制）。新增城市 = 新适配器模块 + `adapters/__init__.py` 的 `_ADAPTERS` 注册一行，server 和 tool 接口不动。
- `interlib/`：图创 Interlib 家族共享模块（广州、杭州共用，详见 [data-sources.md](data-sources.md)）。
- `vendor/`：第三方项目代码，一个组件一个子目录，各保留原始 LICENSE。

## 契约测试与 `_client` 形态

`tests/test_adapter_contract.py` 遍历 `_ADAPTERS` 校验所有适配器的输出结构（字段名、类型、缺字段直接红）。它通过 monkeypatch 替换适配器**模块级 `_client`**（上海 vendor 客户端形态，方法为 `search`/`get_holdings`/`get_return_date`/`get_book_detail`）注入假数据，因此：

- 适配器的公开原语必须经由模块级 `_client` 取数，**不能直连底层函数**——否则 mock 落空，测试会真打图书馆网站。
- `_client` 返回的 attribute 对象（`record_id`/`is_available()`/`item_id` 等）是各适配器与上海 vendor 之间的形态契约。
- 注意命名映射：Interlib 家族 TypedDict 用 `book_id`，契约形态用 `record_id`，映射发生在各适配器 `_Client.search` 内。此处曾出真网故障（单测全绿、冒烟即炸），适配器委托测试必须覆盖**非空 books** 的转换。

## 测试约定

- `uv run pytest`。单测必须 mock 外部依赖，**不打真实图书馆网站**。
- 解析测试打 `tests/fixtures/<city>/` 的实抓 fixture；真网验证走手工 smoke，不进测试套件。
- 抓 fixture 是开发期一次性动作：只读 GET，重试容忍偶发 TLS 重置；字段侦察结论写同目录 `NOTES.md`，解析器以它为准。

## vendor 与 NOTICE

根 [NOTICE](../NOTICE) 是所有第三方组件的唯一事实来源——每个组件一整块，记录主页、许可证、位置、变更：

- 新增组件：放入 `vendor/` 后在 NOTICE 追加一块。
- 修改 vendored 代码：在对应组件块的"变更"里补一条。
- 不在 vendor 目录里放单独的 NOTICE；README 致谢只点到为止，细节一律指向 NOTICE。

## 开发环境

- uv 管理。PyPI 直连不通时用镜像：`uv sync --default-index https://pypi.tuna.tsinghua.edu.cn/simple`。
- 调试 MCP：`uv run fastmcp dev src/mcp_library_search/server.py`（带 inspect 界面）。
