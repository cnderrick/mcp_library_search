# 枣庄市图书馆（新版 UILAS REST）侦察（2026-10-03 实抓）

站点：`http://60.214.100.211:8082/#/index`（页标题「UILAS知识检索平台」）。
与陕西省图书馆/榆林/兰州/江门同款 **新版 UILAS（ILAS REST 平台）**，协议见
`uilas_rest/` 家族。抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

## fixture 与实测

- 检索 `GET /prod-api/bookSearch/search?searchKey=三体&pageNum=1&pageSize=20`：
  实抓 `totalElements=7`，首条《三体：图像小说》id `900060939`、ISBN `978-7-5753-0280-7`。
- 详情 `GET /prod-api/book/bookDetail?recno=900060939`：书目《三体：图像小说》，
  馆藏 1 条（枣庄市图书馆·少儿借阅部，1 可借）。
- `Referer` 用站点根路径即可（`http://60.214.100.211:8082/`，缺失亦可，但不省）。

| 文件 | 说明 |
|---|---|
| `index.html` | SPA 外壳 |
| `search_santi.json` | 检索「三体」，totalElements=7 |
| `search_empty.json` | 生造关键词，0 条 |
| `detail_santi.json` | `bookDetail?recno=900060939` |

## 数据边界

- 同陕图（状态码 `a采编/b在馆/c借出/d租出/e预约`，仅 b 可借；可借概况由
  `holdingCount`/`inHoldingCount` 拼装；`contents` 为提要，可空）。
