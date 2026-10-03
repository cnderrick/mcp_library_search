# 数据源接入作业指导书（子 agent 复用提示词）

> 本文件是「主线程摸底 → 分组 → 派子 agent 对接」这套流程的可复用提示词资产。
> 主线程**不亲自接入**，只把「公共骨架 ＋ 家族附注 ＋ 城市数据行」拼进子 agent 的
> 提示词；子 agent 按单城循环交付并**按批 commit**。每次跑完把踩到的新 quirk 回填
> 本文件，提示词随之优化——这是降费的关键：家族内提示词只维护一份。

登记正文见 [cn.md](../../data-sources/cn.md)；字段级结论见 `tests/fixtures/<city>/NOTES.md`。

## 一、分工

| 角色 | 职责 |
|---|---|
| 主线程 | 从 [cn.md](../../data-sources/cn.md) 取「📋 计划」条目（当前 85 条），按「技术组件」归类到家族，挑一批，把本文件第二节骨架＋第三节家族附注＋第四节城市数据行拼成子 agent 提示词 |
| 子 agent | 收到提示词后按第五节单城循环实网对接，交付代码＋fixture＋测试＋文档，按批 commit；每城一条回报 |

## 二、公共骨架（逐批原样贴给子 agent）

给子 agent 的提示词固定以这段话开头，再追加家族附注与城市数据行：

```
你是本仓库的开发工程师，负责把 cn.md「📋 计划」中的一批城市接入。
严格执行以下硬约束（AGENTS.md 铁律）：

1. server.py 是薄层：业务逻辑只进 adapters/、interlib/、vendor/。
2. 契约测试的模块级 _client 是适配器形态的硬契约：公开三原语必须经由
   adapters/cn/<city>.py 的模块级 _client 取数，不得直连家族函数，否则 mock 落空、测试真打图书馆网站。
3. 单测不打真实图书馆网站：fixture + monkeypatch。
4. 中文注释、NOTES.md、commit 信息一律全角标点。
5. 解析器以 tests/fixtures/<city>/NOTES.md 为准；实抓与 NOTES 不符先改 NOTES 再改代码。
6. 不确定数据不做预设判断：原值照登，不猜语义。
7. 不改家族模块对外签名；城市差异只允许以 Config 带默认值的字段（quirk）新增。
8. 真网冒烟克制：站点有限速（适配器内置节流）；遇 401/验证码立即停手上报，不硬闯。
9. 只读 GET 侦察；不注册、不登录、不提交表单。

工具：Read/Grep/Glob/Edit/Write/Bash。测试统一 `uv run pytest -q`，必须全绿。
每批跑完 git commit（中文全角标点），不 push、不打 tag、不发 PyPI。
```

## 三、家族附注（每家族一份，按批粘贴）

### 3.1 Interlib 家族（图创，`interlib/`）

- 家族模块 `src/mcp_library_search/interlib/`（`client.py`/`parser.py`/`__init__.py` 三原语）。
- 配置 `InterlibConfig(city, name_cn, base_url, …)`，quirk 字段（默认值即广州行为）：
  `curlibcode`、`pro2018`、`pro2018_cite_author`、`ctx`（默认 `/opac`）、`api_detail`、
  `solr_search`、`f_curlibcode`、`captcha`。
- 适配器照 `adapters/cn/dezhou.py` 同款薄包装（`_Holding` dataclass ＋ `_Client` ＋ `_client` 实例）。
- 新成员注册：`adapters/cn/__init__.py` 加 `from . import <city>` 与 `ADAPTERS["<city>"] = <city>`；
  `cn.md` 总览表状态改 ✅＋在「Interlib 家族」成员差异表加一行。
