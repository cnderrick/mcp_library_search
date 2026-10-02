"""成都适配器：图创 Interlib 家族（pro2018 模板代，simple 简版皮肤）。

成都市公共图书馆联合书目检索（https://opac.cdclib.cn，主馆成都图书馆 CD101，
联合目录跨成都平原经济区：成都辖区＋德阳/眉山/资阳等市县馆，libcodeMap 483 馆码）。
厂商定性：meta keywords 自报「opac, 图创, interlib」、页脚 © www.interlib.com.cn、
静态资源 /opac/media/pro2018/simple/，实为图创 Interlib pro2018 模板代
（证据链见 tests/fixtures/chengdu/NOTES.md）。

pro2018 解析自 2026-10-02 起由家族内置（`InterlibConfig(pro2018=True)` 开关），
本模块只是薄包装：HTTP 层与馆藏层直接复用家族（holding JSON 与广州基准完全同构，
state=2→在馆/3→借出经家族词表判定）。detail 的 `?return_fmt=json` 完整 MARC 是
可选增强，HTML 详情已覆盖契约全字段，未采用。

节流：家族 client 无限速，本模块自带 ≥2 秒/host 保守节流（单 host opac.cdclib.cn，
源站未见限频，留余量；单测 monkeypatch _throttle 关闭）。

薄包装 + 契约测试兼容缝同台州：公开原语全部经由模块级 _client 取数，
契约测试（tests/test_adapter_contract.py）monkeypatch 的就是这个 _client，
因此不能把三个原语写成对底层函数的直连委托——那样 mock 会落空、
测试会真打图书馆网站。
"""
import time
from dataclasses import dataclass
from types import SimpleNamespace

from ... import interlib
from ...interlib import InterlibConfig
from ..base import BookDetail, BookSummary, Holding, SearchPage

_CONFIG = InterlibConfig(
    city="chengdu", name_cn="成都图书馆", base_url="https://opac.cdclib.cn",
    pro2018=True,
)

_THROTTLE = 2.0  # 秒/host 最小间隔（任务口径 ≥2 秒，源站未见限频仍保守）
_last_request = 0.0


def _throttle():
    """最小间隔限速：距上次请求不足 _THROTTLE 秒时睡足差值（单 host）。"""
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


# ---------- 契约缝（与台州/广州/杭州同款） ----------


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
    """把家族解析返回值包装成契约测试期望的 attribute 对象形态。"""

    def search(self, keyword, page=1, limit=20):
        _throttle()
        # 家族 search_raw：pro2018 搜索解析 + 带连字符 ISBN 首搜为空时去连字符重试
        r = interlib.search_raw(_CONFIG, keyword, page, limit)
        return SimpleNamespace(
            success=True,
            error="",
            statistics={"total_results": r["total_results"], "page": page,
                        "total_pages": r["total_pages"], "has_next": r["has_next"]},
            # 家族 TypedDict 用 book_id，契约形态用 record_id，此处显式映射
            books=[SimpleNamespace(record_id=b["book_id"], title=b["title"],
                                   author=b["author"], publisher=b["publisher"],
                                   publish_year=b["publish_year"],
                                   availability_summary=b["availability_summary"])
                   for b in r["books"]],
        )

    def get_holdings(self, book_id):
        # 馆藏 JSON 与广州基准完全同构，直接走家族原语（NOTES.md 实抓验证：
        # 98 条全部解析成功，state=2→在馆/3→借出经家族词表判定）
        _throttle()
        hs = interlib.get_holdings(_CONFIG, book_id, only_available=False)
        return [_Holding(**h) for h in hs]

    def get_book_detail(self, book_id):
        _throttle()
        d = interlib.get_book_detail(_CONFIG, book_id)
        return SimpleNamespace(**d)


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"成都图书馆搜索失败：{result.error}")

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
            "due_date": getattr(h, "due_date", "") or "",
        }
        # 契约测试要求已借出且带单册 item_id 时查归还时间；Interlib 的应还日期
        # 已在馆藏 JSON 里解析（loanWorkMap.returnDate），真网 item_id 恒空不会走到这
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
