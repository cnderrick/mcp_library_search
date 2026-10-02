# 舟山市图书馆 UILAS 侦察（2026-10-03 实抓）

站点：`https://opac.zsodl.cn/Index?target=0`（页标题「UILAS知识检索平台」）。
立项登记见 docs/data-sources/cn.md 总览表舟山行（原登记 `www.zslib.net` 已不通）。

技术组件：**UILAS 知识检索平台**（ILAS 系 HTML OPAC，Tomcat/JSP），与金华市
图书馆**同款**，协议（HTTP 层＋解析）抽到 `uilas/` 家族共用。舟山相对金华的
唯一实质差异是**旧式 TLS 密码套件**（见下）。

## 与金华（tests/fixtures/jinhua/NOTES.md）的对照结论

**同构、家族解析零改动**的部分：检索 `POST NTRdrBookRetr.do`（`searchType`/
`searchKey`，ISBN 形态路由 `isbnsrh`）、翻页 GET 带 `nCurrentpage` 且 `SearchKey`
双重 URL 编码、详情 `GET NTRdrBookRetrInfo.do?recno=`（标记「书目详细信息」）、
馆藏内联 `div#BookHolding`（有借出复本时两表）、状态词表仅「入藏（可借）/
借出」、借出无应还日期列 → `due_date` 恒空。实测 10/10 条搜索、详情与馆藏
全字段经由家族 parser 与金华一致。

**差异点**：

1. **旧式 TLS（本城接入的关键）**：站点只支持**静态 RSA 密钥交换**的 TLS 1.2
   密码套件（协商结果为 `TLS_RSA_WITH_AES_256_GCM_SHA384`），**不支持 ECDHE**。
   OpenSSL 3.5 的默认密码列表已停用静态 RSA kx，`urllib` 默认上下文直接回
   `SSLV3_ALERT_HANDSHAKE_FAILURE`（实测 Python 3.13/3.14 均失败，而 curl/LibreSSL
   可通）。`UilasConfig.ssl_ciphers ="AES256-GCM-SHA384:AES128-GCM-SHA256"` 让家族
   HTTP 层显式放行这些套件即可。`ECDHE-RSA-AES256-GCM-SHA384` 单独下发仍失败，
   证明服务端确无 ECDHE。
2. 站点是 **HTTPS**（金华是裸 IP 纯 HTTP）；入口为域名。
3. 其余（表单参数、翻页、详情/馆藏结构、状态词表）与金华逐项相同。

## 状态词表（实抓样本）

同金华：`入藏`（可借）、`借出`（不可借）。实抓 1533337 详情页 1 册 `入藏`；
1561197 详情页 2 册（`入藏` ＋ `借出`，两表）。未观测值一律保守判不可借、
`status` 原值照登（同重庆口径）。

## 数据边界

- 借出单册无应还日期列 → `due_date` 恒空（与金华同，数据边界非故障）。
- 列表页无状态词；`availability_summary` 恒空串。
- 详情页标题可能短于列表页（原值照登不对齐，同金华）。

## fixture 清单

| 文件 | 内容 |
|---|---|
| `index.html` | 首页（UILAS 指纹、检索表单） |
| `search_p1.html` | `POST NTRdrBookRetr.do` 检索「三体」，共有 [266] 条、页码 1/27 |
| `search_empty.html` | 生造关键词，共有 [] 条 |
| `detail.html` | `GET NTRdrBookRetrInfo.do?recno=1533337`（1 册入藏） |
| `detail_loan.html` | 同上 recno=1561197（2 册：入藏＋借出，两表） |
