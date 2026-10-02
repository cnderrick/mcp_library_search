# 南京(金陵)实抓侦察记录

实抓时间:2026-10-02,共 28 个请求(预算 ≤40),间隔 ≥2.5 秒,全程未遇验证码/401。

## 系统判定(关键 pivot)

原任务目标是金陵图书馆自研 PHP OPAC(`opac.jllib.cn`,「金陵图书馆书目检索系统」,
页脚 OPAC v5.6.1.240429,江苏汇文授权)。**实测该站 /opac/ 与 /top/ 下所有业务页
整体登录墙**,匿名程序化不可行:

- `GET /opac/search_adv.php` → 302 `../reader/login.php?msg=login_to_continue`
  (loginwall_search_adv.headers.txt,响应体 loginwall_redirect_body.html);
- `GET /opac/search.php`、`GET /opac/`、`GET /top/top_lend.php` → 同样 302
  (loginwall_search_php.headers.txt、loginwall_opac_dir.headers.txt、
  loginwall_top_lend.headers.txt);
- 站点根路径 `GET /` → 200,146 字节 JS 跳转壳 → `./opac/presearch.php`
  (root_js_redirect.html),而 `GET /opac/presearch.php` 同样 302 登录
  (loginwall_presearch.headers.txt)——即真实检索入口也锁;
- 先带 PHPSESSID 会话再请求 search_adv.php,302 依旧(带会话不解锁);
- `/reader/` 首页(home.html)本身就是登录页外壳,先期调研看到的「公开检索界面」
  只是它导航菜单里的链接,点进去全部锁登录。