- quirk 判据（先试默认，命中再开开关）：
  - HTML 检索页 `/opac/search` 直连可用 → 默认模板，`api_detail=True` 即可。
    - **默认模板变体（铜陵实证）**：`bookmeta` 容器仍在，但著者/出版社锚点**无
      `author-link`/`publisher-link` class**，只在前置文本留「著者:」「出版社:」→ 家族
      `_SearchParser` 已加同层前置文本标签兜底（值取紧随的无 class 锚点，标签 div 闭合即
      失效），带 class 的城市仍优先按 class 命中；无需新增 quirk。
  - 详情页 HTML 截断或模板异常 → `api_detail=True`（走 `/opac/api/book/{recno}` JSON）。
  - 检索页返回 ~3.3KB「opac验证」滑动验证码页 → `solr_search=True`（走 `/opac/api/search`）；
    若该站内嵌 Solr 也不可用（`/opac/api/search` 404，或**回 403「bot detected」**，
    带 Referer/XHR 头仍拦，揭阳实证；或**连接被重置 `RemoteDisconnected`**、多次重试
    仍拦，湖北省图实证）→ `captcha=True`（命中即抛 CaptchaError，不破解）。
  - 应用上下文非 `/opac` → `ctx="/lib2"` 或 `ctx=""`（先探 `/opac/*` 是否 404）。
  - 新版页 `li.libBookLi`／`a.bkTxtTit` → `pro2018=True`（绍兴另需 `pro2018_cite_author=True`）。
  - **静态资源路径不可作模板判据**：检索页引用 `pro2018` 媒体目录（`/opac/media/pro2018/…`）、
    但结果条目仍是默认 `div.bookmeta`（泰安实证）→ **不要**开 `pro2018`，判据只认结果条目容器。
  - **域名停放前置排除**：`base_url` 域名解析到 `198.20.0.x` 域名停放段
    （晋中 `lib.jzstsg.com`→198.20.0.174、莆田 `opac.ptslib.com`→198.20.0.177 实证）→
    非馆方站点，直接判 ⛔ 不通，不必再探 `/opac/*`。
  - **停放段复核（2026-10-03 第八批）**：并非所有 `198.20.x.x` 都是停放——本批 fuzhou
    （`opcs.fzlib.org`→198.20.2.211）、sanya（`opac.sanyalib.com`→198.20.2.212）虽落在
    该段，但返回真实馆方服务（福州为真实 Interlib、三亚为 tcc-opac）；wuzhou
    （`www.wztsg.com`→198.20.2.213）则 82 端口连接超时零字节。故**判据以实抓响应为准**
    （页标题／meta keywords／接口是否可用），不单凭 IP 段一票否决；已知停放页表现为
    通用出售/跳转页或无响应（198.20.0.174/.177 等）。旧批 fuzhou 所记「198.20.2.5 停放段」
    已随域内 IP 变化失效，须重抓复核。
  - **误标为 Interlib 的 tcc-opac 城（三亚实证，2026-10-03）**：入口形如 `/opac/<SEG>`
    但返回 `opac-remould` Vue SPA（页标题「图书馆」、`/opac/static/js/app.*.js`，SPA 挂在
    `/opac/` 下），JS 里出现 `/api/tcc-opac`、`/system/user/getOpenApiAccessToken`、
    `/search/`、`/service/biblios/getbyid` → **实为 tcc-opac，转 3.5 家族**，不要在
    Interlib 里试探/新增 quirk。
  - 应用为**更新的 jishen 模板**（页标题「书目检索」、`solrpagination.js`、表单 POST
    `booklist.jsp`，`/opac/search` 404）→ **非家族模板，不接入**，回报主线程归入新分支
    （清远 `qingyuan` 实证）。
  - 应用为**老版 GLIS 模板**（页标题「图书检索系统」、GB2312、入口 `index.jsp`＋检索走
    GET `jdjsjg.jsp`、`/opac/search` 与 `/opac/api/*` 均 404）→ **非家族模板，不接入**，
    回报主线程归入新分支（开封 `kaifeng` 实证）。
  - 多租户云托管详情需带馆码 → `curlibcode="XXX"`；联合目录按馆过滤 → `f_curlibcode="XX"`。
  - 检索页验证码挡住但**详情/馆藏匿名可通**时仍作 ✅ 接入（`captcha=True` 或 `solr_search=True`），
    同乐山/揭阳先例；recno 可自首页推荐位等匿名页取得。

### 3.2 UILAS 老版家族（ILAS HTML OPAC，`uilas/`）

- 家族模块 `src/mcp_library_search/uilas/`；配置 `UilasConfig`。
- 入口形如 `/ILASOPAC/` 或 `/Index?target=0`；检索 `POST NTRdrBookRetr.do`，翻页 `nCurrentpage`
  且 SearchKey 双重 URL 编码；`book_id` 是裸 recno。
- 旧式 TLS（只支持静态 RSA kx 套件）→ `UilasConfig.ssl_ciphers="AES256-GCM-SHA384:AES128-GCM-SHA256"`
  （舟山实证，OpenSSL 3.5 默认不通）。
