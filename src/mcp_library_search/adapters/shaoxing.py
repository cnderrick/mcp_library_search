"""绍兴适配器：图创 Interlib 家族（pro2018 模板代，与台州/成都同族）。

绍兴图书馆（https://opac.sxlib.com，「绍兴市公共图书馆联合目录」，成员
sxslib 绍兴图书馆/syslib 上虞图书馆/999 中心馆，localMap 737 个馆藏地）。
HTTP 层与馆藏层（馆藏 JSON 与广州完全同构，家族参数形态 `limitLibcodes=&isCluster=`
实测可用）直接复用家族；搜索页（libBookLi 模板）与详情页（bkTxt 模板）是
pro2018 模板代——家族自 2026-10-02 起内置该模板解析（`InterlibConfig(pro2018=True)`
开关），本模块不再自带本地解析副本。

绍兴在 pro2018 基线上的差异（tests/fixtures/shaoxing/NOTES.md）：
- 详情页无「主要责任者」「内容提要」标签（实抓记录均缺）→ 责任者从引文块
  `div.sendToConIn` 兜底（「刘慈欣著.三体.重庆出版社,2010.11.」取首个句点前段，
  原值照登）——对应 `pro2018_cite_author=True`；summary 恒空串（数据边界）；
- 联合层书目可能无本地单册（《三体》1227282 单书 GET 与批量 POST 均 0 条，
  而鲁迅类书目有单册）——holdingList 空照实返回空列表，不是故障；
- 检索页「在馆」计数由前端批量 POST `/opac/api/holding/getHoldingsBybookrecnos`
  异步渲染（form 体 `bookrecnos=id1,id2,`），适配器不依赖该端点，单书馆藏走
  家族 GET（有单册的书目实测返回完整 holdingList+holdStateMap）。

薄包装 + 契约测试兼容缝同台州/广州：公开原语全部经由模块级 _client 取数，
契约测试（tests/test_adapter_contract.py）monkeypatch 的就是这个 _client，
因此不能把三个原语写成对底层函数的直连委托——那样 mock 会落空、
测试会真打图书馆网站。
"""
from dataclasses import dataclass
from types import SimpleNamespace

from .. import interlib
from ..interlib import InterlibConfig
from .base import BookDetail, BookSummary, Holding, SearchPage

_CONFIG = InterlibConfig(
    city="shaoxing", name_cn="绍兴图书馆", base_url="https://opac.sxlib.com",
    pro2018=True, pro2018_cite_author=True,
)


# ---------- 契约缝（与台州/广州同款） ----------


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
        # 馆藏 JSON 与广州完全同构且家族参数形态实测可用（holding_879551 实证），
        # 直接走家族原语；联合层书目无本地单册时返回空列表（数据边界，非故障）
        hs = interlib.get_holdings(_CONFIG, book_id, only_available=False)
        return [_Holding(**h) for h in hs]

    def get_book_detail(self, book_id):
        d = interlib.get_book_detail(_CONFIG, book_id)
        return SimpleNamespace(**d)


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索绍兴市公共图书馆联合目录。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"绍兴图书馆搜索失败：{result.error}")

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

    联合层书目可能无本地单册（空列表，数据边界）。
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
        # 契约测试要求已借出且带单册 item_id 时查归还时间；Interlib 的应还日期
        # 已在馆藏 JSON 里解析（loanWorkMap.returnDate），真网 item_id 恒空不会走到这
        if not available and getattr(h, "item_id", ""):
            item["due_date"] = _client.get_return_date(h.item_id)
        items.append(item)
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(book_id: str) -> BookDetail:
    """指定图书的完整详情：书名、作者、出版社、出版年、ISBN、索书号、内容简介。

    绍兴详情页无「内容提要」标签行，summary 恒空串（数据边界）；责任者从
    引文块兜底（原值照登，含「著/编」字样）。
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
