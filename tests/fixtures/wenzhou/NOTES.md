# 温州市图书馆 OPAC 页面结构侦察（2026-10-02 实抓）

站点：`https://opac3.wzlib.cn`（入口 `/opac/index`，图创 Interlib「检索系统」模板）。
全部只读 GET，共 7 个请求，均 HTTP 200，未遇验证码或封禁。

## 馆名确认

页面**没有醒目的本馆全称文本**：首页 `<title>` 是「检索系统」，logo 是图片
（`/opac/media/images/logo.gif`），footer 只有图创版权（www.interlib.com.cn）。
页面证据：meta keywords「opac, 图创, interlib」；馆藏地点大量以「温图」自称
（温图荐购、温图市府路馆、温图少儿分馆……）；分馆名出现「温州市图书馆老年馆」
「温州市图书馆虚拟电子书」。结合域名 wzlib.cn，馆名全称判定为**温州市图书馆**，
`name_cn` 照此登记（页面原值无全称这一事实如实记录于此）。

主馆馆码 `WT` → libcodeMap 显示名「温图市府路馆」；温州是全市总分馆体系，
libcodeMap 共 91 个馆（龙湾馆 LWT、瓯海馆 OHT、鹿城馆 XD、平阳馆 PYT、苍南馆 CNT、
瑞安馆 RAT、文成县农家书屋 WCN……），localMap 2555 个地点。

## Fixture 清单

| 文件 | 大小 | 来源 |
|---|---|---|
| `search_p1.html` | 243297 字节 | `GET /opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1` |
| `search_empty.html` | 121220 字节 | 同上，`q=azbycxq不存在xyz`，0 条结果 |
| `detail.html` | 107483 字节 | `GET /opac/book/2006220724`（《三体漫画．起源》，结构齐全的代表作） |
| `detail_no_primary_author.html` | 100477 字节 | `GET /opac/book/2006188837`（《一说《三体》》，**缺「主要责任者」「内容提要」行**，quirk 证据） |
| `holding.json` | 130437 字节 | `GET /opac/api/holding/2006220724?limitLibcodes=&isCluster=`（21 条单册） |
| `holding_empty.json` | 114463 字节 | `GET /opac/api/holding/2006188837?limitLibcodes=&isCluster=`（**holdingList 为空**，该书仅虚拟电子书馆藏） |

## 搜索页结构（与广州基准一致）

- 每条结果是 `<div class="bookmeta" bookrecno="{id}">` 容器，字段按 class 锚点
  （title-link / author-link / publisher-link）提取，家族 `parse_search` 直接可用。
- 总数：`检索到: 237 条结果`（同款格式，实测解析 total_results=237）。
- 分页：`共 24 页` + 「下一页」锚点，has_next 解析正常。
- `express_bookrecno` / `express_isbn` 属性存在，内部 isbn 字段可提取。
- **空结果页与杭州同款 quirk**：含 JS 函数定义 `function bookDetail(bookrecno,index,flag){`
  （裸 `bookDetail(` 计 1 次），`bookDetail(数字` 为 0 次；无 `meneame` 分页区。
  家族按 `bookmeta` 容器解析，不受影响（实测 books=0、total_results=0）。

## 详情页结构

`<table id="bookInfoTable">` 两列（leftTD 标签 / rightTD 值），标题在首个 `<h2>`，
与广州同模板。`detail.html`（2006220724）行清单（按 DOM 序）：

| data-sort | 标签 | 示例值 |
|---|---|---|
| 0 | `<h2>` 标题 | 三体漫画．起源 |
| 40 | 题名/责任者 | 三体漫画 [ 专著] / 刘慈欣原著 , 蔡劲，戈闻頔，薄暮改编 |
| 10 | ISBN | 978-7-5339-7402-2 价格： CNY36.00 |
| 80 | 语种 | 汉语 |
| 60 / 61 | 载体形态 / 丛编项 | 165页 ; 23cm / 《三体漫画》系列 |
| 50 | 出版发行 | 杭州 : 浙江文艺出版社, 2024 |
| 70 | 内容提要 | 本书讲述了：汪淼是一位物理学家。…… |
| 90 | 主题词 | 漫画、连环画、中国、现代 |
| 100 | 中图分类法 | J228.2 版次： 5 |
| 30 / 110 | 主要责任者 / 次要责任者 | 刘慈欣 原著 / 蔡劲 改编 …… |
| **130** | **索书号** | **J228.2/0287.16/2v4** |
| 98 | 标签（**左格是裸 `<td>`，无 leftTD**） | 没有标签 |

家族 `parse_detail` 实测输出全部正确：title/author（刘慈欣）/publisher/publish_year/
isbn/call_number（J228.2，「版次」前文本）/summary（内容提要）。

### 与广州基准的差异

