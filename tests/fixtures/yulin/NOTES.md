# 榆林市图书馆（新版 UILAS REST 平台）侦察（2026-10-03 实抓）

站点：`https://www.yulinlib.org.cn/opac/#/index`（页标题「UILAS知识检索平台」）。
与陕西省图书馆同款**新版 UILAS（ILAS REST 平台）**，协议见 `uilas_rest/` 家族。

## 与陕西省图书馆的差异（唯一实质性 quirk）

- **必需 `Referer` 须为站点子路径 `/opac/`**：`Referer: https://www.yulinlib.org.cn/opac/`
  才返回 `code:200`；用根路径 `/` 时**所有 `/prod-api/*` 接口**（含
  `page/getSetting`、`bookSearch/search`）都回 `{"code":401,"msg":"请求访问：…
  认证失败，无法访问系统资源"}`——接口本身匿名可通，401 是 Referer 门（实测）。
  故 `UilasRestConfig.referer` 显式配置。
- 其余（接口、字段、状态码）与陕图逐项相同。

## fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `index.html` | `GET /opac/` | SPA 外壳 |
| `search_santi.json` | `GET /prod-api/bookSearch/search?searchKey=三体&pageNum=1&pageSize=10` | totalElements=16 |
| `search_empty.json` | 生造关键词 | totalElements=0 |
| `detail_santi.json` | `GET /prod-api/book/bookDetail?recno=65654` | 书目＋馆藏 |
| `detail_loan.json` | 同上（含借出记录书目） | 状态样本 |

## 数据边界

- 馆名原值「榆阅空间」（含沙河路街道分馆等网点），照登。
- 其余同陕图（状态码表、可借概况、summary 空串规则）。
