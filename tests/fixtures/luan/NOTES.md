# 六安市图书馆 UILAS 侦察（2026-10-03 实抓）

站点：`http://60.173.147.75:8081/ILASOPAC/Index?target=0`（页标题「UILAS知识
检索平台」）。立项登记见 docs/data-sources/cn.md 总览表六安行（旧登记
www.lalib.net 未核实，以实测为准）。

技术组件：**UILAS 知识检索平台**（ILAS 系 HTML OPAC，Tomcat/JSP），与金华市
图书馆**同款**，协议（HTTP 层＋解析）见 `uilas/` 家族。字段侦察结论以本文件为准。

## 与金华（tests/fixtures/jinhua/NOTES.md）的对照结论

**同构、家族解析零改动**：检索 `POST NTRdrBookRetr.do`、详情
`GET NTRdrBookRetrInfo.do?recno=`、馆藏内联 `div#BookHolding`、状态词表仅
「入藏（可借）／借出（不可借）」、借出无应还日期列 → `due_date` 恒空。
实抓「三体」共 [33] 条、2 页，首条《三体漫画．上：接触：太阳实验》
（recno 371422）。

**差异点**：无。入口是裸 IP 纯 HTTP（同金华），无 TLS quirk；其余逐项同构。

## 状态词表（实抓样本）

同金华：`入藏`（可借）、`借出`（不可借）。详情 recno 371422 为 3 册全 `入藏`；
recno 371423（`detail_loan.html`）为 3 册（2 `入藏` ＋ 1 `借出`，两表）。未观测值
一律保守判不可借、`status` 原值照登。

## 数据边界

- 借出单册无应还日期列 → `due_date` 恒空（与金华同，数据边界非故障）。
- 列表页无状态词；`availability_summary` 恒空串。
- 详情页「附注提要」有值时取原值（实抓 371422 为 `《三体漫画》系列（少年版） 8 果麦`，
  其中 `8` 为源站录入残片，原值照登不猜）。

## fixture 清单

| 文件 | 内容 |
|---|---|
| `index.html` | 入口 `/ILASOPAC/Index?target=0`（UILAS 指纹、检索表单） |
| `search_p1.html` | `POST NTRdrBookRetr.do` 检索「三体」，共有 [33] 条、页码 1/2 |
| `search_empty.html` | 生造关键词，共有 [] 条、0 结果 |
| `detail.html` | `GET NTRdrBookRetrInfo.do?recno=371422`（3 册全入藏） |
| `detail_loan.html` | 同上 recno=371423（3 册：入藏＋入藏＋借出，两表） |