- 成员差异表在 `cn.md`「UILAS 家族（金华、舟山）」章。
- 适配器照 `adapters/cn/jinhua.py`／`zhoushan.py`。

### 3.3 新版 UILAS REST（`uilas_rest/`）

- 家族模块 `src/mcp_library_search/uilas_rest/`；配置 `UilasRestConfig`。
- 前端 Vue＋`/prod-api/*` JSON；检索 `GET /prod-api/bookSearch/search`，
  详情＋馆藏一步 `GET /prod-api/book/bookDetail?recno=`。
- 部分部署只认与站点同路径的 `Referer`（榆林实证：根路径 Referer 全接口 401）→
  逐站配 `UilasRestConfig.referer`。
- 适配器照 `adapters/cn/yulin.py`／`lanzhou.py`。

### 3.4 图星 LibStar Find（`libstar/`）

- 家族模块 `src/mcp_library_search/libstar/`；配置 `LibStarConfig`。
- **两个必需请求头**：`Referer`（任意值，缺失回 `errCode:9999`「系统访问中断」）与
  `groupcode`（缺失 HTTP 200 但 `numFound` 恒 0）。`groupcode` 由
  `POST /find/homePage/getGroupCode {mappingPath}` 查得（`data.groupCode`）。
- 检索 `POST /find/unify/search`；详情必须 GET `…/getBookDetail?recordId=`；
  馆藏 `POST /find/physical/groupItemsByLibCode`。
- `*.libsp.com` 是通配停放域，凭域名猜可达性会误判，须见真站特征或调通 API。
- 适配器照 `adapters/cn/hanzhong.py`（`groupCode=100121`）。

### 3.5 tcc-opac（`tccopac/`）

- 家族模块 `src/mcp_library_search/tccopac/`；配置 `TccOpacConfig`
  （`city`/`name_cn`/`base_url`/`referer` 四项，暂无其它 quirk）。
- 成员已含：宁波/济南/鄂尔多斯，**2026-10-03 增三亚 `sanya`**。
- 入口形如 `{host}/…/999`（宁波/济南/鄂尔多斯）；三亚是 `opac-remould` Vue SPA 挂
  `/opac/<SEG>`、真实 API 前缀 `/api/tcc-opac/<SEG>`，SEG 取自前端 JS 常量
  （三亚 `["SY","YCSTQG"]`，默认 `SY`）。**判据**：JS 出现 `/api/tcc-opac`、
  `/system/user/getOpenApiAccessToken`、`/search/`、`/service/biblios/getbyid` 即成。
- 纯 JSON＋JWT 访客令牌（`POST /system/user/getOpenApiAccessToken` 匿名即发，
  过期自动重取）。
- 检索 `POST /search/`（**尾斜杠**，`hasholding=1`＝只看有馆藏）；详情
  `POST /service/biblios/getbyid`；馆藏 `POST /service/hold/pagelist`。
- 滑块风控 `code ∈ {43001,-1,-402}` → 停手抛错，不硬闯。
- 数据边界：检索条目 `availability_summary` 恒空串；`biblios.shelfno` 为 null 时
  `call_number` 空串（`classno` 分类号不冒充索书号）。**源站可偶发 TLS/读超时**
  （三亚实抓令牌、getbyid 均出现过，重试即通），家族 timeout 30 秒止损、业务请求不重试。
- 适配器照 `adapters/cn/ningbo.py`／`jinan.py`／`sanya.py`。

### 3.6 InDigLib（重庆，独立实现，无共享家族）

- 无家族模块；照 `adapters/cn/chongqing.py` 复制独立实现（urllib＋CookieJar）。
- 入口 `/InDigLib/frontV2/SearchIndex!simple.action?opacType=local`；会话流程先 GET 拿
  JSESSIONID 再 POST `OpacMarcSearchSolr!simpleSearch.action`；翻页必须 GET 带 `pageNo`；
  馆藏走**根路径** `POST InDigLib/GetAsset.action`（`frontV2/` 前缀版有登录拦截）。
- 可借口径统一保守：无法确认在架的一律 `available=False`，原值照登。

### 3.7 超星系（智慧门户 wisweb／chaoxing）