按纪律未绕行。**钉死事实一:金陵自研 PHP OPAC(opac.jllib.cn/opac/*)整体
登录墙——全部业务路径 302 → reader/login.php,先期调研(2026-10-02-uopac.md
§2)看到的「公开检索界面」只是登录页外壳的导航菜单,不是可用的匿名检索入口。**

**但金陵官网首页「馆际借阅」外链指向金陵自己运营的联合目录
`http://uopac.jllib.cn/uopac/`(汇文「南京市公共图书馆书目全文检索」v1.0,
uopac_home.html 64 字节 meta-refresh → `s/search.action`),匿名全通**,成员馆含
金陵图书馆 + 12 个区馆(栖霞/江宁/浦口/江北新区/六合/建邺/鼓楼/雨花台/高淳/
溧水/秦淮/玄武少儿)。三原语全部在该系统上匿名打通。

**钉死事实二:南京 uopac 与扬州 uopac 同为汇文 uopac 系统,但南京站无
扬州站那套 JS AES 加密 Cookie(securitycam)反爬墙——同系统、不同站点、防护
不同(扬州全路径只回 2.5KB JS 壳,南京裸 GET 即回真页)。将来评估其他汇文
uopac 站点时,防护必须逐站实测,不能按系统家族推定。**

范围经协调者批复(2026-10-02):全市联合目录(金陵+12 区馆),不做金陵-only
收窄,所在馆字段每条照实标注;book_id 用 uopac 原生数字 id 不加前缀(南图
ALEPH 已因验证码墙搁置,将来解锁照天津模式加源合并);分面参数可一键锁
金陵,见下。

## 一、检索:GET /uopac/s/search_result.action

表单(uopac_search.html):`action="/uopac/s/search_result.action" method="get"`,
字段 `q`(maxlength=80)+ `meta` 单选:

| meta | 含义 |
|---|---|
| 20 | 任意 |
| 11 | 题名(表单默认勾选) |
| 12 | 责任者 |
| 13 | 出版社 |
| 14 | ISBN |
| 15 | 主题词 |
| 16 | 丛书名 |

适配器策略:普通关键词 `meta=20`(任意),ISBN 形态关键词 `meta=14`(见 ISBN 节)。
分页参数 `page`(从 1 起,GET)。另有分面参数 `fkey=facet_libs&fval=JL` 可把结果
锁定到金陵图书馆(uopac_result_santi_jl.html,23 项,与未过滤页分面计数一致);
分面下翻页链接原样保留 fkey/fval。**当前适配器不加分面(全市联合),分面仅作
侦察证据与将来开关。**

### 结果页结构(uopac_result_santi.html,q=三体&meta=20&page=1)

- 总数:`<div id="found">` 内 `有 <font color="red">59</font> 项符合<font color="red">"三体"</font>的查询结果`
  → total_results=59(源站给真实总数,与重庆不同)。
- 每页固定 20 条,**无每页条数参数**(表单无此控件,也未见 pageSize/rows 参数;
  适配器 limit 参数对源站无效,原样返回整页,数据边界照实)。
- 条目锚点 `<div class="searchcontent">`:

```html
<h2>1.<a target="_blank" href="/uopac/s/detail.action?id=4386216">三体问题 </a></h2>
<p style=color:#666;>汪家訸编著 / 科学出版社  /  / 1961</p>
<p>　　〓=[讠禾](he) </p>
<p style=color:#666;><strong style="color:#006600;">所在馆：</strong>
        金陵图书馆
      &nbsp;&nbsp;
</p>
```

  - book_id = `detail.action?id=` 的数字 id;题名尾部常带空格,_clean 去掉;
  - 第二个 `<p style=color:#666;>` 是元信息行,固定 4 段斜杠分隔:
    `责任者 / 出版社 / ISBN / 出版年`,空段留空(如 `… / 科学出版社  /  / 1961`,
    ISBN 空;`… / 浙江人民美术出版社  / 9787534073304 / 2019`,ISBN 无连字符)。
    责任者本身可能含 `/` 之外任意字符,解析按「末三段为出版社/ISBN/年,其余
    拼回责任者」拆;
  - 第三个 `<p>` 是提要摘句(列表页不入库,详情页有全文);
  - `所在馆：` 后是持有该记录的成员馆名列表(&nbsp; 分隔,可多个,如
    uopac_result_santi_jl.html 里《三体》中的物理学 → 金陵图书馆+六合区图书馆)。
    适配器把它拼进 availability_summary(前缀「所在馆：」、馆名间「、」)——
    这是列表页唯一的可获性信息,原值照登。
- 分页区 `<div id="num">`:`<b><font color=red>1</font>&nbsp; / &nbsp;<font color=black>3</font></b>`
  = 当前页/总页数,另有 首页/下一页/末页 链接(page=N 形态)。
- **空结果页**(uopac_result_empty.html,q=9787229100605&meta=14):found 区
  `有 0 项`,0 个 searchcontent,**无 `<div id="num">` 分页区**——解析器对
  num 缺失回退 `ceil(total/20)`。
- 页面尾部有 `showHoldings(id,school,url,marcNo)` JS(type=simple 的
  ajax_holding),但结果页条目上无任何调用点(模板残留),列表页无单册状态。

### jsessionid URL 重写(真网冒烟抓到的关键 quirk,2026-10-02)

**客户端不带 Cookie 时,Tomcat/Struts2 会把页面里所有生成的 action URL 重写为
`detail.action;jsessionid=E59E86E8…?id=4386216` 形态**(uopac_result_santi_bare.html,
裸抓取,109 处 jsessionid;侦察期 curl 带了 cookie jar,服务器发干净 URL,故
uopac_result_santi.html 无此形态)。适配器是无状态裸请求,实网必然命中重写
形态:条目解析正则必须容忍 `detail.action` 与 `?id=` 之间的任意 jsessionid
段(`detail\.action[^?]*\?id=(\d+)`)。首版正则照带 Cookie fixture 写死
`detail.action?id=`,单测全绿、真网冒烟 0 条目(总数/分页正常,唯 books 空)
——教训:无状态客户端的 fixture 必须裸抓取。num 分页区、found 总数、条目
块锚点(searchcontent/clear div)不受重写影响。**详情页裸抓形态
(uopac_detail_jl_bare.html)只有 logo 链接与表单 action 两处被重写,
span#data 的 ajax_holding URL 保持干净**,tab 解析无需特判;ajax 响应本就
裸请求实证过(逐字节同带会话)。

### ISBN 索引行为(重要 quirk,4 个请求实证)

ISBN 索引按**存储原样字符串前缀匹配**,且各成员馆 MARC 存储形态不一(同页
既有 `978-7-229-10060-5` 也有 `9787534073304`):

- `q=9787229100605&meta=14`(无连字符)→ 0 项(该 ISBN 两条记录都存带连字符);
- `q=978-7-229-10060-5&meta=14` → 2 项(uopac_result_isbn_hyphen.html);
- `q=978-7-229&meta=14`(前缀)→ 1 项(uopac_result_isbn_prefix.html,证明
  是字符串前缀语义);
- `q=978 7 229 10060 5&meta=14`(空格)→ 0 项(不分词);
- `q=978*7*229*10060*5&meta=14` → 2 项(uopac_result_isbn_wild.html,**支持
  `*` 通配**);
- `q=9*7*8*7*2*2*9*1*0*0*6*0*5&meta=14`(每数字间插 `*`)→ 2 项,与带连字符
  精确检索同结果(uopac_result_isbn_wildcard.html)。

**适配器 ISBN 策略**:关键词形态判 ISBN(去连字符后 13 位 978/979 开头或
10 位)→ 去连字符取纯数字,每数字间插 `*` 作 meta=14 查询。子序列匹配下
13 位查询命中 13 位存储即数字全等(通配只吸收连字符),不猜连字符位置、
覆盖两种存储形态;ISBN-10 查询同理只命中 ISBN-10 存储。无连字符 ISBN 走
meta=20(任意)实测也是 0 项(uopac_result_empty.html 即此请求),故任意索引
不能兜底 ISBN。

## 二、详情:GET /uopac/s/detail.action?id={book_id}

uopac_detail_jl.html(id=3911408《三体 典藏版》,9 个成员馆持有)、
uopac_detail_santi.html(id=4308867《三体》,仅江宁区图书馆持有)。

- 书目字段是 `<dl class="booklist"><dt>标签:</dt><dd>值</dd></dl>` 序列,标签集
  (随记录变化,非全出现):题名/责任者、出版发行项、ISBN、载体形态项、丛编项、
  个人责任者、学科主题、中图法分类号、一般附注、提要文摘附注、使用对象附注。
- `题名/责任者:` 值形如 `三体:典藏版/刘慈欣著`——按**第一个 `/`** 拆题名与
  责任者(ISBD 分隔符语义);责任者原值照登(含「著」尾)。
- `出版发行项:` 形如 `重庆:重庆出版社,2016` 或 `重庆:重庆出版社,2015.6`
  → 出版社=去地点前缀去年份尾(同深圳/重庆 _clean_publisher),出版年取
  4 位年份。
- `ISBN:` 存储原样(此例带连字符),原值照登。
- `提要文摘附注:` = 内容简介(summary),可缺失 → 空串。
- **详情页无「索书号」字段**(中图法分类号 I247.5 是分类号不是索书号,单册
  索书号在馆藏表里)→ 照重庆先例 `call_number=""`,不拿分类号冒充。
- 缺失题名的响应(如 id 无效)→ 视为未找到,抛 RuntimeError。

### 馆藏 tab 结构(详情页内)

```html
<div id="tabs">
  <ul>
    <li><a href="#loca_JL">金陵图书馆</a></li>
    <li><a href="#loca_PK">浦口区图书馆</a></li>
    ...
  </ul>
  <div id="loca_JL">
    <h4 id="tabs_infobar">文献类型：中文图书　　　　记录标识号：0001167952</h4>
    <span id="data" >ajax_holding.action?type=full&url=http%3A%2F%2Fopac.jllib.cn%2Fopac%2Flibsys_view.php%3Fmarc_no%3D0001167952%26libCode%3DJL&lib=JL&id=3911408</span>
    <br/>
  </div>
  ...每馆一个 div,无嵌套 div...
</div>
```

- 每个持有馆一个 tab:li 给馆名(loca_ 码 → 中文名映射),div 内 `span#data`
  是**相对 URL**,前端 jQuery tabs 切换时 load 它。`&` 在实抓里是裸的,但页面
  JS 有 `replace(/&amp;/g,"&")` 防御 → 解析统一 html.unescape。
- span 的 `url=` 参数是成员馆自己 OPAC 的 `libsys_view.php?marc_no=…&libCode=…`
  (金陵是公网 opac.jllib.cn,区馆多为 192.168.x/公网 IP 混布)——**由 uopac
  服务端代理抓取**,成员馆内网地址客户端不可达也不需要可达。

## 三、馆藏:GET /uopac/s/ajax_holding.action?type=full&url={代理目标}&lib={馆码}&id={book_id}

- **匿名、无会话**:不带任何 Cookie/Referer 的裸 GET 与带会话请求返回
  **逐字节相同**(holding_bare_no_cookie.headers.txt,200;diff 实证 IDENTICAL)
  → 适配器可完全无状态(不需要 CookieJar,与重庆不同)。
- **金陵图书馆馆藏可匿名取**:金陵自站 /opac/ 整体登录墙,但 uopac 服务端代理
  `opac.jllib.cn/opac/libsys_view.php` 不受影响(uopac_holding_jl.html,13 册,
  含总馆/地铁分馆/街道分馆)。即 libsys_view.php 不在金陵登录墙内(或其代理
  路径被豁免)——事实如此,机制未深究,不绕墙。
- 响应是汇文标准单册表(uopac_holding_jl.html 金陵 13 册、uopac_holding_jn.html
  江宁 24 册):

```html
<table class="table-line">
  <tr align="center" bgcolor="#F5F8F9"> 表头:索书号/条码号/年卷期/校区/馆藏地/馆藏书刊状态 </tr>
  <tr align="center" bgcolor="#FFFFFF">
    <td width="10%" >I247.5/30762</td>
    <td width="15%" >00830387</td>
    <td width="15%" ></td>
    <td width="10%" >金图分馆</td>
    <td width="20%" >地铁分馆·新街口</td>
    <td width="20%" ><font color=green>可借</font></td>
  </tr>
  ...
  <tr align="left">...可借 / 馆藏 (2 / 13) + 「书所在馆OPAC查看」链接...</tr>
  <tr align="left">...不可申请：请先登录！...</tr>
</table>
```

- 单册行锚点:`<tr align="center" bgcolor="#FFFFFF">` + 6 个 `<td>`(表头行
  bgcolor=#F5F8F9、汇总行 align="left",天然排除)。
- 字段映射:索书号→call_number;校区(金陵=金图总馆/金图分馆,江宁=总馆/分馆)
  与馆藏地→location(两列都非空时以空格连接,如「金图分馆 地铁分馆·新街口」;
  契约无对应字段的 条码号/年卷期 舍弃不入库);状态→status 原值照登。
- **状态词表**(两馆实抓所见):`可借`(绿色 font)、`借出-应还日期：YYYY-MM-DD`
  (全角冒号,纯文本)。可借口径:`status == "可借"` → available=True;
  `借出-…` → False + due_date 提取(仅当「应还日期：」后跟标准 YYYY-MM-DD,
  否则空串不猜);**词表外一切状态保守 available=False,原值照登**。
- 汇总行 `可借 / 馆藏 (2 / 13)` 是页脚统计,不入库(单册行已覆盖)。
- 「不可申请：请先登录！」只影响预约申请动作,**不影响数据可见性**。
- tab 的 ajax 响应若无单册行(成员馆代理失败/空馆藏等,形态未实测)→ 该馆
  贡献 0 条,解析器容忍不抛错。

## 四、适配器设计约束(由此推导)

- 无状态轻量 client(urllib),模块级 `_client`,节流 4 秒/host(spec 定)。
  **源站偶发慢响应/传输中途停顿**:侦察 req16 30 秒仅收 34KB(重试成功),
  冒烟首跑 chunked 读取 60 秒无数据超时(重试成功)→ timeout 取 90 秒。
  **2026-10-02 改动**:南京并入南图源成为双源适配器后,本源的失败不再上抛——
  源级容错(≥1 源存活即返回)会把它降级成「只有南图结果」的静默部分结果,原设计
  「失败由调用方重试」的逃生口因此不存在了,所以重试下移到适配器:`_open` 对
  **网络类**错误重试一次(HTTP 状态错误是确定性的,不重试;每次重试照常节流)。
  实测(8 次连查):2 次遇到 ~90 秒停顿,均靠重试成功返回,合计 ~94 秒;
  0 失败。代价是停顿当次延迟翻倍,收益是不再静默少一个源。
- `search_books`:1 请求。meta=20/14 路由如上;total_results 实数;
  total_pages 优先 num 区,缺失回退 ceil(total/20);limit 对源站无效(边界照实)。
- `get_book_detail`:1 请求(detail.action)。
- `get_holdings`:1 + N 请求(N=持有馆 tab 数,9 馆的书 = 10 请求 ≈ 40 秒节流,
  多数书 1~3 馆)。library=tab 中文名,逐馆逐册展开。
- 错误信息前缀统一「金陵图书馆」(uopac.jllib.cn 是金陵运营的服务器;数据
  范围为南京全市联合目录,工具层描述另行说明)。
- book_id = `JL:` ＋ uopac 数字 id(2026-10-02 并入南图源时加前缀;裸数字 id
  走兼容垫片按 JL 成员路由);金陵成员 id 非纯数字 → 抛「book_id 格式应为
  uopac 数字 id」。

## 五、fixture 清单

| 文件 | 内容 |
|---|---|
| home.html / reader_home.headers.txt | opac.jllib.cn/reader/ 登录页外壳(200,8018B) |
| root_js_redirect.html | 站点根 200,JS 跳转 presearch.php |
| loginwall_*.headers.txt / loginwall_redirect_body.html | 五条登录墙 302 证据 |
| presearch.html | presearch.php 302 响应体 |
| uopac_home.html / uopac_search.html | uopac 入口 meta-refresh / 检索表单页 |
| uopac_result_santi.html | 主检索 fixture:三体 meta=20 page=1,59 项 20 条 1/3 页(curl 带 cookie jar,URL 干净) |
| uopac_result_santi_bare.html | 同查询**裸抓取**(无 Cookie):jsessionid URL 重写形态,适配器实网命中的就是它 |
| uopac_result_santi_p2.html | 三体 page=2,20 条,与第 1 页无重复 |
| uopac_result_santi_jl.html | 三体 + 分面 fval=JL,23 项 2 页(分面证据/多馆条目) |
| uopac_result_empty.html | 空结果页(0 项,无 num 分页区) |
| uopac_result_isbn_hyphen.html | 带连字符 ISBN meta=14 → 2 项 |
| uopac_result_isbn_prefix.html | ISBN 前缀 978-7-229 → 1 项(前缀语义证据) |
| uopac_result_isbn_wild.html | 粗通配 978*7*229*10060*5 → 2 项 |
| uopac_result_isbn_wildcard.html | **全数字通配**(适配器实际策略)→ 2 项 |
| uopac_detail_jl.html | 详情 id=3911408,9 馆 tab,字段全(含提要) |
| uopac_detail_jl_bare.html | 同详情**裸抓取**:jsessionid 只重写 logo/表单两处,span#data 干净 |
| uopac_detail_santi.html | 详情 id=4308867,单馆(江宁)tab |
| uopac_holding_jl.html | 金陵馆藏 13 册(2 可借/11 借出带应还日期) |
| uopac_holding_jn.html | 江宁馆藏 24 册(22 可借/2 借出) |
| holding_bare_no_cookie.headers.txt | 无 Cookie 裸请求馆藏 200 证据 |

## 六、请求清单(28 个,侦察阶段)

1 /reader/ 首页;2 /opac/search_adv.php(302);3 /reader/(会话);4 search_adv.php
带会话(302);5-7 search.php、/opac/、top_lend.php(均 302);8-9 根路径(200 JS 壳)、
/opac/index.php(404);10 presearch.php(302);11 uopac.jllib.cn/uopac/(64B);
12 s/search.action(表单页);13 search_result 三体 page1;14 detail 4308867;
15 ajax_holding JN(24 册);16 JL 分面(30 秒超时截断,重试见 17);17 JL 分面
重试(完整);18 detail 3911408(9 tab);19 ajax_holding JL(13 册);20 ISBN
无连字符(0 项);21 ISBN 带连字符(2 项);22 ISBN 无连字符 meta=20(0 项);
23 ISBN 空格分隔(0 项);24 ISBN 前缀(1 项);25 粗通配(2 项);26 全数字通配
(2 项);27 裸无 Cookie ajax_holding(200,逐字节同 19);28 三体 page2。

## 七、真网冒烟(适配器实调,2026-10-02,全过)

冒烟阶段总请求 16(预算 ≤16):首跑 1(暴露 jsessionid 问题)+诊断实抓 2
(结果页/详情页裸形态,已入库为 *_bare fixture)+ 二跑 1(源站传输停顿 60 秒
超时,quirk 实证)+ 三跑 12(全链路成功):

- `search_books("三体")`:total_results=59,page=1,total_pages=3,has_next=True,
  20 条;首条 4386216《三体问题》汪家訸编著/科学出版社/1961,
  availability_summary=「所在馆：金陵图书馆」。
- `get_book_detail("3911408")`:《三体:典藏版》刘慈欣著/重庆出版社/2016/
  ISBN 978-7-229-10060-5/call_number 空/提要有全文。
- `get_holdings("3911408")`(默认 only_available=True):9 册可借,跨三馆合并
  ——金陵图书馆 2(地铁分馆·新街口/锁金村街道分馆,索书号 I247.5/30762)、
  高淳区图书馆 3(总馆 图书外借,I247.55/77)、鼓楼区图书馆 4(基本书库/
  开架借阅室,I247.55/115);各成员馆索书号体系独立,原值照登;9 个 tab 串行
  抓取(4 秒节流,全程约 1 分钟)。
- 未做真网验证项:ISBN 通配路由(侦察 req25/26 已用与适配器同形 URL 实证
  命中;冒烟预算让位给多馆馆藏链路)、page=2 翻页(侦察 req28 实抓过)。

## 八、冒烟教训(记录)

1. **jsessionid URL 重写**:侦察期 curl 带 cookie jar 抓的 fixture 是干净 URL,
   适配器裸请求实网拿到的是 `detail.action;jsessionid=…?id=` 重写形态,首版
   正则单测全绿、冒烟 0 条目。修复=正则容忍 + 裸抓 fixture 补测
   (uopac_result_santi_bare.html / uopac_detail_jl_bare.html)。
2. **源站传输停顿**:chunked 读取可停顿 ≥60 秒(重试即好),timeout 90 秒。
   2026-10-02 双源改造后网络类错误改由适配器重试一次(理由与实测见第四节),
   HTTP 状态错误仍不重试。
