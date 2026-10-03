# 数据源接入作业指导书（子 agent 复用提示词）

> 本文件是「主线程摸底 → 分组 → 派子 agent 对接」这套流程的可复用提示词资产。
> 主线程**不亲自接入**，只把「公共骨架 ＋ 家族附注 ＋ 城市数据行」拼进子 agent 的
> 提示词；子 agent 按单城循环交付并**按批 commit**。每次跑完把踩到的新 quirk 回填
> 本文件，提示词随之优化——这是降费的关键：家族内提示词只维护一份。

登记正文见 [cn.md](../../data-sources/cn.md)；字段级结论见 `tests/fixtures/<city>/NOTES.md`。

## 一、分工

| 角色 | 职责 |
|---|---|
| 主线程 | 从 [cn.md](../../data-sources/cn.md) 取「📋 计划 / 🔍 待核验」条目，按「技术组件」归类到家族，挑一批，把本文件第二节骨架＋第三节家族附注＋第四节城市数据行拼成子 agent 提示词 |
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
  - 详情页 HTML 截断或模板异常 → `api_detail=True`（走 `/opac/api/book/{recno}` JSON）。
  - 检索页返回 ~3.3KB「opac验证」滑动验证码页 → `solr_search=True`（走 `/opac/api/search`）；
    若该站无内嵌 Solr（`/opac/api/search` 404）→ `captcha=True`（命中即抛 CaptchaError，不破解）。
  - 应用上下文非 `/opac` → `ctx="/lib2"` 或 `ctx=""`（先探 `/opac/*` 是否 404）。
  - 新版页 `li.libBookLi`／`a.bkTxtTit` → `pro2018=True`（绍兴另需 `pro2018_cite_author=True`）。
  - 多租户云托管详情需带馆码 → `curlibcode="XXX"`；联合目录按馆过滤 → `f_curlibcode="XX"`。

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

- 家族模块 `src/mcp_library_search/tccopac/`；配置 `TccOpacConfig`。
- 入口形如 `{host}/…/999`（宁波/济南/鄂尔多斯）；纯 JSON＋JWT 访客令牌
  （`POST /system/user/getOpenApiAccessToken` 匿名即发，过期自动重取）。
- 检索 `POST /search/`（**尾斜杠**，`hasholding=1`＝只看有馆藏）；详情
  `POST /service/biblios/getbyid`；馆藏 `POST /service/hold/pagelist`。
- 滑块风控 `code ∈ {43001,-1,-402}` → 停手抛错，不硬闯。
- 适配器照 `adapters/cn/ningbo.py`／`jinan.py`。

### 3.6 InDigLib（重庆，独立实现，无共享家族）

- 无家族模块；照 `adapters/cn/chongqing.py` 复制独立实现（urllib＋CookieJar）。
- 入口 `/InDigLib/frontV2/SearchIndex!simple.action?opacType=local`；会话流程先 GET 拿
  JSESSIONID 再 POST `OpacMarcSearchSolr!simpleSearch.action`；翻页必须 GET 带 `pageNo`；
  馆藏走**根路径** `POST InDigLib/GetAsset.action`（`frontV2/` 前缀版有登录拦截）。
- 可借口径统一保守：无法确认在架的一律 `available=False`，原值照登。

### 3.7 未知系统（待侦）

先只做侦察、**不写 adapter**：抓首页＋找 `opac/search/检索` 入口，记录技术指纹
（meta keywords、静态资源路径、JS 全局变量、接口形态），回报后由主线程归入家族再排期。

## 四、城市数据行（62 条 📋 计划，按家族）

> `标识` 为拟用城市键（拼音，冲突时加后缀）；`quirk` 为待试探项，实抓后回填确认。
> `实抓词` 统一「三体」，记录 `total_results` 与首条，写进该城 `NOTES.md`。

### 4.1 Interlib 默认模板＋`api_detail=True`（41 城）

