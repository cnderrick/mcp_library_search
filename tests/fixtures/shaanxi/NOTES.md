# 陕西省图书馆（新版 UILAS REST 平台）侦察（2026-10-03 实抓）

站点：`https://uilas.sxlib.org.cn`（页标题「UILAS知识检索平台」）。前端 Vue，
接口在 `/prod-api/*`（nginx 映射后端 `/ILASOPAC/*`），返回 JSON。这是**新版
UILAS（ILAS REST 检索平台）**，与老版 `uilas/`（HTML OPAC，`NTRdrBookRetr.do`）
同宗不同代，故独立成家族 `uilas_rest/`。省级馆（馆址西安），匿名可通。

## fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `index.html` | `GET /` | SPA 外壳（指纹「UILAS知识检索平台」） |
| `search_santi.json` | `GET /prod-api/bookSearch/search?searchKey=三体&pageNum=1&pageSize=10` | totalElements=50 |
| `search_empty.json` | 生造关键词 | totalElements=0 |
| `detail_santi.json` | `GET /prod-api/book/bookDetail?recno=8099896` | 书目＋馆藏 |
| `detail_loan.json` | 同上（另一含借出记录的书目） | 状态样本 |

## 接口形态

- **检索**：`GET /prod-api/bookSearch/search`，参数 `searchKey`/`pageNum`/`pageSize`
  （`pageSize` 服务端生效）。响应 `data.pageList.list[]`（书目条目）＋
  `data.pageList.totalElements`（总数）＋ `totalPages/currentPage`。
- **详情**：`GET /prod-api/book/bookDetail?recno={id}`。书目在 `data.bookDetail`
  （`name/author/publish/pubyear/isbn/classno/contents/publish…`），馆藏在
  `data.inList[]`（`status/callno/curlib/curlocal/retudate/cirtype/barcode`），
  馆名表 `data.libraryList`。详情一步即可同时取书目与馆藏。
- **馆藏状态码**（前端 i18n `bookinfo_hold_status_*`）：`a=采编 / b=在馆 /
  c=借出 / d=租出 / e=预约`；**只有 `b` 视为可借**，其余与未知码保守不可借。

## 数据边界

- `bookDetail` 与检索条目同形；`summary` 对应 MARC 提要（`contents`），可为 null → 空串。
- 可借概况由检索条目的 `holdingCount`（总册）/`inHoldingCount`（在馆）拼装。
- 借出单册 `retudate` 为应还日期；无借出时为 `null` 或 `"0"` → 空串。

## 其他

- 未发现验证码；匿名可通。
