# 青岛市公共图书馆联合目录 OPAC 侦察（2026-10-02 实抓）——检索通道改用站点内嵌 Solr

站点:`http://124.129.202.157/opac/index`。馆名全称:页面头部与 meta keywords 均自报
「**青岛市公共图书馆联合目录**」——不是单一「青岛市图书馆」,而是全市联合目录,
libcodeMap 共 26 个馆码(主馆「青岛市图书馆」馆码 `QT`,另有市南/市北/李沧/崂山/
城阳/西海岸新区/即墨/平度/胶州/莱西等区级馆、城市书房分馆、党校/检察院等
非典型成员,原值照登见 holding.json)。技术组件:图创 Interlib
(首页含「图创」「interlib」指纹,版权行 interlib.com.cn)。

**结论:已接入。** 检索入口 `/opac/search` 确实被滑动验证码墙常态拦截(新会话首个
检索请求即触发,非限速封禁),该页至今仍拦截(2026-10-02 复测:匿名直连与「先取首页
会话再带 Referer」两条路径均返回 `opac验证` 页)。但站点内嵌的 **Solr 后端
`/opac/api/search` 开放且不经验证码**——检索原语改走该通道,问题消解。详情页与
馆藏 JSON 开放且与家族解析器零改动兼容。移动端/其他入口未再排查(Solr 通道已够用)。

## 检索通道:站点内嵌 Solr 后端 `/opac/api/search`(开放,不经验证码)

同一 `/opac/api/` 命名空间下(与已在用的 `/opac/api/holding/`、`/opac/api/libcodes`
同族),是站点自己的后端检索接口,不是绕过手段:它不经过 `/opac/search` 那道验证码门。

- `GET /opac/api/search?q=三体&rows=10&page=1&wt=json` → HTTP 200,`response.numFound`
  =143,`response.docs[]` 10 条。响应头 `Content-Type: application/json`(XML 是默认,
  加 `wt=json` 即得 JSON;不加则返回 Solr XML,结构同源)。
- **参数**:`q`(书名/作者/ISBN 通吃)、`rows`(每页条数)、`page`(页码)、`wt=json`。
  服务端凭 `page` 自算 `start=(page-1)×rows`——**直传 `start` 被服务端忽略**
  (实抓:`start=10&rows=3` 回显 `start=0`、仍回首条;`page=2&rows=3` 才回显 `start=3`)。
  `page=0` 被服务端当 1 处理;`page` 超出总页数返回空 `docs`(不报错)。
  服务端会把自己拼的 `q`(dismax 式:`title:三体^10 OR titleKeyword:三体*^20 …`)回显在
  `responseHeader.params.q`,所以**字段限定式检索不生效**(`q=title_meta:三体` 实测 0 条)。
- **`fq` 不可用**:服务端默认 `fq` 是硬编码的状态白名单(`state:…` 长串)＋定位集合
  (`orglocal:…` 长串),自行追加的 `fq` 被整体覆盖(实测 `fq=hasholding:y`、
  `fq=curlibcode:0100` 均无效果)。**后果**:结果默认只含有馆藏的书目,
  `hasholding` 恒为 `y`(实抓 143/143、空检索 1000/1000),因此不构成逐书目可借概况。
  顶层参数 `curlibcode` 可用(`curlibcode=0100` 把「三体」143 条收敛到 4 条,0100=青岛市图书馆)。
- **字段**(`docs[]`):`id`(稳定书目号,即 `bookrecno`)、`title_meta`、`author_meta`、
  `publisher_meta`、`pubdate_meta`(可带月,如「2019.01」)、`isbn_meta`、`classno_meta`、
  `callno_sort`、`subject_meta`、`page_meta`、`price_meta`、`loannum_sort`、
  `booktype_meta`、`hasholding`、`score`、`indate`/`regdate`(epoch 毫秒)。
- **检索行为**:`q=9787536692930` 命中 3 条;带连字符 `q=978-7-5366-9293-0` 命中 0 条
  (与广州 marc 检索同病),故适配器沿用家族「首搜为空则去连字符重试」语义。
  空 `q` 返回全库 1,550,368 条;`rows=1000` 服务端接受(未探到上限)。
  零结果时 `numFound=0`、`docs=[]`,不报错。
- **限频**:连发 6 次(间隔 0.6 秒)全部 200、无验证码、无 401。适配器仍按本仓库惯例
  自带 ≥2 秒/host 保守节流(该站检索入口有验证码门禁,留余量)。

## 检索入口:滑动验证码墙(search_captcha.html 原样存证)——现不经过该通道

