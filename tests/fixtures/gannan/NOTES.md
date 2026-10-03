# 甘南州图书馆 SirsiDynix iLink 实抓侦察记录

实抓时间：2026-10-03。甘南州图书馆无独立 OPAC，借甘肃省图 iLink 实例
（http://search.gslib.com.cn）按馆别检索；实抓时 `library="甘南馆"`、字段「所有字段」、
短语 `"三体"`。

## 技术组件与 quirk

- 与甘肃省图、陇南市图书馆**共用同一 iLink 实例**，检索/详情/馆藏页与大连同构，
  并入 `ilink/` 家族；城市差异只有一处：检索表单 `library`＝`甘南馆`。
- 会话流、ps token 逐步解析、JUMP 翻页、VIEW^N 详情、索书号级馆藏、节流 ≥4 秒/host
  与家族一致，详见 `tests/fixtures/gansu_prov/NOTES.md`。

## 检索通道

- GET 入口 `/uhtbin/cgisirsi/x/x/0/49/` → POST `searchform` action
  （`searchdata1`/`srchfield1`/`library=甘南馆`/`sort_by=TI`）。
- 实抓 `"三体"` → `检索到 3 题名`，单页（hitlist first_hit=1/last_hit=3）。
- 首条为《三体 刘慈欣著》（catkey 1551269），命中列表页无出版年（原值空串）。

## 详情页与馆藏

- `detail.html`：《三体 刘慈欣著》详情，`copy_info`＝「1 馆藏于 甘南图书馆.」
  → 仅表位置、**无明确在架词**，保守 `status="馆藏于"`、`available=False`；馆藏表 2 复本，
  索书号 `(GNT)I247.5/3084.1`，分馆表头「甘南馆」，第 2 复本带「到期: 2020/10/31」
  （文本落在馆藏位置列，原值照登，不解析成 due_date）。
- 馆藏表为**无 `id` 的甘肃变体**，家族按 `td.holdingslist` + 分馆表头解析（同省图）。

## fixture 清单

- `search.html`：`library=甘南馆`、`"三体"` 结果页（3 命中，单页）。
- `detail.html`：《三体 刘慈欣著》详情（copy_info「1 馆藏于 甘南图书馆.」，保守不可借）。

## 数据边界

- 馆藏到索书号级，`item_id`/`due_date` 恒空串；无明确在架词时全部 `available=False`、
  状态原值照登，不做「馆藏于＝可借」预设。
