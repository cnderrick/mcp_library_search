"""SirsiDynix iLink 家族共享模块。

成员：甘肃省图书馆（`gansu_prov`）、陇南市图书馆（`longnan`）、甘南州图书馆
（`gannan`）。三站是**同一套 iLink 实例**（`search.gslib.com.cn`），检索/详情/馆藏
页与大连同构，差别只在检索表单的 `library` 馆别过滤值——故上收为共享家族，三城各以
`IlinkConfig`（含 `library_code`）薄包装。大连 `adapters/cn/dalian.py` 接口同构但仍是
独立实现，见 cn.md 3.8，本家族不重构大连。

三原语：
- 检索 `POST searchform action`（GET 入口页取 fresh ps token），字段 `searchdata1` /
  `srchfield1` / `library`（馆别）/ `sort_by`；翻页 `hitlist` POST `form_type=JUMP^{n}`。
- 详情/馆藏：题名（TI）候选梯度重检索定位 catkey → `VIEW^N` 取「馆藏显示」页。
- `book_id` 形如 `"{catkey}:{题名}"`；馆藏到索书号级，`due_date`/`item_id` 恒空串。

HTTP 层见 `client.py`，解析见 `parser.py`。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import client, parser

if TYPE_CHECKING:
    from ..adapters.base import BookDetail, Holding, SearchPage


@dataclass(frozen=True)
class IlinkConfig:
    """iLink 站点配置。quirk 字段必须带默认值。"""

    city: str                                   # 城市标识，如 "gansu_prov"
    name_cn: str                                # 报错与文档用的中文名
    base_url: str                               # 站点根地址，不含末尾斜杠
    entry_path: str = "/uhtbin/cgisirsi/x/x/0/49/"  # 会话入口（返回「快速检索」首页）
    library_code: str = "ALL"                   # 馆别过滤：searchform 的 library 字段
    general_field: str = "GENERAL^SUBJECT^GENERAL^^所有字段"  # 通用检索字段（无 ISBN 专用）
    title_field: str = "TI^TITLE^SERIES^^题名"  # 详情重定位用的题名字段
    sort_by: str = "ANY"                        # 排序；入口页 hidden sort_by 优先
    page_size: int = 20                         # 源站固定每页 20 条，limit 不生效
    throttle: float = 4.0                       # 秒/host，会话敏感从严
    detail_max_pages: int = 5                   # 详情定位翻页上限（每页 20 条）


def search_books(cfg: IlinkConfig, keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词检索；短语优先、0 命中或源站拒答退回裸词。上游报错抛 RuntimeError。"""
    r = client.search(cfg, keyword, page=page, limit=limit)
    if not r.success:
        raise RuntimeError(f"{cfg.name_cn}搜索失败：{r.error}")
    stats = r.statistics or {}
    return {
        "total_results": stats.get("total_results"),
        "page": stats.get("page", page),
        "total_pages": stats.get("total_pages", 1),
        "has_next": stats.get("has_next", False),
        "books": [
            {
                "book_id": b.record_id,
                "title": b.title,
                "author": b.author,
                "publisher": b.publisher,
                "publish_year": b.publish_year,
                "availability_summary": b.availability_summary,
            }
            for b in (r.books or [])
        ],
    }


def get_holdings(cfg: IlinkConfig, book_id: str,
                 only_available: bool = True) -> list[Holding]:
    """指定图书的索书号级馆藏。匿名视图无单册条码与应还日期（due_date 恒空串）。

    可借口径保守：copy_info 含「在架上」判可借，仅「馆藏于」等判不可借。
    """
    holdings = client.get_holdings(cfg, book_id) or []
    items: list[Holding] = []
    for h in holdings:
        if only_available and not h.is_available():
            continue
        items.append({
            "library": h.library,
            "location": h.location,
            "call_number": h.call_number,
            "status": h.status,
            "available": h.is_available(),
            "due_date": h.due_date or "",
        })
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(cfg: IlinkConfig, book_id: str) -> BookDetail:
    """指定图书的完整详情；失败抛 RuntimeError。"""
    b = client.get_book_detail(cfg, book_id)
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
