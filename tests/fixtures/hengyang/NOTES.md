# 衡阳市图书馆 InDigLib 侦察（2026-10-03 实抓）

入口：`http://weixin.hengyanglib.org/InDigLib/frontV2/SearchIndex!advanced.action`
（页标题「opac查询」）。技术组件 **InDigLib 集群数字图书馆**
（Struts2＋Solr），同重庆家族，但仓库无共享模块，照 `adapters/cn/chongqing.py`
复刻独立实现（urllib＋CookieJar）。

页内 `<base href="http://weixin.hengyanglib.org:80/InDigLib/">`，故所有相对
URL 解析到 `/InDigLib/`（**检索走根路径，非 frontV2 前缀**）。

## 会话与检索流程

1. `GET frontV2/SearchIndex!advanced.action` 建立 JSESSIONID。
   （旧版 `frontV2/SearchIndex!simple.action?opacType=local` 也存在，偶发超时不稳，
   本城入口以 advanced 为准。）
2. `POST /InDigLib/OpacMarcSearchSolr!simpleSearch.action`，字段 `select1`＋`text1`
   ＋`pageSize`（根路径，见上）。
3. 详情 `GET frontV2/BookDetail.action?metaid={N}&metatable={表名}`。
4. 单册 `POST /InDigLib/GetAsset.action`（根路径匿名，与重庆一致；frontV2 前缀
   同名 action 有登录拦截）。

## 检索字段 quirk（关键）

本城 advanced 表单默认检索字段是 **`select1=title`（题名）**，不是重庆的
「任意词 all」。实抓对照：`select1=all` 会把「三体」按字拆成 OR，返回
`totalPage=16`、首条为无关的《三国志》（且第二、三条仍为《三国志》《体育史料》）；
`select1=title` 返回 `totalPage=6`、首条《三体》。故适配器对非 ISBN 关键词一律
路由 `title`（ISBN 走 `select1=isbn`）。此为家族内重庆之外的首个字段差异，
以城市 quirk 表达。

## 分页

结果页分页链接形态：`GET OpacMarcSearchSolr!simpleSearch.action?pageNo=N&select1=
title&text1=...&lastSearchValue=titleFIELD_SPLITVALUE_SPLIT三体...`。POST 表单里的
`page` 字段无效，真实分页是 GET `pageNo`（与重庆一致）。第 2 页首条与第 1 页不同。

## 详情与馆藏

- 详情页 metaid 19673（metatable `i_sgbiblios`）：题名「三体」、著者「刘慈欣著」、
  ISBN `9787536692930`；出版社/出版年未在详情页渲染；详情页无索书号字段，
  `call_number` 恒空串。
- 单册 `GetAsset.action`（metatables=i_sgbiblios、metaids=19673）：2 册，馆名
  「石鼓区图书馆」、位置「石鼓_图书借阅室」、索书号 `I247.55/14`；状态「入藏」
  （语义不确定，保守 `available=False`）与「普通借出」（`due_date=2025-10-02`）。
- 检索结果含多张表（`i_sgbiblios` 石鼓区、`i_nybiblios` 南岳区、`i_biblios` 总馆），
  `book_id` 形如 `{metatable}:{metaid}`，原值照登。

**可借口径统一保守**（同重庆）：源站无明确「可借/在架」状态词，确定的只有借出
（status 含「借出」，带 `retudate`）→ `available=False`＋`due_date`；「入藏」等
一律 `available=False`，status 原值照登。`only_available=True` 恒为空列表。

## fixture 清单

| 文件 | 说明 |
|---|---|
| `index.html` | advanced 检索页（指纹「opac查询」） |
| `search.html` | `select1=title` 检索「三体」，totalPage=6，首条《三体》 |
| `search_p2.html` | 同上第 2 页（GET pageNo=2），首条与第 1 页不同 |
| `search_empty.html` | 生造关键词，totalPage=0 |
| `detail.html` | metaid=19673（i_sgbiblios），《三体》 |
| `get_asset.json` | 根路径 GetAsset，2 册（1 入藏 1 普通借出） |

## 数据边界

- 详情页无索书号字段，`call_number` 空串；出版社/出版年详情页不渲染，空串。
- `select1=all` 为源站分词 OR 行为，命中不相关书目；已改用 `title` 规避（见上）。
- 源站偶发读超时，适配器 `_open` 内有限次（3 次）重试；未见验证码/登录墙。
