"""新版 UILAS（ILAS REST 检索平台）家族共享模块。

成员：陕西省图书馆（`adapters/cn/shaanxi.py`）、榆林市图书馆
（`adapters/cn/yulin.py`）。与老版 `uilas/`（HTML OPAC）同宗不同代：新版为
前后端分离 REST，接口在 `/prod-api/*`，返回 JSON；城市差异只允许以带默认值的
`UilasRestConfig` 字段（quirk）新增。HTTP 层见 `client.py`，解析见 `parser.py`。

三原语：检索 `GET /prod-api/bookSearch/search`、详情与馆藏同走
`GET /prod-api/book/bookDetail?recno=`（书目在 `data.bookDetail`，馆藏在
`data.inList`）。`book_id` 即裸 `id`（数字字符串）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import client
from . import parser

if TYPE_CHECKING:
    from ..adapters.base import BookDetail, Holding, SearchPage


@dataclass(frozen=True)
class UilasRestConfig:
    """新版 UILAS 站点配置。quirk 字段必须带默认值。"""

    city: str       # 城市标识，如 "shaanxi"
    name_cn: str    # 报错与文档用的中文名，如 "陕西省图书馆"
    base_url: str   # 站点根地址，不含末尾斜杠
    referer: str    # 必需 Referer；须与站点页面路径一致（榆林需 `/opac/`，否则回 401）


def _search(cfg: UilasRestConfig, keyword: str, page: int, limit: int) -> dict:
    return parser.parse_search(client.request(
        cfg, "/prod-api/bookSearch/search",
        {"searchKey": keyword, "pageNum": page, "pageSize": limit}))


def search_books(cfg: UilasRestConfig, keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键字检索馆藏，返回统一分页结构。失败抛 RuntimeError（消息含中文馆名）。"""
    import math
    r = _search(cfg, keyword, page, limit)
    total = r["total_results"]
    total_pages = math.ceil(total / limit) if total > 0 and limit > 0 else 0
    return {
        "total_results": total,
        "page": page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "books": [
            {
                "book_id": b["book_id"],
                "title": b["title"],
                "author": b["author"],
                "publisher": b["publisher"],
                "publish_year": b["publish_year"],
                "availability_summary": b["availability_summary"],
            }
            for b in r["books"]
        ],
    }


def _detail(cfg: UilasRestConfig, book_id: str) -> dict:
    return parser.parse_detail(client.request(
        cfg, "/prod-api/book/bookDetail", {"recno": book_id}))


def get_holdings(cfg: UilasRestConfig, book_id: str,
                 only_available: bool = True) -> list[Holding]:
    """指定书目在各分馆的馆藏与可借状态，可借的排前面。失败抛 RuntimeError。"""
    holdings: list[Holding] = []
    for h in _detail(cfg, book_id)["holdings"]:
        if only_available and not h["available"]:
            continue
        holdings.append({
            "library": h["library"],
            "location": h["location"],
            "call_number": h["call_number"],
            "status": h["status"],
            "available": h["available"],
            "due_date": h["due_date"],
        })
    holdings.sort(key=lambda h: (not h["available"], h["library"]))
    return holdings


def get_book_detail(cfg: UilasRestConfig, book_id: str) -> BookDetail:
    """指定书目的完整介绍。失败抛 RuntimeError。"""
    b = _detail(cfg, book_id)["book"]
    if not b["title"]:
        raise RuntimeError(f"{cfg.name_cn}：未找到该书详情：{book_id}")
    return {
        "book_id": book_id,
        "title": b["title"],
        "author": b["author"],
        "publisher": b["publisher"],
        "publish_year": b["publish_year"],
        "isbn": b["isbn"],
        "call_number": b["call_number"],
        "summary": b["summary"],
    }
