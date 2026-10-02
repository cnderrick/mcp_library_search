"""图星 LibStar Find 家族共享模块（北京图星／超星集团）。

统一检索/发现系统，Java/Spring 后端，响应包封 `{success, message, errCode,
data}`。成员：无锡市新吴区图书馆（`adapters/cn/wuxi.py`，多源预留）、徐州
（`adapters/cn/xuzhou.py`）等。城市差异只允许以带默认值的 `LibStarConfig`
字段（quirk）新增；公共 HTTP 层见 `client.py`，解析见 `parser.py`。

本模块三原语为单实例实现（record_id 即 book_id）。需要多实例按 ISBN 归并的
城市（如无锡预留的市图源）在各自适配器内包装本模块的 `search_raw` 原语，
归并口径照天津。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import client
from . import parser

if TYPE_CHECKING:
    from ..adapters.base import BookDetail, Holding, SearchPage


@dataclass(frozen=True)
class LibStarConfig:
    """LibStar 系图书馆的城市配置。quirk 字段必须带默认值。"""

    city: str       # 城市标识，如 "xuzhou"
    name_cn: str    # 报错与文档用的中文名，如 "徐州市图书馆"
    base_url: str   # 站点根地址，不含末尾斜杠，如 "https://findxz.libsp.com"
    groupcode: str  # 租户号，请求头 groupcode；缺失时站点静默 0 结果


# 检索请求体模板（约 30 个固定字段）：只有 searchFieldContent / page / rows 随调用
# 变化。逐次 dict(...) 复制，免得关键词串到下一次请求。
SEARCH_BODY = {
    "docCode": [None], "searchFieldContent": "", "searchField": "keyWord", "matchMode": "2",
    "resourceType": [], "subject": [], "discode1": [], "publisher": [], "libCode": [],
    "locationId": [], "eCollectionIds": [], "neweCollectionIds": [], "curLocationId": [],
    "campusId": [], "kindNo": [], "collectionName": [], "author": [], "langCode": [],
    "countryCode": [], "publishBegin": None, "publishEnd": None, "coreInclude": [],
    "ddType": [], "verifyStatus": [], "group": [], "sortField": "relevance",
    "sortClause": "asc", "page": 1, "rows": 10, "onlyOnShelf": None, "searchItems": None,
    "newCoreInclude": [], "customSub": [], "customSub0": [], "indexSearch": 1,
}


def search_raw(cfg: LibStarConfig, keyword: str, page: int = 1, limit: int = 20) -> dict:
    """检索并返回 parser 原始结构（books 条目含 isbn 内部字段，book_id 为 record_id）。

    供多源归并的城市使用；search_books 是它的契约形态包装。
    """
    payload = dict(SEARCH_BODY, searchFieldContent=str(keyword or ""),
                   page=page, rows=limit)
    return parser.parse_search(
        client.request(cfg, "/find/unify/search", payload=payload), cfg.name_cn)


def search_books(cfg: LibStarConfig, keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键字检索馆藏，返回统一分页结构。失败抛 RuntimeError（消息含中文馆名）。"""
    r = search_raw(cfg, keyword, page, limit)
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


def get_holdings(cfg: LibStarConfig, book_id: str,
                 only_available: bool = True) -> list[Holding]:
    """指定书目在各分馆的馆藏与可借状态，可借的排前面。失败抛 RuntimeError。"""
    payload = client.request(cfg, "/find/physical/groupItemsByLibCode",
                             payload={"recordId": book_id})
    holdings: list[Holding] = []
    for h in parser.parse_holdings(payload, cfg.name_cn):
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


def get_book_detail(cfg: LibStarConfig, book_id: str) -> BookDetail:
    """指定书目的完整介绍（ISBN、索书号、内容简介）。失败抛 RuntimeError。

    详情必须 GET（同参数 POST 回 9999，实抓验证）。
    """
    payload = client.request(cfg, "/find/searchResultDetail/getBookDetail",
                             params={"recordId": book_id})
    d = parser.parse_detail(payload, cfg.name_cn)
    if not d["title"]:
        raise RuntimeError(f"{cfg.name_cn}：未找到该书详情：{book_id}")
    return {
        "book_id": book_id,
        "title": d["title"],
        "author": d["author"],
        "publisher": d["publisher"],
        "publish_year": d["publish_year"],
        "isbn": d["isbn"],
        "call_number": d["call_number"],
        "summary": d["summary"],
    }
