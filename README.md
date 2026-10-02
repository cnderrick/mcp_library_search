# mcp_library_search

[![PyPI version](https://img.shields.io/pypi/v/mcp_library_search)](https://pypi.org/project/mcp-library-search/)

MCP server：查询城市图书馆的馆藏与可借状态——回答"这本书在哪些馆能借到"。

## 支持情况

| 城市 | 标识 | 状态 | 数据源 |
|---|---|---|---|
| 上海 | `shanghai` | ✅ 已接入 | 上海中心图书馆"一卡通"总分馆体系（900+ 网点，含地铁站 24 小时自助机） |
| 广州 | `guangzhou` | ✅ 已接入 | 广州图书馆（图创 Interlib） |
| 杭州 | `hangzhou` | ✅ 已接入 | 杭州图书馆＋浙江图书馆双源合并（同一本书跨馆归并成一条结果） |
| 深圳 | `shenzhen` | ✅ 已接入 | 深圳图书馆之城统一平台（自研 JSON API，167 馆） |
| 天津 | `tianjin` | ✅ 已接入 | 天津图书馆等三源合并（主馆＋少儿馆＋中新友好图书馆，同一本书跨馆归并成一条结果） |
| 重庆 | `chongqing` | ✅ 已接入 | 重庆 InDigLib 集群数字图书馆 |
| 合肥 | `hefei` | ✅ 已接入 | 安徽省图书馆＋合肥市图书馆双源合并（同一本书跨馆归并成一条结果） |
| 南京 | `nanjing` | ✅ 已接入 | 金陵图书馆＋12 区馆联合目录 ＋ 南京图书馆（江苏省图）双源合并，馆藏到单册级；南图源走 Ex Libris ALEPH，有验证码墙 |
| 成都 | `chengdu` | ✅ 已接入 | 成都平原经济区联合目录（图创 Interlib pro2018） |
| 宁波 | `ningbo` | ✅ 已接入 | 宁波市图书馆全市联合目录（图创 tcc-opac） |
| 绍兴 | `shaoxing` | ✅ 已接入 | 绍兴市公共图书馆联合目录（图创 Interlib pro2018） |
| 大连 | `dalian` | ✅ 已接入 | 大连地区网上联合目录（SirsiDynix iLink） |
| 金华 | `jinhua` | ✅ 已接入 | 金华市图书馆（UILAS HTML OPAC） |
| 江阴 | `jiangyin` | ✅ 已接入 | 江阴市图书馆（图创 Interlib，含农家书屋等 24H 网点） |
| 温州 | `wenzhou` | ✅ 已接入 | 温州市图书馆（图创 Interlib，全市总分馆体系） |
| 台州 | `taizhou` | ✅ 已接入 | 台州市图书馆（图创 Interlib pro2018，含地铁站点通借） |
| 青岛 | `qingdao` | ✅ 已接入 | 青岛市公共图书馆联合目录（图创 Interlib，26 馆联合，检索走站点 Solr 通道） |
| 无锡 | `wuxi` | ✅ 已接入 | 无锡市新吴区图书馆（图星 LibStar Find；市图书馆源预留未接入） |
| 扬州 | `yangzhou` | ✅ 已接入 | 扬州市图书馆联盟联合目录（汇文 uopac，与南京金陵源同系统；站点 securitycam 反爬按静态挑战处理） |
| 苏州 | `suzhou` | ✅ 已接入 | 苏州图书馆全市集群目录（图创 Interlib，馆藏到单册级） |
| 更多城市 | — | 欢迎提需求或贡献适配器 | 北京等因站点侧限制暂未接入，详见 docs/data-sources/README.md |

## 安装

### Claude Code

```bash
claude mcp add mcp-library-search -- uvx mcp_library_search
```

### Claude Desktop

在 `claude_desktop_config.json` 里加：

```json
"mcpServers": {
  "mcp-library-search": {
    "command": "uvx",
    "args": ["mcp_library_search"]
  }
}
```

改完重启桌面版。

## 使用

接入后提供 3 个 tool，查询链路为：先 `search_books` 按关键字找到 `book_id`，再用它查馆藏或详情。都带 `region` 与 `city` 两个定位参数：`region` 是地区标识（取域名后缀），默认 `cn`（中国）；`city` 默认 `shanghai`。未接入的地区或城市会返回明确提示：

| tool | 作用 |
|---|---|
| `search_books(keyword, region, city, page, limit)` | 按关键字（书名、ISBN、作者等）搜书，返回分页列表，每条带 `book_id` 和可借概况 |
| `find_book_availability(book_id, region, city, only_available)` | 查这本书在哪些馆有、是否可借，可借的馆排前面；`only_available=False` 时已借出的馆藏带预计归还时间（`due_date`） |
| `get_book_detail(book_id, region, city)` | 查这本书的完整介绍（ISBN、索书号、内容简介） |

典型用法：对 Claude 说"帮我查《三体》在哪个馆能借到" → 搜书拿到 `book_id` → 查各馆可借状态 → 就近推荐。

## 赞赏

如果这个项目帮到了你，欢迎打赏支持：

<a href="https://github.com/cnderrick/mcp_library_search/raw/main/assets/alipay.JPG"><img src="https://github.com/cnderrick/mcp_library_search/raw/main/assets/alipay.JPG" width="240" alt="支付宝收款码"></a>
<a href="https://github.com/cnderrick/mcp_library_search/raw/main/assets/wxpay.JPG"><img src="https://github.com/cnderrick/mcp_library_search/raw/main/assets/wxpay.JPG" width="240" alt="微信收款码"></a>

## 致谢

- [shanghai-library-book-search-python](https://github.com/ZedeX/shanghai-library-book-search-python)——上海图书馆检索能力的来源（Apache-2.0）。

完整的第三方组件列表、归属与变更说明见 [NOTICE](NOTICE)。
