# 2026-10-02 批量城市接入·独立验收报告

- **验收对象**：本批未提交改动（工作树内）——6 个新注册标识（jiangyin、wenzhou、taizhou、jinhua、nanjing、hefei）、hangzhou 重构为杭图＋浙图双源合并（含裸数字 book_id 兼容垫片）、interlib/parser.py `_finish_value` 家族缺陷修复、server.py 工具文案与 docs/data-sources.md 登记。
- **验收依据**：docs/data-sources.md（声称行为＝验收标准）＞ tests/fixtures/<city>/NOTES.md ＞ AGENTS.md 铁律。
- **验收环境**：本机工作树，`uv run pytest`（Python 环境由 uv 管理）；真网验收走生产代码路径 `adapters.search_books / get_holdings / get_book_detail`。
- **验收日期**：2026-10-02。验收人：QA（独立于各开发 agent）。

## 总结论：**通过**（附 3 条备注级发现，均不阻塞；详见问题清单）

全量单测独立复跑 329 passed 与开发侧终验基线一致；新增验收钉子 7 条后合计 336 passed、0 failed。tagTr 家族修复经**变异验证**确证三路钉子真实有效且穗杭津既有测试无回归。杭州裸 id 兼容垫片与合肥双源复合 id 均经真网实证。server.py 文案与 data-sources.md 口径逐条一致，重庆保守口径未被改动。单测全部走 fixture/monkeypatch，未发现任何真网调用。

## 逐验收点结论

| # | 验收点 | 步骤 | 预期 | 实际 | 结论 |
|---|---|---|---|---|---|
| 1 | 全量测试复跑 | 工作树内 `uv run pytest -q` | 329 passed（开发侧基线） | **329 passed in 0.62s**，0 failed / 0 error / 0 xfail | ✅ |
| 2 | 契约测试遍历 12 标识 | `pytest --collect-only -q tests/test_adapter_contract.py` 统计参数化 id；`python -c "sorted(_ADAPTERS)"` | chongqing/guangzhou/hangzhou/hefei/jiangyin/jinhua/nanjing/shanghai/shenzhen/taizhou/tianjin/wenzhou 各 3 条契约 | 12 标识 × 3 契约（search/holdings/detail）＝36 条全绿；`_ADAPTERS` 恰为同 12 键 | ✅ |
| 3 | 家族修复无回归 | 核对既有测试存在性与结果：test_interlib_detail_parser.py（广州基准 2 条）、test_hangzhou_compat.py（5 条，git status 证实**零改动**）、test_tianjin_zxyh.py（6 条）、test_interlib_search_parser.py（express_bookrecno 钉在 :24） | 全绿且 compat 文件未被本批触碰 | 全绿；test_hangzhou_compat.py 不在修改清单中，与 data-sources.md「零改动仍绿」声称一致 | ✅ |
| 4 | tagTr 钉子真实断言 | ①读 interlib/parser.py:202-208 确认修复形态（`_finish_value` 内 `self._label = ""` 一对一消费）；②读三路钉子断言体；③**变异验证**：复制仓库到 /tmp/mutrepo，将 206 行还原为缺陷行为，跑三路钉子＋穗杭既有 7 条 | ③路钉子为真实 assert 非 xfail；变异下钉子必须红、穗杭基准必须仍绿（其 fixture 有「次要责任者」行重置从未触发缺陷） | 无 xfail/skip 标记（grep 全空）；变异后**三路钉子全红**（jiangyin author 被污染为「没有标签」、wenzhou call_number 丢失、hefei author 被覆盖），穗杭 7 条仍绿；原工作树未动（parser.py:206 完好，副本已删除） | ✅ |
| 5 | 杭州向后兼容垫片 | 读 test_hangzhou_merge.py：`test_split_bare_numeric_routes_to_hz`（裸数字→HZ，含复合 id 内混入裸成员）、`test_get_holdings_bare_id_routes_hz_only`（裸 id 只触 HZ 不触浙图）、`test_search_merges_and_sums_totals`（`record_id == "HZ:1+ZJ:2"` 搜索输出带前缀） | 垫片与前缀均有单测钉住且绿 | 22 条 merge 测试全绿，断言与 data-sources.md 杭州小节口径逐条对应 | ✅ |
| 6 | 单测不打真网 | grep 全部新增测试文件的 `urlopen/requests./httpx/socket.`（0 命中）；grep `http` 逐条核对（共 5 处：江阴/温州/台州 base_url 字符串断言、南京 mock 调用 URL 断言、浙图节流 key 字符串）；抽读 test_jiangyin_adapter.py / test_nanjing_detail.py 确认 monkeypatch `interlib.search_books` / `nanjing._open` | 所有 http 出现处均为字符串比对或 mock 路由，无实连 | 5 处全部核实为 mock/断言用途；南京走 `_mock_open` spy，江阴走家族原语 monkeypatch | ✅ |
| 7 | server.py 文案与 docs 口径一致 | `git diff src/.../server.py` 核对改动面；逐条对照 data-sources.md | 12 城清单齐全；南京「limit 不生效」、浙图/金华「无应还日期＝数据边界」、南京「call_number 空串」登记；**重庆保守口径未改动** | 全部一致：重庆文案仅句尾「；」改「、」续接枚举，口径原文未动；江阴「农家书屋等 24H 网点」在 data-sources.md 无对应句但有 fixtures/jiangyin/NOTES.md:52-53 libcodeMap 侦察依据（见问题 #3） | ✅ |
| 8 | 真网·杭州（双源） | `search_books('三体', limit=5)` → `get_book_detail(首条)` → `get_holdings(裸数字 id, only_available=False)` | 搜索输出带前缀、total 为双源合计；detail 取优先级成员；裸 id 路由 HZ 可用（0.3.0 线上形态） | total_results=2076、5 条全部 `HZ:` 前缀；detail('HZ:2007002340') 仅 1 请求取 HZ 成员，isbn/索书号/提要齐全；裸 id `2007002340` 返回 43 条馆藏、16 个馆名全为杭州系（杭州图书馆/各区馆/杭少图分馆），**无浙图馆名混入** | ✅ |
| 9 | 真网·合肥（双源） | `search_books('三体', limit=5)` → `get_holdings('AH:1901234449', only_available=False)` | `AH:`/`HF:` 前缀；跨源同 ISBN 合成复合 id；AH 单成员 holdings 可达 | total_results=351；5 条中 4 条 `AH:` 单成员＋1 条**真网复合 id `AH:1901181704+HF:1001460005`**（与 test_hefei_parse 所用 fixture 记录号一致）；AH holdings 5 条「安徽省馆/在馆/available=True」 | ✅ |
| 10 | 真网·江阴（家族零 quirk） | `search_books('三体', limit=3)` | 家族标准行为：裸数字 book_id、真实总数 | total_results=82、首条 `1139334`《三体》导读——与 NOTES.md 侦察及 test_jiangyin_adapter 期望值完全一致 | ✅ |
| 11 | 硬边界自检 | 核对本次验收产生/修改的文件 | 只新建 tests/ 下验收测试与本报告；不改生产代码、不改 data-sources.md、不 commit | 仅新建 `tests/test_acceptance_20261002.py`（7 条，全绿；全套 336 passed）与本报告；变异验证在 /tmp 隔离副本进行且已删除；未执行任何 git 写操作 | ✅ |

