# 海西州图书馆 LibStar Find 侦察（2026-10-03 实抓）

站点：`https://findhxztsg.libsp.cn`（页标题「统一检索」）。技术组件 **图星
LibStar Find**（北京图星·超星集团），与无锡新吴/徐州/淮安/盐城/汉中/泰州同款，
协议（HTTP 层＋解析）见 `libstar/` 家族。信封 `{success, message, errCode, data}`。

**旧批「需登录」不成立**：本批实抓匿名接口可用——`getGroupCode` 与三原语
（检索/详情/馆藏）均匿名 HTTP 200，未见登录墙或验证码，故正常接入。

## 租户号（groupcode）

`groupCode=100216`，由 `POST /find/homePage/getGroupCode {"mappingPath":""}`
查得（`data.groupCode`，`data.name=海西州图书馆`，`data.label=Hxztsg`）。
**必需请求头 `Referer`＋`groupcode` 缺一不可**（缺 Referer 回 9999「系统访问
中断」，缺 groupcode 静默 0 结果），由家族 client 统一注入。

## 检索

`POST /find/unify/search`，`searchFieldContent=三体`。实抓「三体」总命中
`numFound=106`（22 页），首条 `recordId=148476`《三体. Ⅱ, 黑暗森林》
（可借概况「纸本4，可借4」）。

## 详情与馆藏

- 详情 `GET /find/searchResultDetail/getBookDetail?recordId=148476`：题名
  「三体.Ⅱ.黑暗森林」、作者「刘慈欣著」、出版社「重庆出版社」、出版年 2008、
  ISBN `978-7-5366-9396-8`、中图分类号 `I247.55`；本记录内容简介为空串。
- 馆藏 `POST /find/physical/groupItemsByLibCode {"recordId":"148476"}`：4 册，
  馆名「海西州图书馆」、索书号 `I247/197`；2 册「在架」（可借）、2 册
  「借出-应还日期:2026-06-25 / 2026-09-28」（不可借，带应还日期）。

## 与无锡/徐州/淮安/盐城/汉中/泰州的对照

**同构、家族 parser 零改动**：字段码与状态词表同款。**差异（无 quirk 字段）**：
单实例，`book_id` 即裸 `recordId`。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | SPA 外壳（指纹「统一检索」） |
| `search_santi.json` | 检索「三体」，numFound=106 |
| `search_empty.json` | 生造关键词，numFound=0 |
| `detail_santi.json` | `GET getBookDetail?recordId=148476` |
| `holding_santi.json` | `POST groupItemsByLibCode` recordId=148476，4 册（2 在架 2 借出） |

## 数据边界

- 部分书目无 `onShelfCountI` 等字段时，`availability_summary` 为空串（家族口径）。
- 本城实抓未触发验证码，家族内置 ≥1 秒节流。
