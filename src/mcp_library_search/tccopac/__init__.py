"""图创 tcc-opac 家族共享模块（Java/Spring＋Vue2 SPA，纯 JSON＋JWT 访客令牌）。

与图创 Interlib 是不同产品线，不可复用 `interlib/` 家族。成员：宁波市图书馆
（`adapters/cn/ningbo.py`）、济南市图书馆（`adapters/cn/jinan.py`）、
鄂尔多斯市图书馆（`adapters/cn/eerduosi.py`）。城市差异只允许以带默认值的
`TccOpacConfig` 字段（quirk）新增，默认值即宁波行为。

base_url 形态 `{host}/api/tcc-opac/{首段路径}`（如宁波
`https://opac.nblib.cn/api/tcc-opac/999`）；referer 取站点页面路径（如
`https://opac.nblib.cn/999`）。HTTP 层见 `client.py`，解析见 `parser.py`。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import client
from . import parser

if TYPE_CHECKING:
    from ..adapters.base import BookDetail, Holding, SearchPage

_MAX_SIZE = 50      # 检索每页条数上限（SPA 界面只给 10/15/20，保守）
_HOLD_SIZE = 500    # 馆藏一页全量，前端同款
_DETAIL_FIELDS = "300a,314a,327a,330a"  # 附注字段，前端同款


@dataclass(frozen=True)
class TccOpacConfig:
    """tcc-opac 站点配置。quirk 字段必须带默认值。"""

    city: str       # 城市标识，如 "ningbo"
    name_cn: str    # 报错与文档用的中文名
    base_url: str   # API 根：{host}/api/tcc-opac/{seg}，不含末尾斜杠
    referer: str    # 站点页面路径，作 Referer 头


def search_books(cfg: TccOpacConfig, keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键字搜索，返回统一分页结构。上游报错（含风控）抛 RuntimeError。"""
    try:
        size = max(1, min(int(limit), _MAX_SIZE))
    except (TypeError, ValueError):
        size = 20
    page = max(1, int(page or 1))
    payload = {
        "current": page,
        "size": size,
        "searchWay": "marc",  # 任意词；isbn 专有码表项因存储连字符形态不一未启用
        "sortWay": "score",
        "sortOrder": "desc",
        "hasholding": 1,      # 1=只看有馆藏（源站默认）；0=只看无馆藏，勿用
        "q": str(keyword or ""),
        "facetFieldSearch": {},
    }
    r = parser.parse_search(client.post(cfg, "/search/", payload), cfg.name_cn)
    total = r["total_results"]
    total_pages = math.ceil(total / size) if total else 0
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


def get_holdings(cfg: TccOpacConfig, book_id: str,
                 only_available: bool = True) -> list[Holding]:
    """指定图书在各成员馆的馆藏（单册级），可借的排前面。失败抛 RuntimeError。"""
    bid = parser.check_book_id(book_id, cfg.name_cn)
    rows = parser.parse_holdings(
        client.post(cfg, "/service/hold/pagelist",
                    {"current": 1, "size": _HOLD_SIZE, "bibliosId": bid}), cfg.name_cn)
    holdings: list[Holding] = []
    for h in rows:
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


def get_book_detail(cfg: TccOpacConfig, book_id: str) -> BookDetail:
    """指定书目的完整介绍。聚合条目无本地书目时抛 RuntimeError。"""
    bid = parser.check_book_id(book_id, cfg.name_cn)
    d = parser.parse_detail(
        client.post(cfg, "/service/biblios/getbyid", None,
                    params={"id": bid, "fields": _DETAIL_FIELDS}), bid, cfg.name_cn)
    return {
        "book_id": bid,
        "title": d["title"],
        "author": d["author"],
        "publisher": d["publisher"],
        "publish_year": d["publish_year"],
        "isbn": d["isbn"],
        "call_number": d["call_number"],
        "summary": d["summary"],
    }