1. **部分书目有独立「索书号」行（sort=130）**：广州 fixture 无此行。该标签不在家族
   `_DETAIL_LABELS` 词表，不参与解析；`call_number` 维持家族语义取「中图分类法」，
   完整索书号仍以馆藏 JSON `callno` 为准——行为与广州一致，不需要 quirk 字段。
2. **「主要责任者」「内容提要」行是记录级可选**：`detail_no_primary_author.html`
   （2006188837）两行均缺失（该书为引进版科普书，MARC 无对应字段），author/summary
   解析为空串——这是数据边界不是站点差异，广州遇同款记录行为相同。
3. **⚠ tagTr 标签悬挂污染（家族 parser 潜在 bug，温州首先暴露）**：「标签」行
   （sort=98）左格是裸 `<td>`（无 leftTD class），`_DetailParser._label` 不更新，
   其 rightTD 值「没有标签」会挂到**上一个 leftTD 标签**名下。广州/杭州 fixture 里
   tagTr 前一行是「次要责任者」（词表外）故无害；温州 `detail_no_primary_author.html`
   里 tagTr 前最近的 leftTD 恰是「中图分类法」，导致 `call_number` 被污染成
   「没有标签」（正确值应为 Z228）。**任何城市**的书目只要缺「主要/次要责任者」行
   都会踩中。修复建议见交付报告（interlib/parser.py 属禁改区，未动手）：
   在 `_finish_value` 用掉 label 后清空，即 `self._label = ""`。
4. **简介服务端无独立区块**：页面注释「豆瓣内容简介和著者简介移动到下面的tab统一
   显示」，tab 内容 `class="hide"` 由 JS `getBookAllMetaInfo()` 异步拉外网（且调用
   被注释停用）。summary 唯一来源是「内容提要」行，无则空串。

## 馆藏 JSON（与家族接口完全同构）

`GET /opac/api/holding/{bookrecno}?limitLibcodes=&isCluster=`，顶层字段与广州一致：
`holdingList`、`libcodeMap`、`localMap`、`holdStateMap`、`loanWorkMap`、
`libcodeDeferDateMap`、`pBCtypeMap`、`barcodeLocationUrlMap`、`shelfnoUrlMap`。

- `holding.json`（三体漫画．起源）：21 条单册，state 分布 2（在馆）12 / 3（借出）9；
  `loanWorkMap` 9 条与借出数吻合，`returnDate` epoch 毫秒 → 家族 `_to_date` 实测
  归一正常（如 2026-10-25、2026-10-05）。`stateStr` 恒 null（与杭州同，别用）。
- `holdStateMap` 26 项：0=流通还回上架中、1=编目、2=在馆、3=借出、4=丢失、5=剔除、
  6=下架、7=赠送、8=装订、9=锁定、10=预借、12=清点、13=闭架、14=修补、15=查找中、
  16=重复锁定、17/18=物流发送/签收通知、19/33=已通还、31=运回中、32=已签收、
  34=报废、35=丢失赔书、36=已装订、40=馆际丢失。状态原值照登，可借判定沿用家族
  `is_available_status` 词表（在馆/可借/在架），词表外保守不可借——实测「在馆」12 条
  全部判可借、「借出」9 条全部判不可借，无一漏判。
- `holding_empty.json`：holdingList 空数组但三个 map 齐全（libcodeMap 91 项）——
  仅虚拟电子书的书目无实体单册，`get_holdings` 返回空列表是数据事实不是故障。
- 单册字段带 `cirtype`、`volInfo`、`totalLibNum` 等，家族 parser 不需要，不解析。

## curlibcode 判定

温州是**本地部署**（opac3.wzlib.cn 独立域），不是 sm.interlib.cn 式多租户云托管：
首页 `curlibcode` 出现 28 次全是模板 JS 里的「限定所在馆」筛选 checkbox 逻辑，
无租户参数需求。检索/详情/馆藏三个端点均**不带 curlibcode** 实测 200 正常
（详情若需该参数会像 ZXYH 一样 HTTP 500，未发生）。`InterlibConfig.curlibcode`
留默认空串即可。

## 首页体积说明

首页 675KB（解压后 625KB 文本）偏大的原因：「限定所在馆/馆藏地点」筛选区把
91 个馆 + 数千地点的 checkbox 全量服务端渲染进 HTML。搜索页（243KB）、详情页
（107KB）体积正常，无额外结构差异——搜索/详情/馆藏三端点与广州同模板。

## 结论

温州与广州/杭州同款 Interlib 模板，家族三原语零改动可用（curlibcode 默认空）。
唯一需要动家族代码的是 tagTr 标签悬挂污染（parser bug，非温州特有，禁改区，
patch 建议随报告提交）。适配器按广州/杭州同款 `_client` 形态接入，无新增 quirk 字段。