- 无共享家族（已有门户只登记未接入）。先侦察门户页里 `wisweb／chaoxing` 变量与
  `/entry/page/…` 动态加载的书目检索入口；找到可编程 JSON 接口再评估独立实现
  （照深圳/浙江图书馆「自研 JSON 独立实现」先例），**不照搬**现有家族。
- 参考登记：`cn.md`「超星智慧门户（宿迁、连云港）」章。

### 3.8 SirsiDynix iLink

- 现有大连 `adapters/cn/dalian.py` 是**独立实现**（`/uhtbin/cgisirsi/`，ps token 会话，
  类重庆流程，节流 ≥4 秒/host），暂无 `ilink/` 共享家族。甘肃三城（省图/陇南/甘南）
  若实测同构，按家族先例抽 `ilink/` 模块，再让三城薄包装——**先侦察再决定是否抽象**。

### 3.9 未知系统（待侦）

先只做侦察、**不写 adapter**：抓首页＋找 `opac/search/检索` 入口，记录技术指纹
（meta keywords、静态资源路径、JS 全局变量、接口形态），回报后由主线程归入家族再排期。

## 四、城市数据行（当前 85 条 📋 计划，按家族）

> `标识` 为拟用城市键（拼音，冲突时加后缀）；`quirk` 为待试探项，实抓后回填确认。
> `实抓词` 统一「三体」，记录 `total_results` 与首条，写进该城 `NOTES.md`。
> 入口列省去 `{base_url}` 前缀的公共路径。带 ⚠️ 的条目为「旧批次曾判异常、本批重新升计划」，
> 实抓时优先复核。

### 4.1 Interlib 默认模板（44 城，首批主力）