| 城市 | 馆名 | 标识 | base_url |
|---|---|---|---|
| 铜陵 | 铜陵市图书馆 | `tongling` | http://60.173.22.63:7075 |
| 安庆 | 安庆市图书馆 | `anqing` | http://39.145.39.67:8082 |
| 茂名 | 茂名市图书馆 | `maoming` | http://14.18.69.185:8082 |
| 清远 | 清远市图书馆 | `qingyuan` | https://elib.qylib.com |
| 中山 | 中山市图书馆 | `zhongshan` | https://opac.zslib.cn |
| 揭阳 | 揭阳市图书馆 | `jieyang` | http://61.146.124.30:8088 |
| 普宁 | 普宁市图书馆 | `puning` | http://www.pnlib.com:8088 |
| 东营 | 东营市图书馆 | `dongying` | http://60.214.234.201:81 |
| 烟台 | 烟台市图书馆 | `yantai` | http://144.123.23.246:8082 |
| 潍坊 | 潍坊市图书馆 | `weifang` | http://60.210.241.4:8080 |
| 泰安 | 泰安市图书馆 | `taian` | http://112.245.16.82 |
| 日照 | 日照市图书馆 | `rizhao` | http://58.59.43.7:38080 |
| 临沂 | 临沂市图书馆 | `linyi` | http://111.16.49.57:8888 |
| 聊城 | 聊城市图书馆 | `liaocheng` | http://218.57.211.26:8091 |
| 石家庄 | 石家庄市图书馆 | `shijiazhuang` | http://120.211.62.194:8087 |
| 忻州 | 忻州市图书馆 | `xinzhou` | http://124.163.188.204:9000 |
| 晋中 | 晋中市图书馆 | `jinzhong` | http://lib.jzstsg.com:8082 |
| 四平 | 四平市图书馆 | `siping` | http://111.26.111.223:8081 |
| 齐齐哈尔 | 齐齐哈尔市图书馆 | `qiqihar` | http://www.qqhrlib.org.cn:8086 |
| 牡丹江 | 牡丹江市图书馆 | `mudanjiang` | http://122.156.44.53:8088 |
| 莆田 | 莆田市图书馆 | `putian` | https://opac.ptslib.com:8888 |
| 三明 | 三明市图书馆 | `sanming` | http://opac.fjsmlib.cn:6999 |
| 龙岩 | 龙岩市图书馆 | `longyan` | http://opac.lytsg.com:8082 |
| 宁德 | 宁德市图书馆 | `ningde` | http://220.161.205.210:82 |
| 开封 | 开封市图书馆 | `kaifeng` | http://221.176.156.243:8089 |
| 湖北省图 | 湖北省图书馆 | `hubei_prov` | http://27.17.61.109:8088 |
| 十堰 | 十堰市图书馆 | `shiyan` | http://library.sylib.org.cn:9080 |
| 鄂州 | 鄂州市图书馆 | `ezhou` | http://58.19.204.93:8081 |
| 荆州 | 荆州市图书馆 | `jingzhou` | http://interlib.jzlib.org.cn:8081 |
| 黄冈 | 黄冈市图书馆 | `huanggang` | http://58.19.210.60:8081 |
| 恩施 | 恩施州图书馆 | `enshi` | http://119.96.92.24:9999 |
| 湘潭 | 湘潭市图书馆 | `xiangtan` | http://220.170.15.29:8099 |
| 岳阳 | 岳阳市图书馆 | `yueyang` | http://183.214.211.146:18081 |
| 张家界 | 张家界市图书馆 | `zhangjiajie` | http://110.53.52.47:8090 |
| 三亚 | 三亚市图书馆 | `sanya` | https://opac.sanyalib.com:8888 |
| 六盘水 | 六盘水市图书馆 | `liupanshui` | http://111.85.91.253:8088 |
| 安顺 | 安顺市图书馆 | `anshun` | http://119.1.160.3:8082 |
| 毕节 | 毕节市图书馆 | `bijie` | http://220.172.207.114:8001 |
| 呼伦贝尔 | 呼伦贝尔市图书馆 | `hulunbuir` | https://interlib.hlbewl.cn |
| 桂林 | 广西壮族自治区桂林图书馆 | `guilin` | https://opac.gxgllib.org.cn |
| 梧州 | 梧州市图书馆 | `wuzhou` | http://www.wztsg.com:82 |

### 4.2 Interlib pro2018＋验证码（2 城，同乐山口径，需评估）

