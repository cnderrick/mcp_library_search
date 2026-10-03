# 揭阳市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`http://61.146.124.30:8088/opac/index`（图创 Interlib，页标题「检索系统」，meta keywords 自报
「opac, 图创, interlib, 图书检索, 借书, , 揭阳市图书馆」）。抓取只读 GET。
注册登记见 docs/data-sources/cn.md 总览表。

## 技术组件与 quirk

图创 Interlib **默认（非 pro2018）模板**。本城配置：`api_detail=True`、`captcha=True`。

## 检索

检索页 `/opac/search` 恒返「opac验证」滑动验证码页；站点内嵌 Solr
`GET /opac/api/search` 回 **403「bot detected」**（服务端 bot 检测，带 `Referer`/`X-Requested-With`
头仍 403），**无可用程序化检索通道**。故 `captcha=True`：家族 `client.check_captcha` 命中
「opac验证」即抛 `CaptchaError`（带人工过码指引，指向 `http://61.146.124.30:8088/opac/index`），
穿透源级容错直达调用方，不破解、不静默返回空结果（同乐山口径）。

## 详情与馆藏

- **详情**：`GET /opac/api/book/{recno}` JSON（`api_detail=True`），实抓首条
  《赵匡胤：乱世枭雄开启文治盛世》（4542283）、ISBN `978-7-5171-0559-6`、索书号 `K827=441`。
- **馆藏**：`GET /opac/api/holding/{recno}` JSON，家族 parser 零改动；实抓 2 条，
  为「惠来县图书馆」（联合目录口径，非市馆）。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | 首页指纹 |
| `search_captcha.html` | `GET /opac/search` 的「opac验证」页（验证码墙特征页） |
| `detail_api.json` | `GET /api/book/4542283`（从首页推荐位取得 recno） |
| `holding.json` | `GET /api/holding/4542283`（2 条） |

## 数据边界

- 可借判定沿用家族状态词表（只有「在馆」可借，词表外保守不可借）。
- `availability_summary` 在 HTML 通道下为空串。
- 未过码时检索不可用（抛 `CaptchaError`）；详情/馆藏匿名可通。
- 因检索不可用，详情/馆藏的 recno 由首页推荐位（`/opac/recommend/recommendBookList/list`）取得。