| 城市 | 馆名 | 标识 | base_url | 入口 |
|---|---|---|---|---|
| 铜陵 | 铜陵市图书馆 | `tongling` | http://60.173.22.63:7075 | /opac/ |
| 安庆 | 安庆市图书馆 | `anqing` | http://39.145.39.67:8082 | /opac/ |
| 茂名 | 茂名市图书馆 | `maoming` | http://14.18.69.185:8082 | /opac/index |
| 清远 | 清远市图书馆 | `qingyuan` | https://elib.qylib.com | /opac/ |
| 中山 | 中山市图书馆 | `zhongshan` | https://opac.zslib.cn | /opac/index |
| 揭阳 | 揭阳市图书馆 | `jieyang` | http://61.146.124.30:8088 | /opac/index |
| 普宁 | 普宁市图书馆 | `puning` | http://www.pnlib.com:8088 | /opac/index |
| 东营 | 东营市图书馆 | `dongying` | http://60.214.234.201:81 | /opac/index |
| 烟台 | 烟台市图书馆 | `yantai` | http://144.123.23.246:8082 | /opac/ |
| 潍坊 | 潍坊市图书馆 | `weifang` | http://60.210.241.4:8080 | /opac/index |
| 泰安 | 泰安市图书馆 | `taian` | http://112.245.16.82 | /opac/ |
| 日照 | 日照市图书馆 | `rizhao` | http://58.59.43.7:38080 | /opac/ |
| 临沂 | 临沂市图书馆 | `linyi` | http://111.16.49.57:8888 | /opac/ |
| 聊城 | 聊城市图书馆 | `liaocheng` | http://218.57.211.26:8091 | /opac/index |
| 攀枝花 | 攀枝花市图书馆 | `panzhihua` | http://www.pzhlib.com.cn | 站内 interlibSSO／ifs/search；候选 host http://125.66.234.132:8180 |
| 石家庄 | 石家庄市图书馆 | `shijiazhuang` | http://120.211.62.194:8087 | /opac/index |
| 忻州 | 忻州市图书馆 | `xinzhou` | http://124.163.188.204:9000 | /opac/index |
| 晋中 | 晋中市图书馆 | `jinzhong` | http://lib.jzstsg.com:8082 | /opac/index |
| 四平 | 四平市图书馆 | `siping` | http://111.26.111.223:8081 | /opac/index |
| 齐齐哈尔 | 齐齐哈尔市图书馆 | `qiqihar` | http://www.qqhrlib.org.cn:8086 | /opac/index |
| 牡丹江 | 牡丹江市图书馆 | `mudanjiang` | http://122.156.44.53:8088 | /opac/ |
| 福州 | 福州市图书馆 | `fuzhou` | https://opcs.fzlib.org:8082 | /opac/index ⚠️ 旧批 TLS 失败/停放段，需复核 |
| 莆田 | 莆田市图书馆 | `putian` | https://opac.ptslib.com:8888 | /opac/ |
| 三明 | 三明市图书馆 | `sanming` | http://opac.fjsmlib.cn:6999 | /opac/index |
| 龙岩 | 龙岩市图书馆 | `longyan` | http://opac.lytsg.com:8082 | /opac/index |
| 宁德 | 宁德市图书馆 | `ningde` | http://220.161.205.210:82 | /opac/index |
| 开封 | 开封市图书馆 | `kaifeng` | http://221.176.156.243:8089 | /opac/index.jsp?page=index_jdjs.jsp&index=1 |
| 湖北省图 | 湖北省图书馆 | `hubei_prov` | http://27.17.61.109:8088 | /opac/index（官网 www.library.hb.cn；与 `wuhan` 非同一馆） |
| 十堰 | 十堰市图书馆 | `shiyan` | http://library.sylib.org.cn:9080 | /opac/index |
| 鄂州 | 鄂州市图书馆 | `ezhou` | http://58.19.204.93:8081 | /opac/ |
| 荆州 | 荆州市图书馆 | `jingzhou` | http://interlib.jzlib.org.cn:8081 | /opac/index |
| 黄冈 | 黄冈市图书馆 | `huanggang` | http://58.19.210.60:8081 | /opac/index |
| 恩施 | 恩施州图书馆 | `enshi` | http://119.96.92.24:9999 | /opac/ |
| 长沙 | 长沙图书馆 | `changsha` | https://opac.changshalib.cn | /index ⚠️ 旧批整站 WAF 403，需复核 |
| 湘潭 | 湘潭市图书馆 | `xiangtan` | http://220.170.15.29:8099 | /opac/index |
| 岳阳 | 岳阳市图书馆 | `yueyang` | http://183.214.211.146:18081 | /opac/index |
| 张家界 | 张家界市图书馆 | `zhangjiajie` | http://110.53.52.47:8090 | /opac/ |
| 三亚 | 三亚市图书馆 | `sanya` | https://opac.sanyalib.com:8888 | /opac/SY |
| 六盘水 | 六盘水市图书馆 | `liupanshui` | http://111.85.91.253:8088 | /opac/index |
| 安顺 | 安顺市图书馆 | `anshun` | http://119.1.160.3:8082 | /opac/ |
| 毕节 | 毕节市图书馆 | `bijie` | http://220.172.207.114:8001 | /opac/ |
| 呼伦贝尔 | 呼伦贝尔市图书馆 | `hulunbuir` | https://interlib.hlbewl.cn | /opac/index |
| 桂林 | 广西壮族自治区桂林图书馆 | `guilin` | https://opac.gxgllib.org.cn | /opac/index |
| 梧州 | 梧州市图书馆 | `wuzhou` | http://www.wztsg.com:82 | /opac/ |

### 4.2 Interlib pro2018＋验证码（2 城，同乐山口径，需评估）

| 城市 | 馆名 | 标识 | base_url | 备注 |
|---|---|---|---|---|
| 绵阳 | 绵阳市图书馆 | `mianyang` | http://opac.sclib.cn:8088 | 借省图联合目录，`?tenant=MY`；`pro2018=True`＋`captcha=True`，tenant 参数可能需扩 Config 字段，先侦察再定 |
| 雅安 | 雅安市图书馆 | `yaan` | http://opac.sclib.cn:8088 | 同上，`?tenant=YA` |

### 4.3 疑 Interlib `/ifs/search`（2 城，先侦察后接）

| 城市 | 馆名 | 标识 | base_url |
|---|---|---|---|
| 鞍山 | 鞍山市图书馆 | `anshan` | http://www.aslibrary.com:9200 |
| 西宁 | 西宁市图书馆 | `xining` | http://220.167.179.43:8020 |

### 4.4 UILAS 老版家族（5 城）

