# 芜湖市图书馆 UILAS 侦察（2026-10-03 实抓）

站点：`https://ilas.whstsg.org.cn:18086/ILASOPAC/`（页标题「UILAS知识检索平台」）。
立项登记见 docs/data-sources/cn.md 总览表芜湖行（旧登记 www.whlib.net 未核实，以实测为准）。

技术组件：**UILAS 知识检索平台**（ILAS 系 HTML OPAC，Tomcat/JSP），与金华市
图书馆**同款**，协议（HTTP 层＋解析）见 `uilas/` 家族。字段侦察结论以本文件为准。

## 与金华（tests/fixtures/jinhua/NOTES.md）的对照结论

**同构、家族解析零改动**：检索 `POST NTRdrBookRetr.do`（`searchType=text` /
`searchKey=三体`）、详情 `GET NTRdrBookRetrInfo.do?recno=`（标记「书目详细信息」）、
馆藏内联 `div#BookHolding`（实抓 3163574 为「入藏、入藏、借出」3 册，两表；有借出
复本时出现「已外借馆藏」第二表）、状态词表仅「入藏（可借）／借出（不可借）」、
借出无应还日期列 → `due_date` 恒空。实抓「三体」共 [143] 条、8 页，首条
《三体：图像小说》（recno 3163574）。

**差异点**：

1. 站点是 **HTTPS**（端口 18086，入口 `/ILASOPAC/` 无 `Index?target=0`）。
   实测 **Python 默认 TLS 上下文即可握手**（非舟山式静态 RSA 套件站点）；
   若照舟山下发 `ssl_ciphers="AES256-GCM-SHA384:AES128-GCM-SHA256"` 反而
   `SSLV3_ALERT_HANDSHAKE_FAILURE`。故本城**不加** `ssl_ciphers`，用默认上下文。
2. 其余（表单参数、详情/馆藏结构、状态词表）与金华逐项相同，家族 parser 零改动。

## 状态词表（实抓样本）

同金华：`入藏`（可借）、`借出`（不可借）。实抓 recno 3163574 详情页 3 册
（2 `入藏` ＋ 1 `借出`，两表）。未观测值一律保守判不可借、`status` 原值照登。

## 数据边界

- 借出单册无应还日期列 → `due_date` 恒空（与金华同，数据边界非故障）。
- 列表页无状态词；`availability_summary` 恒空串。
- 详情页无「附注提要」时 `summary` 空串；查询 ISBN 用冒号分隔的连字符原值照登
  （`978-7-5753-0280-7`）。
- 著者原值含生卒年前缀与尾部分号（`(1963-)刘慈欣原著；吴青松编绘；`），原值照登。

## fixture 清单

| 文件 | 内容 |
|---|---|
| `index.html` | 入口 `/ILASOPAC/`（UILAS 指纹、检索表单） |
| `search_p1.html` | `POST NTRdrBookRetr.do` 检索「三体」，共有 [143] 条、页码 1/8 |
| `search_empty.html` | 生造关键词，共有 [] 条、0 结果 |
| `detail.html` | `GET NTRdrBookRetrInfo.do?recno=3163574`（3 册：入藏＋入藏＋借出，两表） |
