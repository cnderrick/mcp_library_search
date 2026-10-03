# 湖北省图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://27.17.61.109:8088/opac/index`（图创 Interlib，页标题「检索系统」，
meta keywords 自报「opac, 图创, interlib, 图书检索, 借书, , 湖北省图书馆」；官网
www.library.hb.cn。与已接入的 `wuhan`（武汉图书馆）非同一馆）。抓取只读 GET。
注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`、`captcha=True`。

## 检索：滑动验证码墙（不破解）

`GET /opac/search` 恒返「opac验证」滑动验证码页（约 4KB，`search_captcha.html`）；
站点内嵌 Solr `GET /opac/api/search` 被 bot 检测拦——实测连接被重置
（`RemoteDisconnected`）或回 403（带 `Referer`／`X-Requested-With` 头仍拦），
**无可用程序化检索通道**。故 `captcha=True`：家族 `client.check_captcha` 命中
「opac验证」即抛 `CaptchaError`（带人工过码指引，指向 `http://27.17.61.109:8088/opac/index`），
穿透源级容错直达调用方，不破解、不静默返回空结果（同乐山/揭阳口径）。

## 详情与馆藏：匿名可通

检索不可用，recno 自匿名首页推荐位（`GET /opac/recommend/recommendBookList/list`，
返回书目链接 `/opac/book/{recno}`）取得。

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓 recno
  2003413334《动荡变革期世界发展和趋势：百年大变局中的观察与分析：observation and
  analysis》、ISBN `978-7-5432-3611-0`、索书号 `D81`、出版年 2024。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 4 条，
  均在馆，馆名「湖北省图书馆」（含省图专属空间分馆、中文保存本）。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_captcha.html` | `GET /opac/search?q=三体` 的「opac验证」页（验证码墙特征页） |
| `detail_api.json` | `GET /api/book/2003413334`（推荐位 recno） |
| `holding.json` | `GET /api/holding/2003413334`（4 条，均在馆） |

## 数据边界

- 未过码时检索不可用（抛 `CaptchaError`）；详情/馆藏匿名可通。
- 因检索不可用，无法实抓「三体」条数与首条；详情/馆藏 fixture 的 recno 由首页
  推荐位取得（同揭阳/乐山先例）。
- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）；
  `availability_summary` 在 HTML 通道下为空串。
- 站点连接不稳定：连续请求偶发 `RemoteDisconnected`，适配器内置超时/报错包装，
  调用方可重试。
