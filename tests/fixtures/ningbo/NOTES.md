# 宁波 tcc-opac 全市联合目录侦察＋前端逆向记录（2026-10-02 复测突破）

站点:`https://opac.nblib.cn/999`(Vue2 SPA 壳)→ 真实后端
`https://opac.nblib.cn/api/tcc-opac/999/...`(图创 tcc-opac,Java/Spring)。
馆名口径:全市联合目录,成员含慈溪/奉化等区县馆与城市书房(馆藏记录馆名带
「慈溪_」类下划线前缀,源站原值照登)。技术组件与穗杭的图创 Interlib 是
**不同产品线**(纯 JSON API + JWT 访客令牌,非 HTML+holding JSON),独立适配
`adapters/ningbo.py`,不复用 interlib/ 家族。

**结论:已接入。** 2026-10-02 上午调研(res-spa)时 `bookSearch` 返回
「系统出现异常」判暂缓;同日复测发现异常消失(返回 code:200「操作成功」但
data:null)——站点已恢复,剩下的是参数形态问题。转为**前端 JS 离线逆向**
(零源站请求)查明真实三原语端点后实测打通。

## 逆向路径(全部离线,基于 /tmp/lib_research/ 调研期已下载的 JS)

1. `nb_app.js`(app.08f9b03f.js,live 复抓 hash 未变)API 层 → webpack 模块
   `888e`:导出 `f` = `POST {base}/search/`(注意尾斜杠)、`e` =
   `POST /service/hold/pagelist`(data)、`h` = `POST /service/biblios/getbyid`
   (**params**,即查询串形态,空 body)。axios 拦截器注入 `ACCESS-TOKEN`
   (localStorage accessToken),`code==1003` 触发 `window.onGetToken()` 重取。
2. 路由懒加载映射:`/refineResults`(检索结果页)= chunk-5a920f2a 模块 `0a03`;
   `/bookDetails` = chunk-3f5b34c0(1.1MB,含 echarts)模块 `e4fa`(**无引号键**,
   `"e4fa":function` 正则搜不到,按 `e4fa:function` 才命中)。
3. 模块 `0a03`(RefineResults):检索调用 `Object(d["f"])(Object(Ct["a"])(searchLists))`;
   `searchLists` 字段 = `current/size`(分页,来自 paginationOpt)、`searchWay`、
   `sortWay:"score"`、`sortOrder:"desc"`、`hasholding`(false→0/true→1)、`q`、
   `research_q:[""]`、`facetFieldSearch`(空值过滤后 {})。响应消费
   `r.bookList/r.numFound/r.curlibcode`;`r.code∈{43001,-1,-402}` → 前端弹
   **滑块验证**(verifySlide 组件在 chunk 内;code 判断即风控触发信号)。
4. 模块 `673c`(Ct):`Ct["a"]` = 空字段过滤器(空串/空数组剔除,0/false 保留);
   `Ct["c"]` = searchWay 码表:marc=任意词、title=题名、title200a=正题名、
   isbn=ISBN/ISSN、author=著者、subject=主题、class=分类号、ctrlno=控制号、
   orderno=订购号、publisher=出版社、callno=索书号(与 Interlib 同款词表)。
5. 模块 `e4fa`(BookDetails + HoldingTable):详情调用
   `Object(d["h"])({id:bibliosId, fields:"300a,314a,327a,330a"})`,消费
   `data.biblios`(主行)+`data.fieldItem`(UNIMARC 字典:200$a 题名/200$f 责任者/
   010$a ISBN/010$d 价格/100$a 定长/101$a 语种/690$a 分类)+`data.fields`
   (请求的四个附注字段直映:330a 提要/327a 内容/300a 一般/314a 著者)。
   馆藏调用 `Object(d["e"])({current:1,size:500,bibliosId})` →
   `data.records[]` 单册级。`bibliosId` 就是检索条目的 `id`(雪花字符串)。

## 三原语实测(2026-10-02 下午,均 HTTP 200)

| 原语 | 端点 | 请求形态 | 响应要点 |
|---|---|---|---|
| 令牌 | `POST /system/user/getOpenApiAccessToken` | body `{}`,匿名 | `{code:200,data:{token:JWT,expiresIn:"2523"}}`(秒级**字符串**,调研期见 5108,浮动) |
| 检索 | `POST /search/` | body 见上;头 `ACCESS-TOKEN` | **成功响应无 code 字段**;顶层 `numFound`(**字符串**'375',hasholding=1 口径)、`bookList[]`(id/orgId/title/author/pubdate/publisher/isbn/price/booktype/classno/callno…)、`nextPage/start/size`、facet 数组(booktypes/curlibcode/fsubject…) |
| 详情 | `POST /service/biblios/getbyid?id=&fields=300a,314a,327a,330a` | 查询串参数＋空 body | `data.biblios`(49 键,稀疏)+`data.fieldItem`+`data.fields`+`data.content`(CNMARC 全字段 JSON 串,子字段标记 ▼) |
| 馆藏 | `POST /service/hold/pagelist` | body `{current:1,size:500,bibliosId}` | `data.records[]`(statename 原生状态词、curOrgName/curlocalName 当前馆/地、orgName/orglocalName 所属馆/登记地、callno、barcode、returnTime/loanTime 完整时间戳、cirTypeName、mediaTypeName、volinfo)、`data.total` |

状态词实测:`state=2/statename=在馆`、`state=3/statename=借出`(借出带
returnTime,如 '2020-01-07 15:36:21'——老数据原值照登)。可借判定:
statename==「在馆」→ True,词表外保守 False。

## 数据边界(原值照登,不做预设判断)

