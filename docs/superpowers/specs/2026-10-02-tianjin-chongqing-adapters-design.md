# 天津（三源合并）、重庆（InDigLib）适配器设计

日期：2026-10-02。前置 spec：`2026-10-01-three-city-adapters-design.md`（广州/杭州/深圳的适配器模式与本 spec 的参照基准）。

## 背景与目标

`mcp_library_search` 现有上海（vendor）、广州/杭州（interlib 家族）、深圳（独立 JSON）四城，已发 0.2.0。本 spec 新增两个直辖市：

- **天津**：对外一个城市标识 `tianjin`，内部合并**三个独立书目源**——这是本设计的核心特殊点
- **重庆**：一个城市标识 `chongqing`，InDigLib 单源独立适配器

对外契约（`SearchPage`/`Holding`/`BookDetail` 结构、`_client` 模块级形态、铁律）一行不改。

## 数据源侦察结论（2026-10-02 本机实测）

### 天津源 A：TJL01 主馆目录（ALEPH 20.1）

- 入口 `http://opacwh.tjl.tj.cn:8991/F`（用户指定），Ex Libris ALEPH 20.1 `www_f_chi` 中文 OPAC
- 检索 `GET /F?func=find-b&request={词}&find_code=WRD&local_base=TJL01`，结果页 HTML，计数在「记录 1 - 10 of N」，短列表每条含索书号/出版社/年份；ISBN 检索 `find_code=ISBN`（ISBN 形态走此路）
- 详情 `func=full-set-set&set_number=N&set_entry=M&format=999`，内嵌 `func=item-global&doc_library=TJL01&doc_number=N` 单册链接
- 单册页表格行：状态（在架上/已借出等）｜类型（阅览/外借）｜馆藏地（如文化中心中图基藏）｜索书号
- 分馆体系：主馆三馆区（文化中心 W*、复康路 F*、海河园 H*）+ 16 区馆（Q*代码）+ 泰达 QTDG、空港 QKGG、行业分馆 HYFG；高级检索页 `func=find-a` 的 `filter_request_5` 下拉含全部 69 个分馆代码
- 武清（QWQG）抽样：关键词「的」命中 7250 条——分馆代码是活的
- **坑**：约 8 次/几分钟触发验证码（401 + 「请验证验证码」，按 IP 封、跨会话持续）；馆藏地等字段为 GBK 字节（页面声明 UTF-8，混合编码）；HTTP 明文、非标端口

### 天津源 B：TJC01 少儿馆目录（ALEPH 20.1）

- 入口 `http://opacse.tjl.tj.cn:8991/F`（用户指定），与源 A 同版本同界面，FIND-BASE=`TJC01`，馆藏地「图书基藏库」
- 端点形态与源 A 完全一致（func=find-b / full-set-set / item-global），同一套解析器可复用，仅 host 与 find_base 不同
- 主馆与少儿馆书目不通：同一本书可能两库各有记录（Primo 只挂源 A 的实证：拿源 B 的 ISBN 9787221179975 搜 Primo 返回 0 条）

### 天津源 C：中新友好图书馆（Interlib 家族，复用现有模块）

- 入口 `http://sm.interlib.cn:8104/opac/`（图创厂商云多租户托管），检索 URL 与穗杭同构：`/opac/search?q=&searchType=standard&searchWay0=marc&logical0=AND&rows=&sortWay=score&sortOrder=desc&page=`，带 `curlibcode=STC001`（生态城馆代码）参数
- **复用方式**：走现有 `interlib/` 家族原语，`InterlibConfig(base_url="http://sm.interlib.cn:8104", …)`；需新增 quirk 字段 `curlibcode: str = ""`（默认空 = 穗杭行为，非空时 `_search_once` 带上该参数）
- 未验证项（实现期侦察任务，见「风险」）：`/opac/api/holding/{bookrecno}` JSON 馆藏接口在该租户上是否可用、详情页结构是否与穗杭模板一致、不带 curlibcode 时的默认范围

### 重庆：InDigLib 集群数字图书馆

- 入口 `http://222.177.237.197:8080/InDigLib/`（用户确认），Struts2（`!xxx.action`）+ Solr 检索，UTF-8
- **会话流程**：先 `GET frontV2/SearchIndex!simple.action?opacType=local` 拿 JSESSIONID cookie，再 `POST OpacMarcSearchSolr!simpleSearch.action`，参数 `select1`（all/title/isbn/author/callno/subject/classno/publisher/pubdate/lang）+ `text1`
- 首页表单的 action（`opacSearch.action`）是假端点；真端点由 `frontV2/opac/bookSearch/js/search.js` 的 `submitForm()` 改写（本 spec 侦察已确认，用户亦独立验证 `opacSearch` 可用——实现期两个端点都试，以实抓为准并在 NOTES 记录）
- 结果页：命中列表 + 作者/出版年/中图分类分面；详情 `frontV2/BookDetail.action?metaid=N&metatable=i_biblios`；`book_id = i_biblios:{metaid}`
- 未验证项：单册级馆藏状态字段（详情页有 `showAsset=true` 参数与 `GetCurrentBorrow.action` ajax，实现期深挖）

## 总体架构

