# 泰州市图书馆 LibStar Find 侦察（2026-10-03 实抓）

站点：`https://findjstzlib.pub.chaoxing.com`（页标题「统一检索」，`*.pub.chaoxing.com`
域名）。技术组件 **图星 LibStar Find**（北京图星·超星集团），与无锡新吴/徐州/淮安/
盐城/汉中同款，协议（HTTP 层＋解析）见 `libstar/` 家族。信封
`{success, message, errCode, data}`。

**标识冲突**：`taizhou` 已被浙江省台州市占用，本城为江苏省泰州市，故标识用
`taizhou_js`（js＝江苏）。

## 租户号（groupcode）

`groupCode=100508`，由 `POST /find/homePage/getGroupCode {"mappingPath":""}`
查得（`data.groupCode`，`data.name=泰州市图书馆`）。**必需请求头 `Referer`＋
`groupcode` 缺一不可**（缺 Referer 回 9999「系统访问中断」，缺 groupcode 静默
0 结果），由家族 client 统一注入。

## 检索

`POST /find/unify/search`，`searchFieldContent=三体`。实抓「三体」总命中
`numFound=179`（36 页），首条 `recordId=345767`《三体 : 图像小说》（可借概况
「纸本2，可借2」）。分页由家族按 `numFound/rows` 自算。

## 详情与馆藏

- 详情 `GET /find/searchResultDetail/getBookDetail?recordId=345767`：题名
  「三体:图像小说」、作者「刘慈欣原著 吴青松编绘」、出版社「译林出版社」、
  出版年 2025、ISBN `978-7-5753-0280-7`、中图分类号 `J228.2`、内容简介齐全。
- 馆藏 `POST /find/physical/groupItemsByLibCode {"recordId":"345767"}`：2 册，
  馆名「泰州市图书馆」、状态「在架」、索书号 `J228.2/6319`。

## 与无锡/徐州/淮安/盐城/汉中的对照

**同构、家族 parser 零改动**：字段码 `cnb01`/`cnb03`/`cnb04`/`cnb67`/`cnb96`
同形；状态词表 `在架`（可借）／`借出-应还日期:YYYY-MM-DD`（不可借）同款。
**差异（无 quirk 字段）**：单实例，`book_id` 即裸 `recordId`。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | SPA 外壳（指纹「统一检索」） |
| `search_santi.json` | 检索「三体」，numFound=179 |
| `search_empty.json` | 生造关键词，numFound=0 |
| `detail_santi.json` | `GET getBookDetail?recordId=345767` |
| `holding_santi.json` | `POST groupItemsByLibCode` recordId=345767，2 册在架 |

## 数据边界

- 部分书目无 `onShelfCountI` 等字段时，`availability_summary` 为空串（家族口径）。
- 本城实抓未触发验证码，家族内置 ≥1 秒节流。
