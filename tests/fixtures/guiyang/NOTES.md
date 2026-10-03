# 贵阳市图书馆 UILAS 侦察（2026-10-03 实抓）

站点：`http://218.201.254.11/Index?target=0`（页标题「UILAS知识检索平台」）。
立项登记见 docs/data-sources/cn.md 总览表贵阳行，用户所给入口按**市馆**登记
（若实为省图再改隶；旧登记 www.gylib.org.cn 为登录墙，弃用）。

技术组件：**UILAS 知识检索平台**（ILAS 系 HTML OPAC，Tomcat/JSP），与金华市
图书馆**同款**，协议（HTTP 层＋解析）见 `uilas/` 家族。字段侦察结论以本文件为准。

## 与金华（tests/fixtures/jinhua/NOTES.md）的对照结论

**同构、家族解析零改动**：检索 `POST NTRdrBookRetr.do`、详情
`GET NTRdrBookRetrInfo.do?recno=`、馆藏内联 `div#BookHolding`、状态词表仅
「入藏（可借）／借出（不可借）」、借出无应还日期列 → `due_date` 恒空。
实抓「三体」共 [80] 条、4 页，首条《不要回答．Vol.02，太空军》（recno 900884513）。

**差异点**：

1. 应用上下文为**根路径**（`base_url="http://218.201.254.11"`，入口 `/Index?target=0`，
   无 `/ILASOPAC` 前缀）——与金华/六安/通化不同，家族按 `base_url + "/NTRdrBookRetr.do"`
   拼路径天然兼容，无需新 quirk。裸 IP 纯 HTTP（同金华），无 TLS quirk。
2. 列表页题名与详情页题名标点不一致（列表「．Vol.02，太空军」／详情「．Vol.02：太空军」），
   原值照登不对齐（家族既有数据边界）。

## 状态词表（实抓样本）

同金华：`入藏`（可借）、`借出`（不可借）。详情 recno 900884513 为 1 册 `入藏`。
未观测值一律保守判不可借、`status` 原值照登。

## 数据边界

- 借出单册无应还日期列 → `due_date` 恒空（与金华同，数据边界非故障）。
- 列表页无状态词；`availability_summary` 恒空串。
- 著者原值重复（`三体宇宙编著；三体宇宙编著；`）与馆藏馆名（`贵阳市南明区图书馆`）
  均为源站原值，照登不修正。

## fixture 清单

| 文件 | 内容 |
|---|---|
| `index.html` | 入口 `/Index?target=0`（UILAS 指纹、检索表单） |
| `search_p1.html` | `POST NTRdrBookRetr.do` 检索「三体」，共有 [80] 条、页码 1/4 |
| `search_empty.html` | 生造关键词，共有 [] 条、0 结果 |
| `detail.html` | `GET NTRdrBookRetrInfo.do?recno=900884513`（1 册入藏） |