```
adapters/tianjin.py    独立实现（照 shenzhen.py 模式）
  ├─ _Client.search    查源A + 源B（ALEPH client）+ 源C（interlib 原语，ZXYH 配置）
  │                    → ISBN 归并 → SearchPage
  ├─ _Client.get_holdings   按 book_id 前缀路由；归并条目跨三源聚合
  └─ _Client.get_book_detail 按前缀路由
adapters/chongqing.py  独立实现（会话 cookie client + 限速）
interlib/__init__.py   仅加 InterlibConfig.curlibcode quirk，签名不变
adapters/__init__.py   _ADAPTERS 注册 tianjin、chongqing 两行
```

不抽 ALEPH/InDigLib 家族（各只有一座城在用）；第二个同族城市出现时再抽，参照 interlib 先例。

## 天津适配器设计

### book_id 与源标识

`{源标识}:{记录号}`，源标识 ∈ `TJL01`、`TJC01`、`ZXYH`（中新友好）。holdings/detail 按前缀路由回对应源。

### 检索与归并

1. 三源各查各的（limit 对每源各取，合并后截断到 limit）；ISBN 形态关键词在源 A/B 走 `find_code=ISBN`，源 C 走 interlib 原生检索（其内部已有连字符重试）
2. **ISBN 归并**：三源记录 ISBN（归一化：去连字符）相同 → 合成一条，book_id 取优先级最高源的记录：TJL01 > TJC01 > ZXYH；无 ISBN 或 ISBN 不同的记录并列呈现不去重
3. `total_results` 给三源合计（归并不精确调整，与现有城市口径一致即可）

### 馆藏聚合

- 非归并条目：前缀路由单源查询
- 归并条目（book_id 为 TJL01 记录）：查源 A 该记录单册 + 源 B/源 C 按同 ISBN 检索到的对应记录单册，三源合并后统一排序（可借在前，馆名升序）

### 限速

- 每 host 独立令牌桶；ALEPH 两 host 保守节奏（初始 4 秒/请求，实现期实测调参并记入 NOTES）
- 命中验证码页 → 抛 `RuntimeError("天津图书馆：检索过于频繁，请稍后再试")`（含馆名，照契约），不自动重试

## 重庆适配器设计

- cookie jar 持久会话；首次请求先 GET 简单检索页，后续 POST `simpleSearch.action`；会话失效（响应为登录页/索引页特征）时重建会话重试一次
- `select1` 映射：默认 `all`（任意词），ISBN 形态 `isbn`（原生支持，无需深圳式整参集）
- 结果解析：命中条目（题名著者出版年）+ 分页；详情 BookDetail.action 解析书目字段与单册馆藏（实现期按实抓结构写解析器）
- 保守限速同天津（初始 3 秒/请求）

## 错误处理

- search 聚合容忍单源失败：≥1 源成功即返回存活源结果（数据原样）；三源全失败 → RuntimeError
- get_holdings：目标源失败 → RuntimeError（含馆名）；归并条目的附属源失败 → 跳过该源，返回已查到部分
- get_book_detail：目标源失败 → RuntimeError

## 测试策略

- 契约测试照旧（`_client` 模块级 monkeypatch，三源请求全部经 `_client` 内部发起，mock 才不落空网）
- fixture 先行：实现首个任务是抓两城实抓样本（天津三源各：搜索结果页/详情页/单册页；重庆：会话页/结果页/详情页），配 `tests/fixtures/tianjin/NOTES.md`、`tests/fixtures/chongqing/NOTES.md`
- 合并逻辑单测：同 ISBN 三源归并、无 ISBN 并列、优先级取主馆、馆藏跨源聚合、前缀路由
- 限速器单测（不打真网，注入时钟）；ISBN 归一化（连字符/空 ISBN/978-979 前缀）
- interlib `curlibcode` 单测：默认空不带参数（穗杭回归）、非空携带
- 全量测试不打真网（铁律）

## 文档与发布

- `docs/data-sources.md` 总览表加两行（直辖市组：上海市、北京市、天津市、重庆市，接北京行之后）；各源实测要点入对应小节
- README 支持表四城 → 六城
- 版本 0.3.0 一次发布两城；tag 触发 CI 可信发布（流程同 0.2.0）

## 范围外

- 天津 Primo（primo.tjl.tj.cn）：发现层、只盖源 A，已弃用
- 天津市少年儿童图书馆作为独立 city：已决定并入 tianjin
- 街道/社区基层服务点：数据不可考
- 北京：WAF 搁置（状态同前）

## 风险

1. **源 C 馆藏接口未验证**：`sm.interlib.cn` 的 `/opac/api/holding/{bookrecno}` 是否可用未知；不可用时按 NOTES 记录实抓，降级为仅 search+detail（holdings 返回空列表而非报错），并在发布说明注明
2. **ALEPH 翻页参数未实测**：`find-b` 结果翻页走 set_number/set_entry 偏移（侦察到 short-jump 形态）；fixture 抓取时确认，解析器按实抓写
3. **验证码阈值**：「约 8 次/几分钟」是单次观察值；限速参数实现期实测，宁可保守
4. **重庆单册状态字段**：详情页静态 HTML 未见单册状态列，可能需 `showAsset` 参数或 ajax；fixture 抓取时确认
5. **源 C 租户确认**：抓取首页确认 `curlibcode=STC001` 即中新友好图书馆（页面馆名），防张冠李戴
