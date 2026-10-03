# 广西壮族自治区桂林图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`https://opac.gxgllib.org.cn/opac/index`（图创 Interlib，页标题「检索系统」，
meta keywords 自报「opac, 图创, interlib, 图书检索, 借书, …, 广西区域图书馆集群」）。
抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`。站点为
「广西区域图书馆集群」全自治区域联合目录口径（馆藏含灵川县图书馆等成员馆）。

## 检索：HTML 检索页直连

`GET /opac/search`（`searchType=standard&searchWay0=marc&logical0=AND`）直连可用，
返回默认模板结果页（`bookmeta` 容器）。实抓「三体」122 条、共 7 页；生造关键词 0 条。
繁体「三體」亦命中（如《三體石經未裂本》），原值照登。

## 详情与馆藏

- **检索首条**：recno 1900005326《三體石經未裂本》文明書局（该记录无馆藏）。
- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），详情/馆藏实例取
  同页 recno 1902562793《三体》（刘慈欣著／重庆出版社／ISBN `978-7-5366-9293-0`／
  索书号 `I247.55`）。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；recno 1902562793
  实抓 1 条，馆名「灵川县图书馆」、位置「图书总库」、索书号 `I247.55/0287`、状态「借出」。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_p1.html` | HTML 检索「三体」，检索到 122 条 |
| `search_empty.html` | 生造关键词，0 条 |
| `detail_api.json` | `GET /api/book/1902562793`（三体，同页有馆藏记录） |
| `holding.json` | `GET /api/holding/1902562793`（1 条，借出） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- 检索首条 1900005326 无馆藏属记录级数据事实，故 fixture 详情/馆藏改用同页 1902562793。
- `availability_summary` 在 HTML 通道下为空串。