| 城市 | 馆名 | 标识 | base_url | 入口 |
|---|---|---|---|---|
| 芜湖 | 芜湖市图书馆 | `wuhu` | https://ilas.whstsg.org.cn:18086 | /ILASOPAC/ |
| 六安 | 六安市图书馆 | `luan` | http://60.173.147.75:8081 | /ILASOPAC/Index?target=0 |
| 通化 | 通化市图书馆 | `tonghua` | https://m.thslib.cn:3888 | /ILASOPAC/Index?target=0 |
| 南昌 | 南昌市图书馆 | `nanchang` | http://uopac.nclib.net:8086 | /Index?target=0 |
| 贵阳 | 贵阳市图书馆 | `guiyang` | http://218.201.254.11 | /Index?target=0 |

### 4.5 图星 LibStar Find（2 城）

| 城市 | 馆名 | 标识 | base_url | 备注 |
|---|---|---|---|---|
| 泰州 | 泰州市图书馆 | `taizhou_js` | https://findjstzlib.pub.chaoxing.com | **标识冲突**：`taizhou` 已被台州市（浙江）占用，泰州（江苏）用 `taizhou_js`；groupcode 待查 |
| 海西 | 海西州图书馆 | `haixi` | https://findhxztsg.libsp.cn | 传需登录，接入前复核匿名接口 |

### 4.6 tcc-opac 疑（1 城）

| 城市 | 馆名 | 标识 | base_url | 备注 |
|---|---|---|---|---|
| 蚌埠 | 蚌埠市图书馆 | `bengbu` | http://58.242.164.105:8090 | 入口 `/999`，同宁波/济南形态，先实抓确认 |

### 4.7 InDigLib（1 城）

| 城市 | 馆名 | 标识 | 入口 |
|---|---|---|---|
| 衡阳 | 衡阳市图书馆 | `hengyang` | http://weixin.hengyanglib.org/InDigLib/frontV2/SearchIndex!advanced.action |

### 4.8 新版 UILAS REST／同陕图平台（2 城）

| 城市 | 馆名 | 标识 | 备注 |
|---|---|---|---|
| 铜川 | 铜川市图书馆 | `tongchuan` | 入口即陕图省馆平台 `https://uilas.sxlib.org.cn/#/index`；铜川专有检索入口待确认，若为租户则并入 `shaanxi` |
| 商洛 | 商洛市图书馆 | `shangluo` | 同上；若为租户则并入 `shaanxi` |

### 4.9 SirsiDynix iLink（3 城，先侦察再决定是否抽家族）

| 城市 | 馆名 | 标识 | 入口 |
|---|---|---|---|
| 甘肃省图 | 甘肃省图书馆 | `gansu_prov` | http://search.gslib.com.cn/uhtbin/cgisirsi/ （仅查馆别＝省馆） |
| 陇南 | 陇南市图书馆 | `longnan` | 无独立入口，借甘肃省图 iLink 按馆别过滤 |
| 甘南 | 甘南州图书馆 | `gannan` | 无独立入口，借甘肃省图 iLink 按馆别过滤 |

### 4.10 MetaLSP 发现系统（1 城）

| 城市 | 馆名 | 标识 | 入口 | 备注 |
|---|---|---|---|---|
| 云南省图 | 云南省图书馆 | `yunnan_prov` | http://metalsp.ynlib.cn:3006/ | 底层书目接口未侦察，先侦 |

### 4.11 超星系（6 城，先侦察书目接口）

| 城市 | 馆名 | 标识 | 入口 | 指纹 |
|---|---|---|---|---|
| 连云港 | 连云港市图书馆 | `lianyungang` | https://4366ha.mh.chaoxing.com/entry/page/ck/peking_library | 超星智慧门户 |
| 宿迁 | 宿迁市图书馆 | `suqian` | https://sqstsg.mh.chaoxing.com | 超星智慧门户 |
| 德阳 | 德阳市图书馆 | `deyang` | http://www.deyanglib.cn | 超星智慧门户（wisweb） |
| 广元 | 广元市图书馆 | `guangyuan` | http://www.gyslib.org.cn | 超星智慧门户（wisweb） |
| 固原 | 固原市图书馆 | `guyuan` | http://www.gyslib.cn | 超星智慧门户；身份存疑（与广元/达州同 IP） |
| 眉山 | 眉山市图书馆 | `meishan` | http://www.mslib.cn | 超星系（cxstar／sslibrary） |

### 4.12 未知系统·待侦（13 城，只侦察，不写 adapter）

