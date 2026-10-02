# 汉中市图书馆 LibStar Find 侦察（2026-10-03 实抓）

站点：`https://findhanzhong.libsp.cn`（页标题「统一检索」）。技术组件 **图星
LibStar Find**（北京图星·超星集团），与无锡新吴/徐州/淮安/盐城同款，协议（HTTP
层＋解析）见 `libstar/` 家族。信封 `{success, message, errCode, data}`。

## 租户号（groupcode）

`groupCode=100121`，由 `POST /find/homePage/getGroupCode {"mappingPath":""}`
查得（`data.groupCode`，`data.name=汉中市`）。**必需请求头 `Referer`＋`groupcode`
缺一不可**（缺 Referer 回 9999「系统访问中断」，缺 groupcode 静默 0 结果），由
家族 client 统一注入。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | SPA 外壳（指纹「统一检索」） |
| `search_santi.json` | 检索「三体」，numFound=930 |
| `search_empty.json` | 生造关键词，numFound=0 |
| `search_santi_nogroup.json` | 同上「三体」但不带 groupcode 头，numFound=0（对照证据） |
| `detail_santi.json` | `GET getBookDetail?recordId=187591`（《三体》） |
| `holding_santi.json` | `POST groupItemsByLibCode` recordId=187591，洋县图书馆 1 册在架 |

## 与无锡/徐州/淮安/盐城的对照

**同构、家族 parser 零改动**：检索 `POST /find/unify/search`；详情
`GET getBookDetail?recordId=`；馆藏 `POST groupItemsByLibCode`。字段码
`cnb01`/`cnb03`/`cnb04`/`cnb67`/`cnb96` 同形；状态词表 `在架`（可借）／
`借出-应还日期:YYYY-MM-DD`（不可借）同款。

**差异（无 quirk 字段）**：单实例、联合目录含洋县图书馆等县级馆（馆藏分组
`libName` 原值照登），`book_id` 即裸 `recordId`。
