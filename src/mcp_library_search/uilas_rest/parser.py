"""新版 UILAS REST 家族解析层：检索/详情/馆藏 JSON。

字段侦察结论见 tests/fixtures/shaanxi/NOTES.md 与 tests/fixtures/yulin/NOTES.md。

- 检索：`data.pageList.list[]`（书目条目）＋ `data.pageList.totalElements`；
- 详情：`data.bookDetail`（完整书目）＋ `data.inList[]`（馆藏单册）＋
  `data.libraryList[]`（馆名表）；
- 馆藏状态码：`a=采编 / b=在馆 / c=借出 / d=租出 / e=预约`（前端 i18n
  `bookinfo_hold_status_*`），只有 `b` 可借，其余与未知码一律保守判不可借。
"""
from __future__ import annotations

import re

_YEAR_RE = re.compile(r"(?:19|20)\d{2}")

# 状态码 → 中文原值（前端 i18n bookinfo_hold_status_*）
STATUS_NAMES = {
    "a": "采编",
    "b": "在馆",
    "c": "借出",
    "d": "租出",
    "e": "预约",
}
# 只有「在馆」可借；其余与未知码保守不可借
AVAILABLE_CODES = {"b"}


def _clean(v):
    return "" if v is None else str(v).strip()


def _year(v):
    m = _YEAR_RE.search(_clean(v))
    return m.group(0) if m else ""


def _record(rec: dict) -> dict:
    """检索/详情共用的书目条目 → 归一字段。"""
    return {
        "book_id": _clean(rec.get("id")),
        "title": _clean(rec.get("name")),
        "author": _clean(rec.get("author")),
        "publisher": _clean(rec.get("publish")),
        "publish_year": _year(rec.get("pubyear")),
        "isbn": _clean(rec.get("isbn")),
        "call_number": _clean(rec.get("classno")),
        "summary": _clean(rec.get("contents")),
    }


def parse_search(payload: dict) -> dict:
    """检索响应 → {"books": [...], "total_results": int}。

    `data.pageList.list[]` 条目字段与详情 `data.bookDetail` 同形。
    """
    data = (payload or {}).get("data") or {}
    pl = data.get("pageList") or {}
    try:
        total = int(pl.get("totalElements") or 0)
    except (TypeError, ValueError):
        total = 0
    books = []
    for rec in pl.get("list") or []:
        if not isinstance(rec, dict):
            continue
        b = _record(rec)
        if not b["book_id"]:
            continue
        # 可借概况：inHoldingCount 在馆 / holdingCount 总册
        total_h = rec.get("holdingCount")
        avail_h = rec.get("inHoldingCount")
        b["availability_summary"] = (
            f"纸本{int(total_h)}，可借{int(avail_h)}"
            if total_h is not None and avail_h is not None else "")
        books.append(b)
    return {"books": books, "total_results": total}


def parse_detail(payload: dict) -> dict:
    """详情响应 → {"book": {...}, "holdings": [...]}。

    书目取 `data.bookDetail`；馆藏取 `data.inList[]`，馆名/位置用 `curlib`/
    `curlocal` 原值（服务端已给中文），状态码经 `STATUS_NAMES` 翻译。
    """
    data = (payload or {}).get("data") or {}
    book = _record(data.get("bookDetail") or {})
    holdings = []
    for it in data.get("inList") or []:
        if not isinstance(it, dict):
            continue
        code = _clean(it.get("status"))
        holdings.append({
            "library": _clean(it.get("curlib")),
            "location": _clean(it.get("curlocal")),
            "call_number": _clean(it.get("callno")),
            "status": STATUS_NAMES.get(code, code),
            "available": code in AVAILABLE_CODES,
            "due_date": _clean(it.get("retudate")) if _clean(it.get("retudate")) not in ("", "0") else "",
        })
    return {"book": book, "holdings": holdings}
