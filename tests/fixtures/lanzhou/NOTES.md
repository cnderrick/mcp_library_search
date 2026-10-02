# 兰州市图书馆（新版 UILAS REST）侦察（2026-10-03 实抓）

站点：`http://36.137.50.135:8082/#/index`（页标题「UILAS知识检索平台」）。与陕西省图书馆/榆林同款
**新版 UILAS（ILAS REST 平台）**，协议见 `uilas_rest/` 家族。

## fixture 与实测

- 检索 `GET /prod-api/bookSearch/search?searchKey=三体`：totalElements=521。
- 详情 `GET /prod-api/book/bookDetail?recno=483939`：书目《三体 ：死神永生》，ISBN `978-7-229-03093-3`；馆藏 1 条（1 可借）。
- `Referer` 用站点根路径即可（`http://36.137.50.135:8082/`）。

| 文件 | 说明 |
|---|---|
| `index.html` | SPA 外壳 |
| `search_santi.json` | 检索「三体」，totalElements=521 |
| `search_empty.json` | 生造关键词，0 条 |
| `detail_santi.json` | `bookDetail?recno=483939` |

## 数据边界

- 同陕图（状态码 `a采编/b在馆/c借出/d租出/e预约`，仅 b 可借；可借概况由
  `holdingCount`/`inHoldingCount` 拼装；`contents` 为提要，可空）。