| 城市 | 馆名 | 标识 | 入口 | 指纹 |
|---|---|---|---|---|
| 济宁 | 济宁市图书馆 | `jining` | http://opac.sdjnlib.net/index.asp | 疑老版汇文/图创 |
| 嘉兴 | 嘉兴市图书馆 | `jiaxing` | http://libsys.jxlib.com/#/Home | libsys 门户 SPA |
| 晋城 | 晋城市图书馆 | `jincheng` | https://opac.jclib.cn/index | 系统未识别 |
| 双鸭山 | 双鸭山市图书馆 | `shuangyashan` | http://shuangyashan.libopac.cn/index | `libopac.cn` 云 OPAC |
| 洛阳 | 洛阳市图书馆 | `luoyang` | http://111.7.82.191:8009/#/index | `#/index` SPA |
| 宜宾 | 宜宾市图书馆 | `yibin` | http://ybslib.cn | 自研 Nuxt |
| 达州 | 达州市图书馆 | `dazhou` | https://www.dzslib.cn | 自研 Vue SPA |
| 嘉峪关 | 嘉峪关市图书馆 | `jiayuguan` | http://jygslib.com.cn | 自研 Vue SPA，身份弱证 |
| 巴中 | 巴中市图书馆 | `bazhong` | https://www.bzslib.cn | 帝国CMS 门户，站内有 opac 字样 |
| 海东 | 海东市图书馆 | `haidong` | https://hdtsg.cn/index.aspx | 自研 ASP.NET（BibliographySearch.aspx） |
| 锡林郭勒盟 | 锡林郭勒盟图书馆 | `xilingol` | http://58.18.112.198:8100/ | ASP.NET「OPAC查询系统」 |
| 广西省图 | 广西壮族自治区图书馆 | `guangxi_prov` | https://opac.gxlib.org.cn/#/home | 疑新版 UILAS；TLS 握手 EOF |
| 南宁市图 | 南宁市图书馆 | `nanning` | https://book.nnlib.com.cn/dss-portal/ | 未知（dss-portal，Vue 壳） |

### 4.13 无系统标注·待探（3 城）

| 城市 | 馆名 | 标识 | 入口 |
|---|---|---|---|
| 太原省图 | 山西省图书馆 | `shanxi_prov` | https://lib.sx.cn |
| 银川 | 宁夏图书馆 | `ningxia_prov` | http://www.nxlib.cn |
| 乌鲁木齐 | 新疆维吾尔自治区图书馆 | `xinjiang_prov` | https://www.xjlib.org |

## 五、单城作业循环（子 agent 每城执行）

1. **侦察**：只读 GET 首页／检索页／详情页／馆藏接口；记录 meta keywords、静态资源路径、
   接口形态，判家族与 quirk；实抓「三体」，记 `total_results` 与首条。
2. **fixture**：`tests/fixtures/<city>/` 存抓到的 HTML/JSON，写 `NOTES.md`
   （技术组件与 quirk、检索通道、详情与馆藏、fixture 清单、数据边界；全角标点）。
3. **adapter**：`src/mcp_library_search/adapters/cn/<city>.py`，照家族范例薄包装，
   公开三原语经模块级 `_client`。
4. **注册**：`adapters/cn/__init__.py` 加 import 与 `ADAPTERS` 一项。
5. **测试**：`tests/test_<city>_adapter.py`（+ 必要时 `_parse.py`），离线，
   monkeypatch `_client` 或家族函数；覆盖 config 正确性、委托、错误包装、契约。
6. **文档**：`cn.md` 总览表该行状态改 `✅ 接入`＋填「适配层位置」；家族成员差异表加一行。
7. **验证**：`uv run pytest -q` 全量绿。
8. **提交**：本批全部城市完成后一次 `git commit`（中文全角标点，说明批内容与各城实抓量）。

## 六、回报模板（子 agent 每城一条，最后汇总）

```
城市 <name_cn>（<city>）｜状态 ✅/❌｜实抓「三体」<N> 条，首条《<title>》
  quirk：<确认的开关与取值>
  改动：adapters/cn/<city>.py ｜ tests/test_<city>_adapter.py ｜ tests/fixtures/<city>/ ｜ cn.md
  备注：<失败原因 / 数据边界 / 需主线程归类项>
```

## 七、回填约定（提示词持续优化）

每批结束后把新发现的 quirk 回填本文件第三节对应家族附注，并在该家族城市数据行的
`quirk` 列写明结论——下次同族城市直接带已知 quirk 下发，减少试探轮次。
