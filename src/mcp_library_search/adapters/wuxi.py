"""无锡适配器：图星 LibStar Find（无锡市新吴区图书馆）。

站点 `http://wxxqlsp.xw.i-wnd.cn:8013`。当前单源——无锡市新吴区图书馆
（libCode 80050700001）；无锡市图书馆（主馆）源码 `WXST` 已按天津口径预留，
接入后在同一城市标识下按 ISBN 归并，既有 book_id 契约不变。

技术组件是图星 LibStar Find v3.2023.12（北京图星/超星集团），与图创 Interlib
是两家厂商，不共用代码。字段侦察结论（字段码表、状态词表、数据边界）见
tests/fixtures/wuxi/NOTES.md。

**两个必需请求头是本城接入的关键**：

- `Referer`：任意值即可，只校验存在。缺失时**所有内容类端点**返回
  `errCode:9999`「系统访问中断」——措辞指向服务端宕机，实为反爬兜底。
  2026-10-02 初判「站点不通」即栽在这里；
- `groupcode: 800507`：新吴区租户号（≠ libCode 80050700001）。缺失不报错，
  HTTP 200 但 `numFound` 恒 0。

两者由 `_request()` 统一注入，三个原语全部经由它取数，调用点无从遗漏。
"""
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from types import SimpleNamespace

from .base import BookDetail, BookSummary, Holding, SearchPage

_NAME = "无锡市新吴区图书馆"
_BASE = "http://wxxqlsp.xw.i-wnd.cn:8013"
_GROUPCODE = "800507"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
_TIMEOUT = 20

_THROTTLE = 1.0  # 秒/host 保守间隔（站点未观测到限频，留余量；单测 monkeypatch 关闭）
_last_request = 0.0

# 数据源表：新增源只需在此加一条（天津口径）。WXST（无锡市图书馆）为预留槽位，
# 尚未接入——补上配置即可启用，book_id 形态与归并逻辑都已就位。
_SOURCES = {
    "WXXW": {"name_cn": _NAME},
    # "WXST": {"name_cn": "无锡市图书馆"},   # 预留：主馆，接入后按 ISBN 归并
}
# 归并优先级：主馆在前（复合 book_id 成员顺序与主记录取值同源）
_SOURCE_PRIORITY = ("WXST", "WXXW")

# 检索请求体模板（约 30 个固定字段）：只有 searchFieldContent / page / rows 随调用变化。
# 逐次 dict(...) 复制，免得关键词串到下一次请求。
_SEARCH_BODY = {
    "docCode": [None], "searchFieldContent": "", "searchField": "keyWord", "matchMode": "2",
    "resourceType": [], "subject": [], "discode1": [], "publisher": [], "libCode": [],
    "locationId": [], "eCollectionIds": [], "neweCollectionIds": [], "curLocationId": [],
    "campusId": [], "kindNo": [], "collectionName": [], "author": [], "langCode": [],
    "countryCode": [], "publishBegin": None, "publishEnd": None, "coreInclude": [],
    "ddType": [], "verifyStatus": [], "group": [], "sortField": "relevance",
    "sortClause": "asc", "page": 1, "rows": 10, "onlyOnShelf": None, "searchItems": None,
    "newCoreInclude": [], "customSub": [], "customSub0": [], "indexSearch": 1,
}


@dataclass
class _Book:
    """跨源归并用的轻量书目；`isbn` 是内部字段，不进 BookSummary 契约。"""

    record_id: str
    title: str = ""
    author: str = ""
    publisher: str = ""
    publish_year: str = ""
    availability_summary: str = ""
    isbn: str = ""


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


def _throttle():
    """最小间隔限速：距上次请求不足 _THROTTLE 秒时睡足差值（单 host）。"""
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _clean(text):
    """字段值 → 原值字符串（None→空串），只去首尾空白，不改内容。"""
    if text is None:
        return ""
    return str(text).strip()


# ---------- HTTP 出口 ----------


