# 西安市图书馆 OPAC 结构侦察（2026-10-03 实抓）

站点：`https://opac.xalib.org.cn/opac3/index`（西安市公共图书馆集群信息化管理
平台，`<meta name="keywords">` 自报「opac, 图创, interlib」）。图创 Interlib
**pro2018 模板代**，应用上下文 **`/opac3`**（非 `/opac`）。抓取只读 GET，
无 401／验证码。

## fixture 清单

| 文件 | 来源 | 说明 |
|---|---|---|
| `index.html` | `GET /opac3/index` | 首页（meta keywords 指纹） |
| `search_p1.html` | `GET /opac3/search?q=三体&…&rows=10&page=1` | pro2018 搜索第 1 页（检索到 139 条、共 14 页） |
| `search_empty.html` | 生造关键词 | 0 条 |
| `detail_api.json` | `GET /opac3/api/book/902511096` | 书目 JSON（详情走此接口） |
| `holding.json` | `GET /opac3/api/holding/902511096?limitLibcodes=&isCluster=` | 馆藏 JSON，4 册在馆 |

## 与广州基准的差异（均以家族配置字段表达）

1. **应用上下文 `/opac3`**：家族新增 `InterlibConfig.ctx`（默认 `/opac`）。
2. **pro2018 模板**：`pro2018=True`，搜索条目 `libBookLi`，家族 `parse_search_pro2018` 零改动；
   详情亦可用 pro2018 解析。
3. **详情走 `/api/book/{recno}` JSON**：`api_detail=True`。各 Interlib 站点均提供该接口，
   返回 `{biblios:{title,author,publisher,pubdate,isbn,classNo,summary,…}, holdings:[…]}`；
   比 HTML 详情页更稳（不受页面截断/模板差异影响）。
4. 馆藏 `/api/holding/{recno}` 与广州基准同构，家族 parser 零改动。
5. 不需要 `curlibcode`。

## 其他

- pro2018 搜索分页按家族既有口径（JS 变量 `totalPage`/`currentPage`）。
- 集群平台含碑林区图书馆等成员馆（馆藏译名照登）。
