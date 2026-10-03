# 通化市图书馆 UILAS 侦察（2026-10-03 实抓）

站点：`https://m.thslib.cn:3888/ILASOPAC/Index?target=0`（页标题「UILAS知识
检索平台」）。立项登记见 docs/data-sources/cn.md 总览表通化行（旧登记
www.thlib.net 未核实，以实测为准）。

技术组件：**UILAS 知识检索平台**（ILAS 系 HTML OPAC，Tomcat/JSP），与金华市
图书馆**同款**，协议（HTTP 层＋解析）见 `uilas/` 家族。字段侦察结论以本文件为准。

## 与金华（tests/fixtures/jinhua/NOTES.md）的对照结论

**同构、家族解析零改动**：检索 `POST NTRdrBookRetr.do`、详情
`GET NTRdrBookRetrInfo.do?recno=`、馆藏内联 `div#BookHolding`、状态词表仅
「入藏（可借）／借出（不可借）」、借出无应还日期列 → `due_date` 恒空。
实抓「三体」共 [10] 条、1 页，首条《三体.Ⅱ.黑暗森林》（recno 124581）。

**差异点**：

1. 站点是 **HTTPS**（端口 3888）。实测 **Python 默认 TLS 上下文即可握手**
   （非舟山式静态 RSA 套件站点）；照舟山下发
   `ssl_ciphers="AES256-GCM-SHA384:AES128-GCM-SHA256"` 反而
   `SSLV3_ALERT_HANDSHAKE_FAILURE`。故本城**不加** `ssl_ciphers`。
2. 结果条目 recno 锚点形态与金华的 `name="bookItemCheckbox"` 不同：页面把
   `bookItemCheckbox` 与 `recno=` 链接并用，家族 `parse_search` 的
   `_RECNO_LINK`（`recno=(\d+)`）兜底命中，无需扩展 quirk。
3. 题名内用半角句点拼接分卷（`三体.Ⅱ.黑暗森林`），原值照登。

## 状态词表（实抓样本）

同金华：`入藏`（可借）、`借出`（不可借）。详情 recno 124581 为 3 册全 `入藏`；
recno 127760（`detail_loan.html`）为 6 册（4 `入藏` ＋ 2 `借出`）。未观测值一律
保守判不可借、`status` 原值照登。

## 数据边界

- 借出单册无应还日期列 → `due_date` 恒空（与金华同，数据边界非故障）。
- 列表页无状态词；`availability_summary` 恒空串。
- 馆藏馆名兼含「通化市图书馆」与区馆「东昌区图书馆」（联合目录口径），原值照登。

## fixture 清单

| 文件 | 内容 |
|---|---|
| `index.html` | 入口 `/ILASOPAC/Index?target=0`（UILAS 指纹、检索表单） |
| `search_p1.html` | `POST NTRdrBookRetr.do` 检索「三体」，共有 [10] 条、页码 1/1 |
| `search_empty.html` | 生造关键词，共有 [] 条、0 结果 |
| `detail.html` | `GET NTRdrBookRetrInfo.do?recno=124581`（3 册全入藏） |
| `detail_loan.html` | 同上 recno=127760（6 册：4 入藏＋2 借出，两表） |
