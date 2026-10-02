"""汉中适配器：图星 LibStar Find 家族。

薄包装 + 契约测试兼容缝：公开原语全部经由模块级 _client 取数，
契约测试（tests/test_adapter_contract.py）monkeypatch 的就是这个 _client，
因此不能把三个原语写成对 libstar 函数的直连委托——那样 mock 会落空、
测试会真打图书馆网站。

站点 `https://findhanzhong.libsp.cn`，与无锡新吴/徐州/淮安/盐城同款图星
LibStar Find，协议见 `libstar/` 家族。字段侦察结论见
tests/fixtures/hanzhong/NOTES.md。租户号 `groupCode=100121`（`POST
/find/homePage/getGroupCode {mappingPath:""}` 查得）。两个必需请求头
（`Referer`＋`groupcode`）由家族 client 统一注入。本城单实例，`book_id`
即裸 `recordId`。
"""
from dataclasses import dataclass
from types import SimpleNamespace

from ... import libstar
from ...libstar import LibStarConfig
from ..base import BookDetail, BookSummary, Holding, SearchPage

_CONFIG = LibStarConfig(
    city="hanzhong", name_cn="汉中市图书馆",
    base_url="https://findhanzhong.libsp.cn", groupcode="100121",
)


@dataclass
class _Holding:
    """与上海 vendor 客户端同形的馆藏对象（契约测试按此形态注入）。"""

    library: str = ""
    location: str = ""
    call_number: str = ""
    status: str = ""
    available: bool = True
    item_id: str = ""
    due_date: str = ""

    def is_available(self):
        return self.available


class _Client:
    """把 libstar 家族返回值包装成契约测试期望的 attribute 对象形态。"""

    def search(self, keyword, page=1, limit=20):
        r = libstar.search_books(_CONFIG, keyword, page=page, limit=limit)
        return SimpleNamespace(
            success=True,
            error="",
            statistics={k: r[k] for k in ("total_results", "page", "total_pages", "has_next")},
            # 家族契约用 book_id，契约形态用 record_id，此处显式映射
            books=[SimpleNamespace(record_id=b["book_id"], title=b["title"],
                                   author=b["author"], publisher=b["publisher"],
                                   publish_year=b["publish_year"],
                                   availability_summary=b["availability_summary"])
                   for b in r["books"]],
        )

    def get_holdings(self, book_id):
        hs = libstar.get_holdings(_CONFIG, book_id, only_available=False)
        return [_Holding(**h) for h in hs]

    def get_book_detail(self, book_id):
        return SimpleNamespace(**libstar.get_book_detail(_CONFIG, book_id))


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索汉中市图书馆馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"汉中市图书馆搜索失败：{result.error}")

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
    """指定图书的馆藏与可借状态，可借的排前面。"""
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
        # 契约测试要求已借出且带单册 item_id 时查归还时间。本城应还日期已内嵌在
        # 馆藏状态串里解析出来，故仅在日期缺失时才补查——真网家族馆藏不带
        # item_id（日期必有），不会走到这
        if not available and getattr(h, "item_id", "") and not item["due_date"]:
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
