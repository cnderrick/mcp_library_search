"""MCP server：城市图书馆馆藏查询——"这本书在哪些馆能借到"。

多城市架构，已接入：上海、广州、杭州（杭图＋浙图双源合并）、深圳、
天津（三源合并）、重庆、合肥（皖图＋合肥市图双源合并）、
南京（金陵图书馆＋12 区馆联合目录）、金华、江阴、温州、台州。
tool 与具体城市解耦：先用 search_books 按关键字查到 book_id，
再用它调用 find_book_availability（哪些馆有）或 get_book_detail（完整介绍）。
"""
from importlib.metadata import PackageNotFoundError, version as _pkg_version

from fastmcp import FastMCP

from mcp_library_search import adapters
from mcp_library_search.adapters.base import BookDetail, Holding, SearchPage

try:
    _VERSION = _pkg_version("mcp_library_search")
except PackageNotFoundError:
    _VERSION = "0.0.0+local"  # 源码直跑（包未安装）时兜底

mcp = FastMCP("mcp-library-search", version=_VERSION)


@mcp.tool
def search_books(keyword: str, city: str = "shanghai", page: int = 1, limit: int = 20) -> SearchPage:
    """按关键字搜索城市图书馆的馆藏图书，返回分页列表。

    已接入城市：shanghai（上海，全市 900+ 网点，含地铁站 24 小时自助机）、
    guangzhou（广州）、hangzhou（杭州，杭州图书馆＋浙江图书馆双源合并，
    同一本书跨馆归并成一条结果）、shenzhen（深圳，167 馆统一平台）、
    tianjin（天津，主馆＋少儿馆＋中新友好三源合并，同一本书跨馆归并成一条结果）、
    chongqing（重庆，馆藏到单册级；源站无明确「可借」状态词，全部保守按不可借展示，状态原值照登）、
    hefei（合肥，安徽省图书馆＋合肥市图书馆双源合并，同一本书跨馆归并成一条结果）、
    nanjing（南京，金陵图书馆＋12 区馆联合目录，馆藏到单册级；源站每页固定 20 条，limit 不生效）、
    jinhua（金华，馆藏到单册级）、jiangyin（江阴，含农家书屋等 24H 网点）、
    wenzhou（温州，全市总分馆体系）、taizhou（台州，全市通借网络含地铁站点）；
    其他城市待接入。
    keyword 可以是书名、ISBN、作者名等。每条结果带 book_id，是后续查询的凭据。
    total_results 为 null 表示数据源不提供总数：用 page 继续翻页，
    直到 has_next 为 false 或 books 为空。

    参数：
        keyword：书名、ISBN、作者等检索词
        city：城市标识，默认 "shanghai"
        page：页码，默认 1
        limit：每页条数，默认 20
    """
    try:
        return adapters.search_books(city, keyword, page=page, limit=limit)
    except Exception as e:
        raise RuntimeError(f"搜索失败：{e}") from e


@mcp.tool
def find_book_availability(book_id: str, city: str = "shanghai", only_available: bool = True) -> list[Holding]:
    """查询指定图书在各分馆的馆藏与可借状态，可借的馆排前面。

    已借出的馆藏可能带 due_date（预计归还时间，YYYY-MM-DD），仅在
    only_available=False 时出现；数据源查不到时为空串。
    重庆源站无明确「可借」状态词：only_available=True 恒为空，请用 False
    查看状态原值（入藏/借出等）与应还日期，自行判断。
    浙江图书馆源（hangzhou 双源之一）与金华源的借出馆藏拿不到应还日期
    （due_date 为空串属数据边界，非故障）；杭州图书馆源正常带应还日期。

    参数：
        book_id：search_books 返回的图书 ID，需与 search_books 使用同一 city
        city：城市标识，默认 "shanghai"
        only_available：True（默认）只返回当前可借的馆；False 返回全部馆藏
    """
    try:
        return adapters.get_holdings(city, book_id, only_available=only_available)
    except Exception as e:
        raise RuntimeError(f"查询馆藏失败：{e}") from e


@mcp.tool
def get_book_detail(book_id: str, city: str = "shanghai") -> BookDetail:
    """查询指定图书的完整介绍：书名、作者、出版社、出版年、ISBN、索书号、内容简介。

    上海数据源没有独立简介区块，内容简介取自书目"附注"字段，可能带有
    "新版本册内容："之类的原生前缀。
    南京数据源详情页无索书号字段，call_number 为空串（单册索书号在馆藏明细里）。

    参数：
        book_id：search_books 返回的图书 ID，需与 search_books 使用同一 city
        city：城市标识，默认 "shanghai"
    """
    try:
        return adapters.get_book_detail(city, book_id)
    except Exception as e:
        raise RuntimeError(f"查询图书详情失败：{e}") from e


def main() -> None:
    """console script 入口：`uvx mcp_library_search` 即以此启动 stdio 服务。"""
    mcp.run()


if __name__ == "__main__":
    main()