- **`hasholding` 语义(2026-10-02 复测钉死)**:`1`(或缺省)＝只看有馆藏、
  `0`＝只看无馆藏,两集合**不相交**,取 1 与缺省结果完全一致(逐条比对)。
  实测「三体」1→375 条、0→32 条;「活着」1→3594、0→245;「红楼梦」
  1→6633、0→558;窄关键词「一说《三体》」1→1 条、0→4 条,两集合无一重合。
  适配器固定传 `1`;传 0 会把结果集限制在空壳子集上——**这是此前的接入
  缺陷**,原记录把 0 当成「前端默认」,实为前端「在馆记录」复选框的取消态
  (组件 data 初值与 resetData 均为 `!0`,请求构造 `!1===h ? 0 : 1`)。
- **聚合条目**:新导入雪花 id(1849… 段,如《三体》1849291138475802626,
  booktype 同为 1)无本地书目,getbyid 返回 `code:-1「数据不存在」`、
  pagelist 返回 200+0 条——非故障。它们属「无馆藏」子集,`hasholding=1`
  的检索不会返回。老段 id(670…,《活着》670379643136847935)三原语全通。
- 条目字段富化程度随子集不同:有馆藏条目实测带 publisher/pubdate/isbn/
  classno/callno(《三体》670380481158787137:重庆出版社 2017,I247.55/251V1);
  「无馆藏」子集的条目 publisher/pubdate 常为空串。
- 详情 biblios 主行稀疏(《活着》publisher/pubdate/page/shelfno 全 null),
  CNMARC 210(出版项)/215(载体)子字段全空(`▼a▼c▼d`)——老编目数据缺失,
  出版年兜底从 fieldItem `100$a` 定长字段取(d2003 → 2003)。
- title 带原生句点(「活着．」)、author 带未闭合方括号(「余华[著」)——
  CNMARC 著录原值照登,不清洗。
- 索书号:classno(690$a,I247.57)是分类号**不冒充**索书号(南京口径);
  biblios.shelfno 常 null → detail.call_number 常空串;单册完整索书号在
  馆藏 callno(「I247.57/6289」)。
- 简介:fields 四附注全空串(该样例);有值时的形态未验证(待有样例)。
- 馆藏一页 500 册封顶(前端同款);超出场景未验证。
- booktypes 码表(`/format/getBookTypeList`):typeNo 1=图书(其余类型样例
  未见,原值存 booktypes.json)。

## 风控与令牌生命周期

- 滑块验证触发码(前端对 /search/ 的判断):`43001 / -1 / -402`。程序化
  访问命中即停手抛错,不硬闯(与青岛滑动墙同一纪律)。复测期约 14 请求
  未触发。
- 令牌过期:`code==1003` → 重取一次重试(前端拦截器同款)。expiresIn 秒级,
  适配器提前 60s 刷新。
- `bookSearch` 端点(开放平台形态)与 `/search/`(前端形态)不是同一接口:
  前者参数不明且历史「系统异常」,后者已逆向打通——适配器只用后者。
- 姊妹站 bopac.nlic.cn(宁波大学园区图书馆)需 orgId 租户头,orgCode 不可
  枚举,维持不接入(res-spa 调研结论未变)。

## Fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `search_santi.json` | `POST /search/` q=三体,searchWay=marc,hasholding=0,size=10 | numFound='32',bookList 10 条(含聚合条目 1849… 段) |
| `search_huozhe_hasholding.json` | `POST /search/` q=活着,hasholding=1,size=10 | numFound='3594',curlibcode facet 有值,条目 callno 有值 |
| `detail_huozhe.json` | `POST /service/biblios/getbyid?id=670379643136847935&fields=…` | 《活着》biblios+fieldItem+fields+content(CNMARC) |
| `holdings_huozhe.json` | `POST /service/hold/pagelist` bibliosId=670379643136847935 | 9 单册:7 在馆(慈溪_宗汉/桥头、奉化区)+2 借出(慈溪_周巷,returnTime 2020) |
| `booktypes.json` | `POST /format/getBookTypeList` | typeNo/typeName 码表(1=图书) |

## 复测＋逆向请求清单(2026-10-02,共约 14 次,间隔 ≥2.5s,全部只读)

1. 令牌 ×2(上午调研已验,下午复测重取)
2. `bookSearch` 探测 ×1(code:200 data:null → 判定站点恢复、参数不明)
3. SPA 壳 `/999` ×1(app.js hash 08f9b03f 未变,确认前端未重部署)
4. chunk JS ×2(chunk-3f5b34c0/520e639a,重下载后与调研期副本 md5 相同)
5. `/search/` ×2(三体 hasholding=0 ✅;活着 hasholding=1 ✅)
6. `/format/getBookTypeList` ×1
7. `bookDetails` 误探 ×1(404,网关 path=/999/bookDetails——该端点不存在,
   真实详情是 getbyid)
8. `hold/pagelist` 误参 ×1(id 代 bibliosId → 25s 超时挂起,**参数名错误会
   挂起**,适配器 timeout 30s 止损)
9. `getbyid`+`pagelist` 三体聚合 id ×2(数据不存在/0 条 → 边界确认)
10. `getbyid`+`pagelist` 活着 ×2(✅ 全通)

## 适配器真网冒烟(2026-10-02,7 请求)

`search_books("活着", limit=5)` → total=245/前 3 均聚合条目;
`get_book_detail(670379643136847935)` → 《活着．》/余华[著/9787506365390/
publish_year=2003(100$a 兜底)/call_number 空;`get_holdings(…, False)` →
9 条(7 在馆前排+2 借出 due 2020-01-07);`only_available=True` → 7 条;
聚合 id 详情抛「未找到该书详情(数据不存在)」、馆藏 0 条。全链路 ✅。
