# 三城适配器集成与发布计划（集成者执行）

> 本计划由集成者（主会话）在三城分支完成后顺序执行，非子 agent 任务。

**Goal:** 将 `feature/guangzhou`、`feature/hangzhou`、`feature/shenzhen` 三个分支逐个 review 后合入 main，补齐文档，冒烟，发布 0.2.0。

**Spec:** `docs/superpowers/specs/2026-10-01-three-city-adapters-design.md`

## Global Constraints

- 合流顺序固定：guangzhou → hangzhou → shenzhen（guangzhou 把 `interlib/` 骨架换成实现，hangzhou 才能转绿）。
- 三城契约测试全部转绿后才可冒烟与发版；真网冒烟人工做，不进测试套件。
- 版本号由集成者统一 bump 0.2.0，子 agent 分支不得改 `pyproject.toml`。
- 推送输出脱敏（远端 URL 含 PAT，不原样贴出）。

---

- [ ] **1. Review feature/guangzhou**

```bash
cd /Users/admin/Downloads/test/mcp_library_search
git fetch origin
git diff main...origin/feature/guangzhou --stat
git diff main...origin/feature/guangzhou -- src/mcp_library_search/interlib src/mcp_library_search/adapters/guangzhou.py
```

核对：只动了允许的文件；公开接口（`InterlibConfig` + 三函数签名）与 spec 冻结版一致；无新增依赖；`interlib/` 内用的是 `client.get(...)` 这种可 monkeypatch 的调用方式。读 agent 最终报告里的 NOTES 结论。

- [ ] **2. 合并 guangzhou**

```bash
git merge --no-ff origin/feature/guangzhou
uv run pytest -q        # 期望：全绿，契约测试覆盖 guangzhou
```

- [ ] **3. Review + 合并 hangzhou**

```bash
git diff main...origin/feature/hangzhou --stat
git merge --no-ff origin/feature/hangzhou
uv run pytest -q        # 期望：全绿——家族实现已合入，hangzhou 契约测试应转绿
```

若 hangzhou 契约测试仍红：读 agent 的"合流 TODO"，判断是杭州 quirk（加带默认值的 config 字段）还是 agent 遗漏，处理后再验。

- [ ] **4. Review + 合并 shenzhen**

```bash
git diff main...origin/feature/shenzhen --stat
git merge --no-ff origin/feature/shenzhen
uv run pytest -q        # 期望：全绿，契约测试覆盖 shenzhen
```

- [ ] **5. 真网冒烟（人工，三城）**

```bash
uv run python - <<'PY'
from mcp_library_search.adapters import guangzhou, hangzhou, shenzhen
for name, mod, kw in [
    ("广州", guangzhou, "活着"),
    ("杭州", hangzhou, "三体"),
    ("深圳", shenzhen, "活着"),
]:
    page = mod.search_books(kw)
    b = page["books"][0]
    hs = mod.get_holdings(b["book_id"], only_available=False)
    det = mod.get_book_detail(b["book_id"])
    print(f"{name}: 总数={page['total_results']} 首条={b['title'][:20]!r} "
          f"馆藏数={len(hs)} 借出带应还日期={sum(1 for h in hs if h.get('due_date'))}")
PY
```

检查：三城都能搜到书、拿到馆藏、详情非空；深圳借出条目带应还日期；杭州（国庆若不可达则重试）。

- [ ] **6. 文档与版本**

- `README.md` 支持情况表加三行：广州/杭州/深圳 ✅，数据源分别写"广州图书馆（图创 Interlib）"、"杭州图书馆（图创 Interlib）"、"深圳图书馆之城统一平台（自研 JSON API，167 馆）"；
- `AGENTS.md` 架构节补充：新增"系统家族"约定——Interlib 家族模块位于 `src/mcp_library_search/interlib/`，新接入同族城市只写 `adapters/<city>.py` 薄包装 + 注册，不碰家族模块；
- `pyproject.toml` `version` → `0.2.0`。

```bash
git add README.md AGENTS.md pyproject.toml
git commit -m "三城适配器：广州、杭州、深圳 + 文档 + 0.2.0"
```

- [ ] **7. 构建、发布、打 tag**

```bash
rm -rf dist && uv build
UV_PUBLISH_TOKEN="$(cat ~/.config/pypi/mcp_library_search.token)" uv publish
git tag -a v0.2.0 -m "三城适配器：广州、杭州、深圳"
git push origin main v0.2.0
```

（发布流程细节见 AGENTS.md 发布节；PyPI 上传后镜像有同步延迟，本机按名验证要加清华镜像 index。）

- [ ] **8. 清理与收尾**

```bash
git push origin --delete feature/guangzhou feature/hangzhou feature/shenzhen   # 远端分支已合，删除
git branch -d feature/guangzhou feature/hangzhou feature/shenzhen              # 本地分支
```

更新 `tests/fixtures/*/NOTES.md`（若有临时侦察结论）留档。最终向项目负责人汇报：三城冒烟结果、发布版本、剩余风险（深圳 API 非官方、Interlib 两城 DOM 潜在漂移）。
