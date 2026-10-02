"""图星 LibStar Find 家族解析层：检索页/详情/馆藏 JSON。

响应信封统一 `{success, message, errCode, data}`。`success` 为假即上抛；
`errCode 9999` 补一句「漏带 Referer 头」提示（本站反爬闸）。

字段码表、状态词表与数据边界见各城 `tests/fixtures/<city>/NOTES.md`。
"""
from __future__ import annotations

import re

_RE_ISBN_TAIL = re.compile(r"[\s/]")
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")
_RE_DUE = re.compile(r"应还日期[:：]\s*(\d{4}-\d{2}-\d{2})")


def _clean(text):
    """字段值 → 原值字符串（None→空串），只去首尾空白，不改内容。"""
    if text is None:
        return ""
    return str(text).strip()


def check(payload, what, name=""):
    """图星统一信封校验：success 为假即上抛，errCode 9999 补一条头缺失提示。"""
    if isinstance(payload, dict) and payload.get("success"):
        return payload.get("data") or {}
    code = payload.get("errCode") if isinstance(payload, dict) else None
    msg = payload.get("message") if isinstance(payload, dict) else str(payload)[:120]
    hint = "；errCode 9999 通常意味着请求漏带 Referer 头（本站反爬闸）" if code == 9999 else ""
    prefix = f"{name}：" if name else ""
    raise RuntimeError(f"{prefix}{what}失败 errCode={code}：{msg}{hint}")


def _year(text):
    """出版日期原值 → 四位年份（实抓可为「2016.6」）；取不到返回空串。"""
    m = _YEAR_RE.search(str(text or ""))
    return m.group(0) if m else ""


def _isbn_from(values):
    """cnb04「ISBN及定价」→ ISBN。

    同码可重复，且首条可能只有定价没有 ISBN（实抓 764039：先 `'/271.00 (8册)'`
    后 `'978-7-229-10062-9/271.00 (8册)'`）——取首个切出的非空 token。
    """
    for raw in values:
        head = _RE_ISBN_TAIL.split(raw, 1)[0].strip()
        if head:
            return head
    return ""


def _availability(record):
    """可借概况：站点 UI 即用这两个数显示「纸本(N) / 可借(M)」。

    任一项缺失（老书目）则留空串，不拿单项编造。
    """
    total, on_shelf = record.get("physicalCount"), record.get("onShelfCountI")
    if total is None or on_shelf is None:
        return ""
    return f"纸本{int(total)}，可借{int(on_shelf)}"


def parse_search(payload, name=""):
    """检索响应 → {"books": [...], "total_results": int}。

    `numFound` 是真实总数（扁平数字）。`publisher` 源站可为 null → 空串。
    `isbn` 是内部字段（供跨源归并），不进 BookSummary 契约。
    """
    data = check(payload, "检索", name)
    try:
        total = int(data.get("numFound") or 0)
    except (TypeError, ValueError):
        total = 0
    books = []
    for rec in data.get("searchResult") or []:
        if not isinstance(rec, dict):
            continue
        book_id = _clean(rec.get("recordId"))
        if not book_id:
            continue
        books.append({
            "book_id": book_id,
            "title": _clean(rec.get("title")),
            "author": _clean(rec.get("author")),
            "publisher": _clean(rec.get("publisher")),
            "publish_year": _year(rec.get("publishYear")),
            "availability_summary": _availability(rec),
            "isbn": _clean(rec.get("isbn")),
        })
    return {"books": books, "total_results": total}


def _fields(payload, name=""):
    """bean2List → {字段码: [值, ...]}（同码可多条，如 cnb20/cnb67）。"""
    out = {}
    for item in (check(payload, "详情", name).get("bean2List") or []):
        if not isinstance(item, dict):
            continue
        key = _clean(item.get("key"))
        if key:
            out.setdefault(key, []).append(_clean(item.get("fieldVal")))
    return out


def parse_detail(payload, name=""):
    """详情 → 归一字段。

    - `cnb01` 题名/责任者：按第一个 `/` 切题名与责任者（MARC 200 段惯例）；
    - `cnb03` 出版发行项：「出版地:出版社,年份」或「出版地,年份」，后者无出版社；
    - `cnb04` ISBN及定价：取首个 token（其后是装帧/定价，空格或 `/` 分隔）；
      同码可重复且可能首条无 ISBN，见 `_isbn_from`；
    - `cnb67` 中图法分类号：可多条，取首条作 call_number（同青岛家族口径，
      完整索书号在馆藏明细的 call_number 里）；
    - `cnb96` 提要文摘附注：内容简介。
    """
    f = _fields(payload, name)
    title_author = (f.get("cnb01") or [""])[0]
    title, _, author = title_author.partition("/")
    pub = (f.get("cnb03") or [""])[0]
    head, _, year = pub.rpartition(",")
    publisher = head.partition(":")[2] if head else ""
    return {
        "title": title.strip(),
        "author": author.strip(),
        "publisher": publisher.strip(),
        "publish_year": _year(year) if head else "",
        "isbn": _isbn_from(f.get("cnb04") or []),
        "call_number": (f.get("cnb67") or [""])[0],
        "summary": (f.get("cnb96") or [""])[0],
    }


def _status_of(process_type):
    """processType → (status 原值, available, due_date)。

    观测词表：`在架`（可借）与 `借出-应还日期:YYYY-MM-DD`（不可借且自带应还
    日期）。未观测到的值一律保守判不可借、原值照登（同重庆口径）。
    """
    status = _clean(process_type)
    if status == "在架":
        return status, True, ""
    due = _RE_DUE.search(status)
    return status, False, due.group(1) if due else ""


def parse_holdings(payload, name=""):
    """馆藏响应 → 单册列表。

    `data.sortedList` 按馆名分组；馆名取分组键（回退到 libName），馆内位置取
    `locationName`，索书号取 `callNo`。同一书目可命中多个分馆分组，空分组
    （如主馆无单册）自然贡献 0 条。
    """
    data = check(payload, "馆藏", name)
    holdings = []
    for lib_key, group in (data.get("sortedList") or {}).items():
        if not isinstance(group, dict):
            continue
        group_name = _clean(group.get("libName")) or _clean(lib_key)
        for item in group.get("phyItemVo") or []:
            if not isinstance(item, dict):
                continue
            status, available, due = _status_of(item.get("processType"))
            holdings.append({
                "library": group_name,
                "location": _clean(item.get("locationName")),
                "call_number": _clean(item.get("callNo")),
                "status": status,
                "available": available,
                "item_id": _clean(item.get("itemId")),
                "due_date": due,
            })
    return holdings