| 城市 | 馆名 | 标识 | base_url | 备注 |
|---|---|---|---|---|
| 绵阳 | 绵阳市图书馆 | `mianyang` | http://opac.sclib.cn:8088 | 借省图联合目录，`?tenant=MY`；`pro2018=True`＋`captcha=True`，tenant 参数可能需扩 Config 字段，先侦察再定 |
| 雅安 | 雅安市图书馆 | `yaan` | http://opac.sclib.cn:8088 | 同上，`?tenant=YA` |

### 4.3 UILAS 老版家族（5 城）

| 城市 | 馆名 | 标识 | base_url | 入口 |
|---|---|---|---|---|
| 芜湖 | 芜湖市图书馆 | `wuhu` | https://ilas.whstsg.org.cn:18086 | `/ILASOPAC/` |
| 六安 | 六安市图书馆 | `luan` | http://60.173.147.75:8081 | `/ILASOPAC/Index?target=0` |
| 通化 | 通化市图书馆 | `tonghua` | https://m.thslib.cn:3888 | `/ILASOPAC/Index?target=0` |
| 南昌 | 南昌市图书馆 | `nanchang` | http://uopac.nclib.net:8086 | `/Index?target=0` |
| 贵阳 | 贵阳市图书馆 | `guiyang` | http://218.201.254.11 | `/Index?target=0` |

### 4.4 图星 LibStar Find（2 城）

| 城市 | 馆名 | 标识 | base_url | 备注 |
|---|---|---|---|---|
| 泰州 | 泰州市图书馆 | `taizhou_js` | https://findjstzlib.pub.chaoxing.com | **标识冲突**：`taizhou` 已被台州市（浙江）占用，泰州（江苏）用 `taizhou_js`；groupcode 待查 |
| 海西 | 海西州图书馆 | `haixi` | https://findhxztsg.libsp.cn | 传需登录，接入前复核匿名接口 |

### 4.5 单城家族（各 1 城）

| 城市 | 馆名 | 标识 | base_url | 家族/备注 |
|---|---|---|---|---|
| 蚌埠 | 蚌埠市图书馆 | `bengbu` | http://58.242.164.105:8090 | 疑 tcc-opac（入口 `/999`），先实抓确认 |
| 衡阳 | 衡阳市图书馆 | `hengyang` | http://weixin.hengyanglib.org | InDigLib，照重庆独立实现 |
| 商洛 | 商洛市图书馆 | `shangluo` | https://uilas.sxlib.org.cn | 入口即陕图省馆平台（`shaanxi`），商洛专有入口待确认；若实为租户则并入 `shaanxi` |

### 4.6 疑 Interlib `/ifs/search`（2 城，先侦察后接）

| 城市 | 馆名 | 标识 | base_url |
|---|---|---|---|
| 鞍山 | 鞍山市图书馆 | `anshan` | http://www.aslibrary.com:9200 |
| 西宁 | 西宁市图书馆 | `xining` | http://220.167.179.43:8020 |

### 4.7 未知系统·待侦（5 城，只侦察）

| 城市 | 馆名 | 标识 | 入口 | 指纹 |
|---|---|---|---|---|
| 济宁 | 济宁市图书馆 | `jining` | http://opac.sdjnlib.net/index.asp | 疑老版汇文/图创 |
| 嘉兴 | 嘉兴市图书馆 | `jiaxing` | http://libsys.jxlib.com/#/Home | libsys 门户 SPA |
| 晋城 | 晋城市图书馆 | `jincheng` | https://opac.jclib.cn/index | 系统未识别 |
| 双鸭山 | 双鸭山市图书馆 | `shuangyashan` | http://shuangyashan.libopac.cn/index | `libopac.cn` 云 OPAC |
| 洛阳 | 洛阳市图书馆 | `luoyang` | http://111.7.82.191:8009/#/index | `#/index` SPA |

### 4.8 实测阻断·不应排期（回退状态）

| 城市 | 馆名 | 标识 | 入口 | 处置 |
|---|---|---|---|---|
| 长沙 | 长沙图书馆 | — | https://opac.changshalib.cn/index | 整站 WAF 403（含内嵌 Solr），暂回退 ⛔ 不通 |
| 福州 | 福州市图书馆 | — | https://opcs.fzlib.org:8082 | TLS 握手失败、域名停放段，暂回退 ⛔ 不通 |

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
