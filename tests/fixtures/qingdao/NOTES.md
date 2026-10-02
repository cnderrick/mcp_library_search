# 青岛市公共图书馆联合目录 OPAC 侦察（2026-10-02 实抓）——降级待调研

站点:`http://124.129.202.157/opac/index`。馆名全称:页面头部与 meta keywords 均自报
「**青岛市公共图书馆联合目录**」——不是单一「青岛市图书馆」,而是全市联合目录,
libcodeMap 共 26 个馆码(主馆「青岛市图书馆」馆码 `QT`,另有市南/市北/李沧/崂山/
城阳/西海岸新区/即墨/平度/胶州/莱西等区级馆、城市书房分馆、党校/检察院等
非典型成员,原值照登见 holding.json)。技术组件:图创 Interlib
(首页含「图创」「interlib」指纹,版权行 interlib.com.cn)。

**结论:降级待调研。** 检索入口 `/opac/search` 被滑动验证码墙拦截(新会话首个
检索请求即触发,非限速封禁),search_books 原语程序化不可用;检索是该城三原语的
入口,拦死即全城不可用。按规则停手不硬闯(滑动验证需图像识别+轨迹模拟,属硬闯)。
详情页与馆藏 JSON **开放且与家族解析器零改动兼容**,一旦检索通道可用即可快速接入。

## 检索入口:滑动验证码墙(search_captcha.html 原样存证)

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

**因此青岛搜索结果页结构(bookmeta 容器、总数文案、分页锚点、express_isbn 属性)
全部未验证**,无搜索结果页 fixture。站点其余页面均为同款 Interlib 模板,推测同构,
但必须待检索通道可用后实抓确认,不预设。

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

无搜索结果页 fixture(被验证码拦截,未能实抓)。

## 侦察请求清单(共 9 次,全部只读 GET,间隔 ≥2 秒,遇验证码即停手)

1. `/opac/index`(匿名)→ 200,493KB 首页,馆名与 Interlib 指纹确认
2. `/opac/index`(cookie jar)→ 200,取得 JSESSIONID + IFCCAS_3RD_TOKEN
3. `/opac/search?q=三体&…rows=10&page=1`(匿名)→ 200 验证码页
4. `/opac/search?q=三体&…`(带会话+Referer)→ 200 验证码页(判定:常态门禁)
5. `/opac/book/1`(无效 id 探测)→ 500
6. `/opac/api/holding/1?limitLibcodes=&isCluster=` → 200,空 holdingList
7. `/opac/ranking/bookLoanRank` → 200,取得真实 bookrecno
8. `/opac/book/177071` → 200,详情页 fixture
9. `/opac/api/holding/177071?limitLibcodes=&isCluster=` → 200,馆藏 fixture

## 后续调研方向

- 定期探测验证码策略是否变化(时段性/策略调整);策略一放开即可按家族范式快速接入:
  详情与馆藏已验证零改动兼容,只欠搜索页实抓(bookmeta/总数/分页锚点确认)。
- 调研「青岛市公共图书馆联合目录」是否存在其他开放检索入口(如省级联合目录平台、
  移动端 API),若有可评估作为检索通道。
- 若馆方提供白名单/接口授权,直接接入。
