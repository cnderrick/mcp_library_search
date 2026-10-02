"""舟山适配器：UILAS 知识检索平台（`uilas/` 家族）→ base.py 统一模型。

薄包装 + 契约测试兼容缝：公开原语全部经由模块级 _client 取数，
契约测试（tests/test_adapter_contract.py）monkeypatch 的就是这个 _client，
因此不能把三个原语写成对 uilas 函数的直连委托——那样 mock 会落空、
测试会真打图书馆网站。

站点 `https://opac.zsodl.cn/Index?target=0`（页标题「UILAS知识检索平台」），
与金华同款 UILAS，协议与解析见 `uilas/` 家族。字段侦察结论见
tests/fixtures/zhoushan/NOTES.md。

**旧式 TLS quirk（本城相对金华的唯一差异）**：站点只支持静态 RSA 密钥交换的
TLS 1.2 密码套件，OpenSSL 3.5 默认密码列表已停用它们，默认 urllib 上下文会
`SSLV3_ALERT_HANDSHAKE_FAILURE`。配置 `ssl_ciphers` 让家族 HTTP 层显式放行。
还有一处：检索结果页 total 锚点形态是「共有 [N]条记录」（同金华）。
"""
from dataclasses import dataclass
from types import SimpleNamespace

from ... import uilas
from ...uilas import UilasConfig
from ..base import BookDetail, BookSummary, Holding, SearchPage

_CONFIG = UilasConfig(
    city="zhoushan", name_cn="舟山市图书馆", base_url="https://opac.zsodl.cn",
    ssl_ciphers="AES256-GCM-SHA384:AES128-GCM-SHA256",
)


@dataclass
class _Holding:
    """与上海 vendor 客户端同形的馆藏对象（契约测试按此形态注入）。"""

    library: str = ""
    location: str = ""
    call_number: str = ""
    status: str = ""
    available: bool = False
    item_id: str = ""
    due_date: str = ""

    def is_available(self):
        return self.available


class _Client:
    """把 uilas 家族返回值包装成契约测试期望的 attribute 对象形态。"""

    def search(self, keyword, page=1, limit=20):
        r = uilas.search_books(_CONFIG, keyword, page=page, limit=limit)
        return SimpleNamespace(
            success=True,
            error="",
            statistics={k: r[k] for k in ("total_results", "page", "total_pages", "has_next")},
            books=[SimpleNamespace(record_id=b["book_id"], title=b["title"],
                                   author=b["author"], publisher=b["publisher"],
                                   publish_year=b["publish_year"],
                                   availability_summary=b["availability_summary"])
                   for b in r["books"]],
        )

    def get_holdings(self, book_id):
        hs = uilas.get_holdings(_CONFIG, book_id, only_available=False)
        return [_Holding(**h) for h in hs]

    def get_book_detail(self, book_id):
        return SimpleNamespace(**uilas.get_book_detail(_CONFIG, book_id))


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"舟山市图书馆搜索失败：{result.error}")

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
    """指定图书的单册级馆藏：索书号、馆藏地点、状态原值。

    状态词表仅「入藏（可借）/借出」，词表外保守不可借；借出单册源站不给
    应还日期 → due_date 恒空（数据边界，非故障）。
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
        if not available and getattr(h, "item_id", ""):
            item["due_date"] = _client.get_return_date(h.item_id)
        items.append(item)
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(book_id: str) -> BookDetail:
    """指定图书的完整详情：书名、作者、出版社、出版年、ISBN、索书号、内容简介。

    内容简介取详情页内联「附注提要」原值；无附注则空串。
    """
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