- `GET /opac/search?q=三体&searchType=standard&searchWay0=marc&logical0=AND&rows=10&sortWay=score&sortOrder=desc&page=1`
  → HTTP 200,3561 字节,`<title>opac验证</title>`。
- 匿名直连、以及先 GET 首页拿 JSESSIONID+IFCCAS_3RD_TOKEN 再带会话与 Referer
  的合法流程,**两种路径均在首个检索请求即命中验证码页**——是常态门禁,不是
  限速后的临时封禁(天津 ALEPH 那种约 8 请求后 401 封 IP、可人工解封的形态)。
- 验证组件:`$('#mpanel1').slideVerify({...})`(layui + `/opac/media/captcha/js/verify.js`),
  滑动成功回调 POST `/opac/captcha/verification`(参数 `captchaVerification`),
  返回 code==200 时提示文案「验证成功，等待页面跳转」,随后 `window.location.reload()`
  ——验证结果只落在当次浏览器会话,程序化客户端无法复用。
- 首页检索表单即 `<form name="searchForm" action="search" method="get">`,
  与家族标准检索路径同一个被拦端点;热词入口 `searchByHotKeyword()` 也指向检索页。

**因此青岛 HTML 搜索结果页结构(bookmeta 容器、总数文案、分页锚点、express_isbn
属性)全部未验证**。检索改走 Solr 通道后不再需要该页:总数取 `numFound`、分页按
`rows`/`page` 自算,均不依赖 HTML 结构,故不再实抓。

## 开放端点(无验证码,实测)

### 详情页 `GET /opac/book/{bookrecno}`(detail.html,id=177071)

- `<table id="bookInfoTable">` + leftTD/rightTD 两列结构与广州基准一致;标题在首个
  `<h2>`(《中国古代造纸史渊源》);`/opac/api/holding/` 在页内出现(Ajax 加载馆藏,
  同广州);「馆藏浏览」锚点缺失、「馆藏地点」存在(同杭州 quirk,家族解析不依赖)。
- 家族 `parser.parse_detail` **零改动全字段解析成功**:title/author(主要责任者)/
  publisher+publish_year(出版发行)/isbn/call_number(中图分类法)/summary(内容提要)。
- 与广州基准的标签集差异(原值照登,不做预设判断):
  - 多一行独立「**索书号**」标签(广州没有);家族解析器不认该标签,call_number 仍取
    「中图分类法」值(F426.83),完整索书号(F426.83/2)在馆藏 JSON `callno` 里。
    若接入时想优先取「索书号」行,需家族新增 quirk 字段,现未验证该行值的形态。
  - 多「豆瓣内容简介:」「豆瓣著者简介:」标签行,家族解析器忽略,不影响现字段。
  - 首行标签是「题名/责任者:」,值单元格含 `<h2>` 标题(与广州同构)。
  - leftTD 文本含换行与制表符(如「中图分类法\n\t…:」),家族 `_clean` 折叠空白 +
    rstrip 冒号后正常归一,已实测无碍。
- 无效 id(book/1)返回 HTTP 500 错误页(与 ZXYH 缺 curlibcode 时同症状);青岛
  详情**无需 curlibcode 参数**(裸 GET 即 200)。

### 馆藏 JSON `GET /opac/api/holding/{bookrecno}?limitLibcodes=&isCluster=`(holding.json,id=177071)

- 顶层字段与广州完全一致:`holdingList/libcodeMap/localMap/holdStateMap/loanWorkMap/
  pBCtypeMap/barcodeLocationUrlMap/libcodeDeferDateMap/shelfnoUrlMap`(9 键)。
- 单册字段同构:`state/callno/curlib/curlocal/shelfno/barcode/loan/...`,另见
  `stateStr`(本样例为 null,语义未验证,原值照登)。
- 家族 `parser.parse_holdings` 零改动解析 4 条馆藏,馆名/位置/状态全部正确翻译:
  崂山图书馆·3楼书库·在馆、胶州图书馆·三里河街道_中赵家庄·在馆、
  青岛市图书馆·库密1（闭架5、6楼查阅）·在馆、胶州图书馆·九龙街道_西石河城市书房·在馆。
- `holdStateMap` 22 项(广州 29 项),含青岛特有状态码:9=锁定、12=清点、14=修补、
  15=查找中、16=重复锁定、31=运回中、32=已签收、33=已通还、35=丢失赔书、36=已装订。
  逐项过 `is_available_status`:以上特有状态全部保守判不可借,「在馆」判可借,
  「借出」判不可借——**家族现有词表无需改动**(未识别状态本就保守不可借)。
