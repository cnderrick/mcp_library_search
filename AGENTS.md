# AGENTS.md

给在本仓库工作的 AI 编码助手和贡献者的指南。面向使用者的文档见 [README.md](README.md)。

## 文件地图

| 文件 | 内容 |
|---|---|
| [docs/architecture.md](docs/architecture.md) | 分层架构、契约测试与 `_client` 形态约定、测试与 vendor/NOTICE 约定、开发环境 |
| [docs/data-sources/README.md](docs/data-sources/README.md) | 数据源总目录（按国家／地区分卷，总目录解释分卷关系与登记约定）；已接入城市的入口、技术组件、quirks 见分卷 cn.md，新城市先登记 |
| [docs/release.md](docs/release.md) | 发布流程：tag 触发 CI/CD 可信发布到 PyPI |
| [NOTICE](NOTICE) | 第三方组件的唯一事实来源（许可、归属、本地变更），vendor 目录内不放单独 NOTICE |
| `tests/fixtures/<city>/NOTES.md` | 各城市实抓 fixture 的字段侦察结论，解析器以它为准 |

## 铁律

1. `server.py` 是薄层：业务逻辑只进 `adapters/`、`interlib/`、`vendor/`。
2. 单测不打真实图书馆网站；契约测试的模块级 `_client` 是适配器形态的硬契约。
3. 中文注释与中文提交信息用全角标点。
