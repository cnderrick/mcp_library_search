# mcp_library_search

[![PyPI version](https://img.shields.io/pypi/v/mcp_library_search)](https://pypi.org/project/mcp-library-search/)

MCP server：查询城市图书馆的馆藏与可借状态——回答"这本书在哪些馆能借到"。

## 支持情况

| 城市 | 标识 | 状态 | 数据源 |
|---|---|---|---|
| 上海 | `shanghai` | ✅ 已接入 | 上海中心图书馆"一卡通"总分馆体系（900+ 网点，含地铁站 24 小时自助机） |
| 广州 | `guangzhou` | ✅ 已接入 | 广州图书馆（图创 Interlib） |
| 杭州 | `hangzhou` | ✅ 已接入 | 杭州图书馆（图创 Interlib） |
| 深圳 | `shenzhen` | ✅ 已接入 | 深圳图书馆之城统一平台（自研 JSON API，167 馆） |
| 更多城市 | — | 欢迎提需求或贡献适配器 | — |

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

接入后提供 3 个 tool，查询链路为：先 `search_books` 按关键字找到 `book_id`，再用它查馆藏或详情。都带 `city` 参数（默认 `shanghai`，未接入的城市会返回明确提示）：

| tool | 作用 |
|---|---|
| `search_books(keyword, city, page, limit)` | 按关键字（书名、ISBN、作者等）搜书，返回分页列表，每条带 `book_id` 和可借概况 |
| `find_book_availability(book_id, city, only_available)` | 查这本书在哪些馆有、是否可借，可借的馆排前面；`only_available=False` 时已借出的馆藏带预计归还时间（`due_date`） |
| `get_book_detail(book_id, city)` | 查这本书的完整介绍（ISBN、索书号、内容简介） |

典型用法：对 Claude 说"帮我查《三体》在哪个馆能借到" → 搜书拿到 `book_id` → 查各馆可借状态 → 就近推荐。

## 赞赏

如果这个项目帮到了你，欢迎打赏支持：

<a href="https://github.com/cnderrick/mcp_library_search/raw/main/assets/alipay.JPG"><img src="https://github.com/cnderrick/mcp_library_search/raw/main/assets/alipay.JPG" width="240" alt="支付宝收款码"></a>
<a href="https://github.com/cnderrick/mcp_library_search/raw/main/assets/wxpay.JPG"><img src="https://github.com/cnderrick/mcp_library_search/raw/main/assets/wxpay.JPG" width="240" alt="微信收款码"></a>

左：支付宝，右：微信。

## 致谢

- [shanghai-library-book-search-python](https://github.com/ZedeX/shanghai-library-book-search-python)——上海图书馆检索能力的来源（Apache-2.0）。

完整的第三方组件列表、归属与变更说明见 [NOTICE](NOTICE)。