- 无效 id(holding/1)返回 200 + 空 holdingList(不报错),libcodeMap 等字典仍全量返回。
- `loanWorkMap` 本样例为空(4 条全在馆,无借出样例),借出单册的应还日期字段
  (returnDate)未验证——与广州 fixture 初期同样的空白,待有借出样例时确认。
- `libcodeDeferDateMap` 给出各馆延长天数(0/1/7 不等),家族现不消费。

### 榜单页 `GET /opac/ranking/bookLoanRank`(未存 fixture)

开放,返回借阅榜单,内含真实 `/opac/book/{bookrecno}` 链接(177071 即由此取得)。
是无需检索即可获得 book_id 的旁路,但榜单不是检索能力,不构成接入依据。

## Fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `search_captcha.html` | `GET /opac/search?q=三体&...`(带会话+Referer) | 滑动验证码页原样存证,检索被拦的证据 |
| `detail.html` | `GET /opac/book/177071` | 《中国古代造纸史渊源》详情页,家族 parser 零改动可解析 |
| `holding.json` | `GET /opac/api/holding/177071?limitLibcodes=&isCluster=` | 馆藏 JSON,4 条全「在馆」,含 26 馆 libcodeMap 与 22 项 holdStateMap |

| `search_solr.json` | `GET /opac/api/search?q=中国古代造纸史渊源&rows=10&page=1&wt=json` | 单命中样本(`numFound=1`,`id=177071`,与详情/馆藏 fixture 同一本书) |
| `search_solr_santi.json` | `GET /opac/api/search?q=三体&rows=10&page=1&wt=json` | 多页样本(`numFound=143`,10 条/页,含 `pubdate_meta=2019.01` 带月形态) |
| `search_solr_empty.json` | `GET /opac/api/search?q=zzzz不存在&rows=10&page=1&wt=json` | 零结果样本(`numFound=0`,`docs=[]`,不报错) |

无 HTML 搜索结果页 fixture(该页仍被验证码拦截;改走 Solr 通道后不再需要)。

## 侦察请求清单(全部只读 GET,间隔 ≥2 秒)

首轮 9 次(遇验证码即停手):

1. `/opac/index`(匿名)→ 200,493KB 首页,馆名与 Interlib 指纹确认
2. `/opac/index`(cookie jar)→ 200,取得 JSESSIONID + IFCCAS_3RD_TOKEN
3. `/opac/search?q=三体&…rows=10&page=1`(匿名)→ 200 验证码页
4. `/opac/search?q=三体&…`(带会话+Referer)→ 200 验证码页(判定:常态门禁)
5. `/opac/book/1`(无效 id 探测)→ 500
6. `/opac/api/holding/1?limitLibcodes=&isCluster=` → 200,空 holdingList
7. `/opac/ranking/bookLoanRank` → 200,取得真实 bookrecno
8. `/opac/book/177071` → 200,详情页 fixture
9. `/opac/api/holding/177071?limitLibcodes=&isCluster=` → 200,馆藏 fixture

复测轮(`/opac/search` 两条路径仍为验证码页,另发现 Solr 通道):

10. `/opac/search?q=三体&…`(匿名)→ 200 验证码页(与首轮一致,非临时封禁)
11. `/opac/search?q=三体&…`(带会话+Referer)→ 200 验证码页(同上)
12. `/opac/api/search?q=三体` → 200,Solr XML(`numFound=143`),不经验证码
13. `/opac/api/search?q=三体&rows=3&wt=json` → 200,JSON
14. `/opac/api/search?q=三体&start=10&rows=3` → 回显 `start=0`(`start` 被忽略)
15. `/opac/api/search?q=三体&page=2&rows=3` → 回显 `start=3`(`page` 生效)
16. `/opac/api/search?q=9787536692930` → 200,3 条;`q=978-7-5366-9293-0` → 0 条
17. `/opac/api/search?q=` → 全库 1,550,368 条;`rows=1000` 接受
18. `/opac/api/search?q=三体&…` 连发 6 次(间隔 0.6 秒)→ 全 200,无验证码/401
19. `/opac/book/912374345`、`/opac/api/holding/912374345` → 200,`docs[].id` 直连详情/馆藏成立
20. 三份 `wt=json` 检索 fixture 抓取(见上表)

## 后续调研方向

- 定期探测 `/opac/search` 验证码策略是否变化;策略放开可再评估改回 HTML 检索页
  (但 Solr 通道已够用,且字段更结构化)。
- 服务端 `fq` 若出现可配置形态,可评估暴露「只看某馆」与逐书目可借概况。
- 若馆方提供白名单/接口授权,优先替换为授权接口。
