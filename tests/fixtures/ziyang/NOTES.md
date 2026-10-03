# 资阳市图书馆 小程序 H5 接口侦察（2026-10-03 实抓）

站点：资阳市图书馆「微信公众号 H5」应用（uwei 2.0），接口基址 `https://b.dataesb.com`、
静态资源 CDN `https://wechat-cdn.dataesb.com/uwei2.0/<版本>/`。本目录是从浏览器抓取的
原始响应与前端包（见下「fixture 清单」），用于攻克其接口调用认证。注册登记见
`docs/data-sources/cn.md` 总览表「资阳」行（状态 🚧 攻关）。

> 本包来自项目平级目录 `../资阳/`（用户抓取），2026-10-03 导入仓库；
> `.DS_Store` 与抓包时的 OAuth 回跳页（`index.html?code=…&state=uwei2020`，含一次性
> 微信 code）未导入。

## 身份与配置（`b.dataesb.com/api/v1/getConfig` 原值）

- `wxname`：资阳市图书馆；微信公众号 `appid`：`wx0c83fd90fbe36e1b`。
- 站点 `token`：`3dd655712f78`；`libcode`：`ZYLIB`；`glc`：`P2SC028016`；`auth_type`：2。
- 首页自定义 `template_id`：6，`motif_id`：05。

## 接口认证（待攻克）

前端包 `static/js/index.*.js` 揭示两段客户端逻辑，均为**客户端内置常量**（任何人均可
下载该 H5 包，非服务端机密）：

1. **微信 openid 授权**：`GET /api/v1/openidAuthorization/uweiVue`，参数
   `token`／`time`（秒级）／`openid`／`sign`，其中
   `sign = md5(openid + time + <内置密钥>)`。未走通 openid 授权前，涉读者的接口应被拒。
2. **报文 SM2 加解密**：包内 `v = require("8060").sm2`、私钥常量 `C`、公钥点常量 `A`；
   `doEncrypt` 对明文加密并前置 `04`，响应体经 `doDecrypt(t, C)` 解密（`T`/`O` 为
   base64↔hex 辅助）。即请求/响应可能以 SM2 密文承载，而非明文 JSON——这正是「小程序
   H5 接口调用认证」的实质。

**攻关入口点**：先定位这三个内置常量的取值（都在 `index.*.js` 内联），复刻 `sign` 计算与
SM2 解密，再补齐 openid 授权；图形验证码/WAL 与本城无关（故本城仍列 🚧 攻关而非 ⚠️ 障碍）。

## 检索接口

`GET/POST /api/v1/books/search`（实抓响应 `b.dataesb.com/api/v1/books/search`，40KB）。
返回 `{status, code, message, data}`；`data` 含 `numFound`／`start`／`rows`／`page`／
`filter`（分面）／书目列表。**关键事实**：该实例是**成都都市圈联合目录**，
`data.filter.curlibcode` 同时含 `CD101…CD190`（成都各区馆）、`MZSLIB`（眉山）、
`ZYLIB`（资阳）等；实抓关键词命中 `ZYLIB` 23 条。资阳馆码＝`ZYLIB`。

同批其它端点：`books/hotWords`（热词榜）、`books/newBookReport`（新书）、
`pavilion/libSecondaryList`（馆点列表）、`pageConf/searchConfig`、
`pageConf/globalConfig`、`pageConf/homeCarousel`、`pageConf/wechatJsSdk`、
`fansOperation/bindList`。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `b.dataesb.com/api/v1/getConfig` | 站点身份/配置（wxname/appid/token/libcode） |
| `b.dataesb.com/api/v1/books/search` | 检索响应，`ZYLIB` 23 条 |
| `b.dataesb.com/api/v1/books/hotWords` | 热词榜 |
| `b.dataesb.com/api/v1/books/newBookReport` | 新书通报 |
| `b.dataesb.com/api/v1/pavilion/libSecondaryList` | 馆点列表（76KB） |
| `b.dataesb.com/api/v1/fansOperation/bindList` | 读者绑定列表 |
| `b.dataesb.com/api/v1/pageConf/searchConfig`、`…searchConfig?token=…`、`globalConfig?token=…`、`homeCarousel`、`wechatJsSdk` | 页面配置 |
| `b.dataesb.com/index.html` | H5 入口（`<title>uwei 加载中…`） |
| `wechat-cdn.dataesb.com/uwei2.0/202609231711/…` | 前端包：`index.*.js`（含 sign/SM2 逻辑）、`chunk-vendors.*.js`、CSS、主题、图标 |

## 数据边界与待办

- 尚未复刻认证，故检索接口**未结构化**、未接入；本目录仅存原始物料。
- `books/search` 实抓显示未鉴权即可返回数据（用户抓取时或已带会话）；接入前须确认
  裸请求是否被拒，避免误判可达。
- 若攻克成功，按仓库约定新建 `adapters/cn/ziyang.py` + 家族/独立实现，并把结构化
  fixture 落本目录。
