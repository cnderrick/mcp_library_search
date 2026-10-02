"""扬州适配器：扬州市图书馆联盟联合目录（汇文 Libsys/uopac）。

站点 http://ytlmopac.cn:8080，页头「扬州市图书馆联盟馆藏书目检索 v1.0」，
覆盖扬州市图书馆与邗江区图书馆等成员馆（联合目录口径，不做成员馆过滤，
同金陵「全市联合」口径）。页面结构与金陵同系统、逐项同构，解析走 `uopac/`
家族模块；**两站唯一差别是本站全路径要求 securitycam cookie**（金陵匿名全通）。

那层反爬是**静态挑战**：壳页里 key/IV/密文三个常量硬编码、跨请求逐字节相同
（只有回显的跳转 URL 不同），解出的 cookie 是个固定值，所以直接把常量放进
UopacConfig.securitycam，不引入 JS 引擎也不移植 slowAES。常量若被站方轮换，
uopac 家族 client 认出壳页就会抛含馆名的错误（不静默退化成空结果），
重算一条命令，步骤见 tests/fixtures/yangzhou/NOTES.md。

字段侦察结论见 tests/fixtures/yangzhou/NOTES.md：
- 详情页无索书号字段，call_number 恒空串（中图法分类号不冒充）；
- 状态词表实测只有「可借」「借出」，后者源站不给应还日期 → due_date 恒空串
  （数据边界，非故障）；
- ISBN 索引按「存储原样」前缀匹配，走数字间插 `*` 的通配（meta=14）——
  与金陵同一策略，通配路由与状态词表都在 uopac 家族里。
"""
from .. import uopac
from ..uopac import UopacConfig
from .base import BookDetail, BookSummary, Holding, SearchPage

_THROTTLE = 4.0  # 秒/host，按 spec 保守限速

# 壳页（slowAES 静态挑战）解出的固定 cookie，推导过程与重算命令见 NOTES.md
_SECURITYCAM = "6322e5171be855cb6e0f4e8b640895e6"

_YZ = UopacConfig(
    name_cn="扬州市图书馆联盟",
    base_url="http://ytlmopac.cn:8080",
    securitycam=_SECURITYCAM,
    throttle=_THROTTLE,
)


class _Client:
    """单源客户端：全部委托 uopac 家族；book_id 即源站 uopac 原生数字 id。"""

    def search(self, keyword, page=1, limit=20):
        r = uopac.search_raw(_YZ, keyword, page=page)
        return uopac.SearchResult(
            success=True,
            error="",
            statistics={
                "total_results": r["total_results"],
                "page": page,
                "total_pages": r["total_pages"],
                "has_next": page < r["total_pages"],
            },
            books=r["books"],
        )

    def get_holdings(self, book_id):
        holdings = uopac.get_holdings(_YZ, book_id)
        holdings.sort(key=lambda h: (not h.available, h.library))
        return holdings

    def get_book_detail(self, book_id):
        return uopac.get_book_detail(_YZ, book_id)

    def get_return_date(self, item_id):
        """源站无按单册查归还日期的接口：应还日期在馆藏响应里直取。

        扬州馆藏不带 item_id，模块级 get_holdings 的补查分支真网永不触发；
        定义仅为对齐契约形状。
        """
        raise RuntimeError(f"扬州：无单册归还日期接口：{item_id}")


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索扬州市图书馆联盟联合目录。上游报错抛 RuntimeError。

    源站每页固定 20 条，limit 参数不生效（数据边界，翻页请用 page）。
    """
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"扬州市图书馆联盟搜索失败：{result.error}")

    books: list[BookSummary] = [
        {
            "book_id": b.record_id,
            "title": b.title,
            "author": b.author,
            "publisher": b.publisher,
            "publish_year": b.publish_year,
            "availability_summary": b.availability_summary,
        }
        for b in (result.books or [])
    ]
    stats = result.statistics or {}
    return {
        "total_results": stats.get("total_results"),
        "page": stats.get("page", page),
        "total_pages": stats.get("total_pages", 1),
        "has_next": stats.get("has_next", False),
        "books": books,
    }


def get_holdings(book_id: str, only_available: bool = True) -> list[Holding]:
    """指定图书在各成员馆的馆藏与可借状态，可借的排前面。

    每持有馆一次代理请求（1+N），多馆持有的书响应较慢（4 秒节流）。
    """
    holdings = _client.get_holdings(book_id) or []
    kept = [h for h in holdings if (not only_available or h.is_available())]
    items: list[Holding] = []
    for h in kept:
        available = h.is_available()
        item: Holding = {
            "library": h.library,
            "location": h.location,
            "call_number": h.call_number,
            "status": h.status,
            "available": available,
            "due_date": getattr(h, "due_date", "") or "",
        }
        # 契约形态兼容分支：扬州数据无 item_id，真网路径不会触发
        if not available and getattr(h, "item_id", ""):
            item["due_date"] = _client.get_return_date(h.item_id)
        items.append(item)
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(book_id: str) -> BookDetail:
    """指定图书的完整详情：书名、作者、出版社、出版年、ISBN、索书号、内容简介。"""
    b = _client.get_book_detail(book_id)
    return {
        "book_id": book_id,
        "title": b.title,
        "author": b.author,
        "publisher": b.publisher,
        "publish_year": b.publish_year,
        "isbn": b.isbn,
        "call_number": b.call_number,
        "summary": b.summary,
    }
