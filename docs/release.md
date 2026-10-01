# 发布

- 入口是 console script `mcp_library_search`（pyproject 的 `[project.scripts]`，转发到 `server:main`）；改动入口要同步检查 README 里的 uvx 用法。
- 发布走 GitHub Actions 可信发布（`.github/workflows/release.yml`，OIDC，仓库里不存任何 PyPI token）。
- 流程：pyproject 的 `version` bump → 提交 → 打 `v<版本>` tag 推送 GitHub，tag 触发：测试 → 校验 tag 与版本号一致（不一致拒绝发布）→ `uv build` → 发布 PyPI。
- PyPI 侧一次性配置：项目页 Settings → Publishing → Add trusted publisher，Owner=`cnderrick`、Repository=`mcp_library_search`、Workflow=`release.yml`、**Environment name 留空**（workflow 未声明 environment，填了会 OIDC 校验失败）。
- workflow 里的 action 全部钉死 commit SHA（防 tag 劫持）；升级 action 时同步钉新 SHA。
- 发布后 `uvx mcp_library_search` 即装即用（项目页：https://pypi.org/project/mcp-library-search/ ）。注意镜像同步延迟：本机走清华源验证要加 `--default-index https://pypi.tuna.tsinghua.edu.cn/simple`，发布后等几分钟到几小时才能按名字装上。
- 同版本号不可重复上传（有问题只能 yank 后发新版）；首传后包名永久占位。
- 改了 tool 的名称/参数/描述，同步更新 README 的 tool 表。