## 发现的问题清单（报告为证，均未修改）

1. **【备注】tests/test_jiangyin_adapter.py 顶部 docstring 过期**。
   复现：读该文件 1-5 行——声称「江阴暂未注册进 _ADAPTERS……test_adapter_contract.py 盖不到它」；实际江阴已注册且契约测试已覆盖（本报告验收点 2 实证 3 条契约全绿）。注释性陈述与现状不符，不影响任何行为，建议开发侧下次顺手更新。
2. **【备注·数据漂移记录】data-sources.md 杭州小节的真网实证复合 id 本次未复现**。
   复现：真网 `search_books('hangzhou', '三体', limit=5)`，文档所记 `HZ:2007154111+ZJ:110000014851476` 中的 `HZ:2007154111`（三体：图像小说）本次以单成员形态返回，前 5 条无复合 id。判断：归并按 ISBN 匹配，浙图源侧书目变动即可导致，属上游数据漂移而非合并逻辑缺陷——复合 id 形态本身已由合肥真网（`AH:1901181704+HF:1001460005`）与杭州单测（fixture 钉死）双重实证。不要求改动，仅照实记录。
3. **【备注】server.py 江阴文案「含农家书屋等 24H 网点」未见于 data-sources.md**。
   复现：grep「农家书屋」——仅命中 tests/fixtures/jiangyin/NOTES.md:52-53（libcodeMap 含 njsw=农家书屋、YueCheng24H=月城水韵社区 24H）。文案有侦察依据、与文档不矛盾，但 data-sources.md 江阴小节未提；如需两文档完全同口径可由开发侧补登。

## 真网请求数登记

| 轮次 | 步骤 | 城市/源 | 请求数 |
|---|---|---|---|
| 第 1 轮 | A 搜索（脚本随后因本地 KeyError 中止，非网络失败） | 杭州 HZ＋ZJ | 2 |
| 第 2 轮 | A 搜索 | 杭州 HZ＋ZJ | 2 |
|  | B 详情（单成员 `HZ:`，仅触 HZ） | 杭州 HZ | 1 |
|  | C 馆藏（裸 id 垫片，仅触 HZ） | 杭州 HZ | 1 |
|  | D 搜索 | 合肥 AH＋HF | 2 |
|  | E 馆藏（单成员 `AH:`） | 合肥 AH | 1 |
|  | F 搜索 | 江阴 | 1 |
| **合计** |  | 3 城（含双源城杭州、合肥） | **10 ≤ 12** |

节流合规：脚本每步骤间强制 sleep 2.5 秒；浙图客户端自带 2 秒/host 节流；合肥 HF 源一次通过未触发重试（「三体」非 ISBN 关键词，去连字符重试分支不激活）。全程无 401、无验证码、无封禁迹象，未触发中止条件。

## 新增验收钉子

`tests/test_acceptance_20261002.py`（7 条，全离线）：注册表恰 12 标识、每适配器模块级 `_client` 存在（AGENTS.md 硬契约）、server.py 三个工具 docstring 覆盖全部注册城市且数据边界文案（南京 limit／浙图金华 due_date／重庆保守口径）在位、data-sources.md 以反引号标识登记全部 12 城。任何一侧单独增删城市或改口径即红。
