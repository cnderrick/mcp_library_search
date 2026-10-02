"""上海适配器：vendor 的 LibraryClient → base.py 统一模型。"""
from ...vendor.shanghai_library.library_client import LibraryClient
from ..base import BookDetail, BookSummary, Holding, SearchPage

_client = LibraryClient()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"上海图书馆搜索失败：{result.error}")

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
    raw_total = result.statistics.get("total_results", 0)
    return {
        # 站点统计区不再输出总条数（解析结果恒为 0）：
        # 总数为 0 且当前页有结果 → 视为未知（null）；当前页无结果 → 真的为 0
        "total_results": raw_total if raw_total > 0 else (None if books else 0),
        "page": result.statistics.get("page", page),
        "total_pages": result.statistics.get("total_pages", 1),
        "has_next": result.statistics.get("has_next", False),
        "books": books,
    }


def get_holdings(book_id: str, only_available: bool = True) -> list[Holding]:
    """指定图书在各分馆的馆藏与可借状态，可借的排前面。"""
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
            "due_date": "",
        }
        # 已借出的馆藏带单册 item_id，逐个查预计归还时间（单册级接口），失败留空串
        if not available and getattr(h, "item_id", ""):
            item["due_date"] = _client.get_return_date(h.item_id)
        items.append(item)
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(book_id: str) -> BookDetail:
    """指定图书的完整书目信息（含 ISBN、内容简介）。查不到抛 RuntimeError。"""
    book = _client.get_book_detail(book_id)
    if book is None:
        raise RuntimeError(f"未找到该书的详情：{book_id}")
    return {
        "book_id": book.record_id,
        "title": book.title,
        "author": book.author,
        "publisher": book.publisher,
        "publish_year": book.publish_year,
        "isbn": book.isbn,
        "call_number": book.call_number,
        "summary": book.summary,
    }
