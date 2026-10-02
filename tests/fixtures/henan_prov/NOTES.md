# 河南省图书馆 UILAS 侦察（2026-10-03 实抓）

站点：`http://218.28.6.78:8081/ILASOPAC/Index?target=0`（页标题「UILAS知识检索
平台」）。与金华市图书馆同款**老版 UILAS（HTML OPAC）**，协议见 `uilas/` 家族。

## fixture 与实测

- 检索 `POST NTRdrBookRetr.do`：实抓「三体」共 [57] 条记录。
- 详情 `GET NTRdrBookRetrInfo.do?recno=`：首条《我的三体漫画．第一辑．1》ISBN `978-7-5728-2657-3`；馆藏内联
  `div#BookHolding` 3 条（3 入藏可借）。
- 状态词表同金华（入藏可借／借出不可借）；借出无应还日期 → `due_date` 空串。

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | 检索「三体」，共有 [57] 条 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail.html` | 详情页（含内联馆藏） |
