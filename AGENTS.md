# AGENTS.md

给在本仓库工作的 AI 编码助手和贡献者的指南。面向使用者的文档见 [README.md](README.md)。

## 架构约束（改代码前必读）

- `server.py` 是薄层：只做参数传递和异常包装。业务逻辑、对方代码的 import 一律不进这一层。
- 对方代码只允许在 `adapters/` 和 `vendor/` 中出现。适配层把对方接口收敛成干净函数，返回给 LLM 的字段在适配层裁剪，不透传原始 dataclass。
- 新增一座城市 = `adapters/<city>.py` 实现 `search_books` / `get_holdings` / `get_book_detail` 三个原语（返回结构对齐 `base.py` 的 TypedDict，由 `tests/test_adapter_contract.py` 强制校验），再在 `adapters/__init__.py` 的 `_ADAPTERS` 注册一行。server 和 tool 接口不动，README 的支持情况表加一行。

## vendor 目录（`src/mcp_library_search/vendor/`）

收录第三方项目代码（vendored），一个组件一个子目录，各目录保留其原始 LICENSE。

**NOTICE 约定**：根目录的 [NOTICE](NOTICE) 是所有第三方组件的唯一事实来源——每个组件一整块，记录主页、许可证、位置、变更。

- 新增组件：除放入 vendor/ 外，必须在 NOTICE 追加一块。
- 本地修改 vendored 代码：必须在 NOTICE 对应组件块的"变更"里补一条。
- 不要在 vendor 目录里放单独的 NOTICE 文件；README 致谢只点到为止，细节一律指向 NOTICE。

当前组件：shanghai-library-book-search-python（[仓库](https://github.com/ZedeX/shanghai-library-book-search-python)，Apache-2.0，位于 `vendor/shanghai_library/`）。

- 保持原样，bug 优先提给上游。
- 上游是平铺 import，已改为包内相对导入（仅 `library_client.py` 三行）；**同步上游（覆盖同名文件）后必须重新应用相对导入修改**，否则包无法导入。同步后记得在 NOTICE 的变更里记一笔。
- 检索总条数：站点统计区已不再输出该信息（`total_results` 恒为 0），adapter 按"0 且当前页有结果 → 视为未知（null）"处理，不属于代码 bug。
- 图书简介：站点没有独立简介区块，内容简介以书目"附注"字段（MARC 500）形式给出，vendor 补丁将 summary 回退到附注（见 NOTICE 变更）。
- 预计归还时间：馆藏页不直接渲染归还日期，已借出馆藏的 `<a class="item-return-date">` 只带单册 `data-itemid`，需按条调用 `AJAX/JSON?method=itemReturnDate` 接口（vendor 提供 `get_return_date`，adapter 负责逐个补 `due_date`）。
- 本地补丁：`parser.py` 解析 has_next（下一页链接）、`library_client.py` 的 statistics 附带 has_next（见 NOTICE 变更）。同步上游覆盖文件后，检查这些补丁是否仍需重新应用。

## 测试

- `uv run pytest`。单测必须 mock 外部依赖，**不打真实图书馆网站**。
- 真网验证走手工 smoke，不进测试套件。

## 开发环境

- uv 管理。PyPI 不通时用镜像：`uv sync --default-index https://pypi.tuna.tsinghua.edu.cn/simple`。
- 调试 MCP：`uv run fastmcp dev src/mcp_library_search/server.py`（带 inspect 界面）。

## 发布

- 入口是 console script `mcp_library_search`（定义在 pyproject 的 `[project.scripts]`，转发到 `server:main`）。改动入口要同步检查 README 里的 uvx 用法。
- `uv build && uv publish`（需 PyPI token）。发布后 `uvx mcp_library_search` 生效。
- 改了 tool 的名称/参数/描述，同步更新 README 的 tool 表。
