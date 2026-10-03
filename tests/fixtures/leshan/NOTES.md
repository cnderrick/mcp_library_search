# 乐山市图书馆 / 四川省图书馆联合目录 OPAC 侦察（2026-10-03 实抓）

站点：`http://opac.sclib.cn:8088/opac/index`（页标题「四川省图书馆书目检索系统」，
媒体路径 `/opac/media/pro2018/simple/` → **图创 Interlib pro2018**）。
乐山借四川省图书馆联合目录按 `f_curlibcode=LS` 过滤乐山馆。
抓取只读 GET。注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **pro2018 模板**。本城配置：`pro2018=True`、`api_detail=True`、
`f_curlibcode="LS"`、`captcha=True`。

## 检索：滑动验证码墙（不破解）

`GET /opac/search`（含 `f_curlibcode=LS`）恒返「opac验证」滑动验证码页
（`/opac/media/captcha/js/verify.js`，服务端 `/opac/captcha/verification`），
且**无内嵌 Solr**（`/opac/api/search` 恒 404）。按天津 ALEPH 家族同一口径
**不破解验证码**：家族 `client.check_captcha` 命中「opac验证」即抛 `CaptchaError`
（带人工过码指引，见 `interlib/client.py`），穿透源级容错直达调用方，
不静默返回空结果。过码后检索即按 `f_curlibcode=LS` 过滤。

## 详情与馆藏：匿名可通

- **详情**：`GET /opac/api/book/{recno}` JSON，实抓 recno `3681673`
  《中国站起来:我们的前途、命运与精神解放》、ISBN `978-7-5354-4265-9`。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 3 条，
  馆名是**省内各县馆**（如遂宁市大英县图书馆）——省图联合目录口径，非乐山本馆。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹（pro2018） |
| `search_captcha.html` | `GET /opac/search` 的「opac验证」页（验证码墙 4KB 特征页） |
| `detail_api.json` | `GET /api/book/3681673` |
| `holding.json` | `GET /api/holding/3681673` |

## 数据边界

- 未过码时检索不可用（抛 `CaptchaError` 指向 `http://opac.sclib.cn:8088/opac/index`）。
- 馆藏为四川省图联合目录口径，含省内各馆，不等于乐山本馆馆藏。
- pro2018 详情/馆藏字段同家族（`/api/book` JSON）。