def _request(path, payload=None, params=None):
    """统一 HTTP 出口：注入 Referer 与 groupcode 两个必需头，返回解析后的 JSON 信封。"""
    url = _BASE + path
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    headers = {
        "Referer": _BASE + "/",          # 缺失 → 全站内容端点回 errCode 9999（反爬兜底）
        "groupcode": _GROUPCODE,         # 缺失 → HTTP 200 但静默 0 结果
        "User-Agent": _UA,
        "Accept": "application/json, text/plain, */*",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json;charset=UTF-8"
    req = urllib.request.Request(url, data=data, headers=headers)
    _throttle()
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        # 网络层失败（TLS 重置/超时/DNS）带上馆名上抛，不裸抛 URLError
        raise RuntimeError(
            f"{_NAME}：请求失败（{path}）：{getattr(e, 'reason', e)}") from e
    try:
        return json.loads(body)
    except ValueError as e:
        raise RuntimeError(f"{_NAME}：响应不是 JSON（可能被拦截或接口变更）：{body[:120]}") from e


def _check(payload, what):
    """图星统一信封校验：success 为假即上抛，errCode 9999 补一句头缺失提示。"""
    if isinstance(payload, dict) and payload.get("success"):
        return payload.get("data") or {}
    code = payload.get("errCode") if isinstance(payload, dict) else None
    msg = payload.get("message") if isinstance(payload, dict) else str(payload)[:120]
    hint = "；errCode 9999 通常意味着请求漏带 Referer 头（本站反爬闸）" if code == 9999 else ""
    raise RuntimeError(f"{_NAME}：{what}失败 errCode={code}：{msg}{hint}")


# ---- ISBN 归并与复合 book_id（口径照天津/合肥） ----


def _looks_like_isbn(keyword):
    """ISBN 形态判断：去连字符后 13 位（978/979 开头）或 10 位（末位可为 X）。"""
    s = str(keyword or "").replace("-", "").strip()
    if len(s) == 13 and s.isdigit():
        return s[:3] in ("978", "979")
    if len(s) == 10 and s[:9].isdigit():
        return s[9].isdigit() or s[9] in "Xx"
    return False


def _norm_isbn(isbn):
    """ISBN 归一：去连字符与空白并转大写；非 ISBN 形态返回空串（不参与归并）。"""
    s = re.sub(r"[\s-]", "", str(isbn or "")).upper()
    return s if _looks_like_isbn(s) else ""


def _merge_books(per_source):
    """跨源按归一 ISBN 归并：{source: [ _Book ]} → 归并后的 _Book 列表。

    口径同天津：同 ISBN 每源至多一个成员（源内重复保留首条）；多源命中合成复合
    record_id（`+` 连接，按优先级排序），书目字段取优先级最高成员的原值；无 ISBN
    （含脏值）不参与归并、各自成条，按源优先级排在分组条目之后。当前只有单源，
    此函数是预留结构——市图接入后无需改动归并逻辑。
    """
    order = []    # ISBN 首次出现顺序
    groups = {}   # 归一 ISBN -> {source: _Book}
    singles = []
    for source in _SOURCE_PRIORITY:
        for b in per_source.get(source, []):
            key = _norm_isbn(b.isbn)
            if not key:
                singles.append(b)
                continue
            members = groups.setdefault(key, {})
            if source in members:
                continue
            if not members:
                order.append(key)
            members[source] = b
    merged = []
    for key in order:
        ordered = [groups[key][s] for s in _SOURCE_PRIORITY if s in groups[key]]
        if len(ordered) == 1:
            merged.append(ordered[0])
        else:
            merged.append(replace(ordered[0],
                                  record_id="+".join(m.record_id for m in ordered)))
    merged.extend(singles)
    return merged


def _split_book_id(book_id):
    """复合/单成员 book_id → 按优先级排序的 [(source, record_id)]；形态非法即抛错。"""
    members = []
    for part in str(book_id or "").split("+"):
        source, sep, rid = part.strip().partition(":")
        if not sep or not rid or source not in _SOURCE_PRIORITY:
            raise RuntimeError(f"{_NAME}：未知 book_id 形态：{book_id}")
        members.append((source, rid))
    return sorted(members, key=lambda m: _SOURCE_PRIORITY.index(m[0]))


def _source(source):
    """取已接入源的配置；预留槽位（如 WXST）给出明确报错而非静默空结果。"""
    cfg = _SOURCES.get(source)
    if cfg is None:
        raise RuntimeError(f"{_NAME}：数据源 {source} 尚未接入（预留槽位）")
    return cfg


# ---------- 解析 ----------

_RE_ISBN_TAIL = re.compile(r"[\s/]")
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def _year(text):
    """出版日期原值 → 四位年份（实抓可为「2016.6」）；取不到返回空串。

    同青岛/重庆/宁波口径：只提形态，不做换算猜测。
    """
    m = _YEAR_RE.search(str(text or ""))
    return m.group(0) if m else ""


def _isbn_from(values):
    """cnb04「ISBN及定价」→ ISBN。

    同码可重复，且首条可能只有定价没有 ISBN（实抓 764039：先 `'/271.00 (8册)'`
    后 `'978-7-229-10062-9/271.00 (8册)'`）——取首个切出的非空 token，照单取首条
    会把 ISBN 解析成空串。
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


def _parse_search(payload):
    """检索响应 → {"books": [...], "total_results": int}。

    `numFound` 是真实总数（扁平数字）。`publisher` 源站可为 null → 空串。
    `isbn` 是内部字段（供跨源归并），不进 BookSummary 契约。
    """
    data = _check(payload, "检索")
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


def _fields(payload):
    """bean2List → {字段码: [值, ...]}（同码可多条，如 cnb20/cnb67）。"""
    out = {}
    for item in (_check(payload, "详情").get("bean2List") or []):
        if not isinstance(item, dict):
            continue
        key = _clean(item.get("key"))
        if key:
            out.setdefault(key, []).append(_clean(item.get("fieldVal")))
    return out


def _parse_detail(payload):
    """详情 → 归一字段。

    - `cnb01` 题名/责任者：按第一个 `/` 切题名与责任者（MARC 200 段惯例）；
    - `cnb03` 出版发行项：「出版地:出版社,年份」或「出版地,年份」，后者无出版社；
    - `cnb04` ISBN及定价：取首个 token（其后是装帧/定价，空格或 `/` 分隔）；
      同码可重复且可能首条无 ISBN，见 `_isbn_from`；
    - `cnb67` 中图法分类号：可多条，取首条作 call_number（同青岛家族口径，
      完整索书号在馆藏明细的 call_number 里）；
    - `cnb96` 提要文摘附注：内容简介。
    """
    f = _fields(payload)
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


_RE_DUE = re.compile(r"应还日期[:：]\s*(\d{4}-\d{2}-\d{2})")


def _status_of(process_type):
    """processType → (status 原值, available, due_date)。

    实测词表只有两态：`在架`（可借）与 `借出-应还日期:YYYY-MM-DD`（不可借且自带
    应还日期）。未观测到的值一律保守判不可借、原值照登（同重庆口径）。
    """
    status = _clean(process_type)
    if status == "在架":
        return status, True, ""
    due = _RE_DUE.search(status)
    return status, False, due.group(1) if due else ""


def _parse_holdings(payload):
    """馆藏响应 → 单册列表。

    `data.sortedList` 按馆名分组（新吴区全站单馆，实际只有一组）；馆名取分组键
    （回退到 libName），馆内位置取 `locationName`，索书号取 `callNo`。
    """
    data = _check(payload, "馆藏")
    holdings = []
    for lib_key, group in (data.get("sortedList") or {}).items():
        if not isinstance(group, dict):
            continue
        name = _clean(group.get("libName")) or _clean(lib_key)
        for item in group.get("phyItemVo") or []:
            if not isinstance(item, dict):
                continue
            status, available, due = _status_of(item.get("processType"))
            holdings.append({
                "library": name,
                "location": _clean(item.get("locationName")),
                "call_number": _clean(item.get("callNo")),
                "status": status,
                "available": available,
                "item_id": _clean(item.get("itemId")),
                "due_date": due,
            })
    return holdings


# ---------- 契约缝（与成都/台州/青岛同款） ----------


class _Client:
    """按源表分派：当前单源；源级容错口径同天津——≥1 源成功即返回存活源结果。"""

    def _search_source(self, source, keyword, page, limit):
        payload = dict(_SEARCH_BODY, searchFieldContent=str(keyword or ""),
                       page=page, rows=limit)
        r = _parse_search(_request("/find/unify/search", payload=payload))
        total, books = r["total_results"], r["books"]
        return {
            "books": [
                _Book(record_id=f"{source}:{b['book_id']}", title=b["title"],
                      author=b["author"], publisher=b["publisher"],
                      publish_year=b["publish_year"],
                      availability_summary=b["availability_summary"], isbn=b["isbn"])
                for b in books
            ],
            "total_results": total,
            "total_pages": math.ceil(total / limit) if total > 0 and limit > 0 else 0,
        }

    def search(self, keyword, page=1, limit=20):
        per_source, errors = {}, []
        for source, cfg in _SOURCES.items():
            try:
                per_source[source] = self._search_source(source, keyword, page, limit)
            except RuntimeError as e:
                errors.append(f"{cfg['name_cn']}：{e}")
        if not per_source:
            raise RuntimeError(f"{_NAME}：检索失败——" + "；".join(errors))
        books = _merge_books({s: r["books"] for s, r in per_source.items()})
        totals = [r["total_results"] for r in per_source.values()]
        # 合计口径同天津：任一存活源不提供总数 → 合计不可知，如实 None
        total = None if any(t is None for t in totals) else sum(totals)
        total_pages = max(r["total_pages"] for r in per_source.values())
        return SimpleNamespace(
            success=True,
            error="",
            statistics={"total_results": total, "page": page,
                        "total_pages": total_pages, "has_next": page < total_pages},
            books=books,
        )

    def _holdings_for(self, source, rid):
        _source(source)  # 预留源在此报错
        return [_Holding(**h) for h in
                _parse_holdings(_request("/find/physical/groupItemsByLibCode",
                                         payload={"recordId": rid}))]

    def get_holdings(self, book_id):
        """复合 book_id 拆成员逐个查询后聚合；容错口径同天津（首成员失败报错）。"""
        holdings = []
        for i, (source, rid) in enumerate(_split_book_id(book_id)):
            try:
                holdings.extend(self._holdings_for(source, rid))
            except RuntimeError:
                if i == 0:
                    raise
        holdings.sort(key=lambda h: (not h.available, h.library))
        return holdings

    def get_book_detail(self, book_id):
        """复合 id 取优先级最高成员的详情；record_id 保留查询原样（天津口径）。"""
        source, rid = _split_book_id(book_id)[0]
        _source(source)
        # 详情必须 GET（同参数 POST 回 9999，实抓验证）
        d = _parse_detail(_request("/find/searchResultDetail/getBookDetail",
                                   params={"recordId": rid}))
        return SimpleNamespace(record_id=book_id, **d)

    def get_return_date(self, item_id):
        """应还日期已内嵌在馆藏 `processType` 里，无按单册查的接口。

        定义仅为对齐契约形状（同天津）；模块级 get_holdings 的补查分支真网不触发。
        """
        raise RuntimeError(f"{_NAME}：无单册归还日期接口：{item_id}")


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索无锡市新吴区图书馆馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"{_NAME}搜索失败：{result.error}")

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
    """指定图书的馆藏与可借状态，可借的排前面。

    全站单馆（新吴区），馆藏地下沉到街道分馆与社区服务点，馆名原值照登。
    借出单册自带应还日期（藏在状态串里），访客视角即可拿到。
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
        # 契约测试要求已借出且带单册 item_id 时查归还时间。本城应还日期已内嵌在
        # 馆藏 processType 里解析出来，故仅在日期缺失时才补查——真网永不走到
        # （青岛/天津是同款分支但 item_id 恒空；本城 item_id 非空，必须显式判空）
        if not available and getattr(h, "item_id", "") and not item["due_date"]:
            item["due_date"] = _client.get_return_date(h.item_id)
        items.append(item)
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(book_id: str) -> BookDetail:
    """指定图书的完整详情：书名、作者、出版社、出版年、ISBN、索书号、内容简介。

    `call_number` 取详情「中图法分类号」（cnb67，同青岛家族口径）；完整索书号在
    馆藏明细的 `call_number` 里。老书目出版项无出版社段时（`北京,2017`）
    `publisher` 为空串，属数据边界。
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
