"""金华适配器：金华市图书馆 UILAS 知识检索平台（ILAS 家族 HTML OPAC）→ base.py 统一模型。

裸 IP 纯 HTTP 入口（443 证书已过期，别走 https），全链路匿名可通、无需 cookie
会话。检索 POST NTRdrBookRetr.do：ISBN 形态关键词路由 searchType=isbnsrh，其余
一律 text（任意词）；翻页 GET 带 nCurrentpage，SearchKey 按页内翻页链接原样
**双重 URL 编码**。详情 GET NTRdrBookRetrInfo.do?recno=（book_id＝裸 recno，
纯数字），馆藏内联在详情页 div#BookHolding（CADAL 数字图书的两个 table.table
在锚点之前，切片天然排除）。状态词表仅「入藏（可借）/借出」，词表外保守不可借；
借出单册**无应还日期列** → due_date 恒空（数据边界，不猜）；简介＝详情页内联
「附注提要」原值，无则为空串（站方 getBookCatalog.do 未启用，不接）。字段侦察
结论见 tests/fixtures/jinhua/NOTES.md。
"""
import html
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from ..base import BookDetail, BookSummary, Holding, SearchPage

_BASE = "http://202.101.180.43/ILASOPAC"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA}
_THROTTLE = 4.0  # 秒/host；天津 ILAS 家族经验的安全线（NOTES.md）

_opener = urllib.request.build_opener()
_last_request = 0.0


def _open(req, timeout=30):
    """HTTP 入口：4 秒节流，返回 UTF-8 文本。失败抛含馆名的 RuntimeError。

    匿名可通无需 CookieJar；详情页可达 600KB+，超时放宽到 30 秒。
    """
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"金华市图书馆请求失败：{e}") from e


def _looks_like_isbn(keyword):
    """ISBN 形态判断：去连字符后 13 位（978/979 开头）或 10 位（末位可为 X）。同重庆/深圳口径。"""
    s = str(keyword or "").replace("-", "").strip()
    if len(s) == 13 and s.isdigit():
        return s[:3] in ("978", "979")
    if len(s) == 10 and s[:9].isdigit():
        return s[9].isdigit() or s[9] in "Xx"
    return False


def _clean(text):
    """去标签、解转义、压缩空白，返回纯文本原值。

    JSP 模板在单元格里留大量换行/制表符/条件分支残片（NOTES.md），
    必须压缩空白后再取文本。
    """
    s = re.sub(r"<[^>]+>", "", html.unescape(str(text or "")))
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def _year(text):
    """从出版日期原值提取公历年；民国纪年等提不到则空串（不做换算猜测）。同重庆口径。"""
    m = re.search(r"(?:19|20)\d{2}", str(text or ""))
    return m.group(0) if m else ""


@dataclass
class _Book:
    record_id: str = ""
    title: str = ""
    author: str = ""
    publisher: str = ""
    publish_year: str = ""
    availability_summary: str = ""
    isbn: str = ""
    call_number: str = ""
    summary: str = ""


@dataclass
class _SearchResult:
    success: bool = True
    error: str = ""
    statistics: dict = field(default_factory=dict)
    books: list = field(default_factory=list)


@dataclass
class _Holding:
    library: str = ""
    location: str = ""
    call_number: str = ""
    status: str = ""
    available: bool = False
    item_id: str = ""  # 条码号不当 item_id 用（同重庆口径），避免触发契约的归还日期分支
    due_date: str = ""

    def is_available(self):
        return self.available


# ---------- 检索结果页解析 ----------

_TOTAL = re.compile(r"共有\s*\[(\d*)\]条记录")       # 空结果页括号为空 → 0
_PAGENO = re.compile(r"页码:\s*(\d+)/(\d*)")          # 空结果页「页码: 1/」无总页数 → 1
_ENTRY_SPLIT = '<h3 class="title">'                   # 条目分块锚点（页面 JS 里也有 checkbox 字样，不能数裸字符串）
_RECNO = re.compile(r'name="bookItemCheckbox"\s+value="(\d+)"')
_RECNO_LINK = re.compile(r"recno=(\d+)")
_TITLE_A = re.compile(r"<a[^>]*>(.*?)</a>", re.S)
_DETAIL_MARKER = "书目详细信息"                        # 详情页 <title> 标记（检索页无）


def _is_result_page(text):
    """总数锚点在＝结果页（空结果页也有「共有 []条记录」）；缺失＝被打回别的页。"""
    return bool(_TOTAL.search(text))


def _entry_field(label, chunk):
    m = re.search(label + r"：<span[^>]*>(.*?)</span>", chunk, re.S)
    return _clean(m.group(1)) if m else ""


def _parse_search(text):
    """检索结果页 → {"books", "total_results", "total_pages"}。列表页无状态词。"""
    books = []
    for chunk in text.split(_ENTRY_SPLIT)[1:]:
        m = _RECNO.search(chunk) or _RECNO_LINK.search(chunk)
        if not m:
            continue
        t = _TITLE_A.search(chunk)
        books.append(_Book(
            record_id=m.group(1),
            title=_clean(t.group(1)) if t else "",
            author=_entry_field("作者", chunk),
            publisher=_entry_field("出版社", chunk),
            publish_year=_year(_entry_field("出版时间", chunk)),
        ))
    tm = _TOTAL.search(text)
    total = int(tm.group(1)) if tm and tm.group(1) else 0
    pm = _PAGENO.search(text)
    total_pages = int(pm.group(2)) if pm and pm.group(2) else 1
    return {"books": books, "total_results": total, "total_pages": total_pages}


# ---------- 详情页解析 ----------

def _li_field(label, text):
    m = re.search(r"<li>" + label + r"：(.*?)</li>", text, re.S)
    return _clean(m.group(1)) if m else ""


_DETAIL_TITLE = re.compile(r'<h3 class="title">\s*<a[^>]*>(.*?)</a>', re.S)
_SUMMARY = re.compile(r'<strong>附注提要</strong>.*?<div class="text"[^>]*>(.*?)</div>', re.S)


def _parse_detail(text):
    """详情页 → 书目字段 dict。标题取 h3.title 第一个 <a>（形态「标题</a>/<a>作者」）。"""
    tm = _DETAIL_TITLE.search(text)
    sm = _SUMMARY.search(text)
    return {
        "title": _clean(tm.group(1)) if tm else "",
        "author": _li_field("作者", text),
        "publisher": _li_field("出版社", text),
        "publish_year": _year(_li_field("出版日期", text)),
        "isbn": _li_field("ISBN/ISSN", text),   # 查无 ISBN 时原值「书号不详」照登
        "call_number": _li_field("分类号", text),
        "summary": _clean(sm.group(1)) if sm else "",  # 内联附注提要；无则空串
    }


# ---------- 馆藏解析（详情页内联） ----------

_HOLDING_ANCHOR = 'id="BookHolding"'
_TABLE = re.compile(r'<table[^>]*class="table"[^>]*>(.*?)</table>', re.S)
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TH = re.compile(r"<th[^>]*>(.*?)</th>", re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)

# 状态词表仅这两词（用户定调口径）：「入藏」可借，「借出」不可借，词表外保守不可借
_AVAILABLE_STATUS = {"入藏"}


def _cell(cells, idx, label):
    n = idx.get(label)
    return cells[n] if n is not None and n < len(cells) else ""


def _parse_holdings(text):
    """详情页 div#BookHolding → 单册级 _Holding 列表。

    锚点切片天然排除其前的 CADAL 数字图书表；只有入藏复本时单表（「馆藏信息」），
    有借出复本时两表（＋「已外借馆藏」），全部遍历合并。列位按 th 标签映射
    （第 7 列两表文案不一：预借/预约，且属动作列不入数据）。借出无应还日期列，
    due_date 恒空。
    """
    i = text.find(_HOLDING_ANCHOR)
    if i < 0:
        return []
    holdings = []
    for tbl in _TABLE.findall(text[i:]):
        labels = [_clean(x) for x in _TH.findall(tbl)]
        idx = {lab: n for n, lab in enumerate(labels)}
        for row in _TR.findall(tbl):
            cells = [_clean(c) for c in _TD.findall(row)]
            if not cells:
                continue  # thead 行（只有 th）或空行
            h = _Holding(
                library=_cell(cells, idx, "当前所在馆"),
                location=_cell(cells, idx, "当前所在地点"),
                call_number=_cell(cells, idx, "索书号"),
                status=_cell(cells, idx, "馆藏状态"),
            )
            if not (h.library or h.call_number or h.status):
                continue  # 模板空行防御（实抓未见）
            h.available = h.status in _AVAILABLE_STATUS
            holdings.append(h)
    return holdings


def _check_recno(book_id):
    """book_id 必须是裸 recno（纯数字，NOTES.md）；带前缀/异形直接报错。"""
    s = str(book_id or "").strip()
    if not re.fullmatch(r"\d+", s):
        raise RuntimeError(f"金华市图书馆：book_id 应为纯数字 recno：{book_id}")
    return s


class _Client:
    """UILAS HTML client：把原始响应解析成与 vendor 对象同形的结构。"""

    def _fetch_search(self, search_type, keyword, page, limit):
        if page <= 1:
            data = urllib.parse.urlencode({
                "searchType": search_type,
                "searchKey": keyword,
                "searchWay": "searchWayPrv",
                "pageNum": str(limit),
                "matchType": "pubyear",
                "matchSort": "desc",
            }).encode()
            req = urllib.request.Request(
                f"{_BASE}/NTRdrBookRetr.do", data=data, headers=_HEADERS)
        else:
            # 页内翻页链接原样（NOTES.md）：GET 带 nCurrentpage，SearchKey 双重
            # URL 编码——先 quote 一层，urlencode 再编码一层
            params = urllib.parse.urlencode({
                "nCurrentpage": str(page),
                "SearchType": search_type,
                "SearchKey": urllib.parse.quote(keyword, safe=""),
                "PageNum": str(limit),
                "searchWay": "searchWayPrv",
                "matchType": "pubyear",
                "matchSort": "desc",
            })
            req = urllib.request.Request(
                f"{_BASE}/NTRdrBookRetr.do?{params}", headers=_HEADERS)
        return _open(req)

    def search(self, keyword, page=1, limit=20):
        search_type = "isbnsrh" if _looks_like_isbn(keyword) else "text"
        text = self._fetch_search(search_type, keyword, page, limit)
        if not _is_result_page(text):
            # 匿名可通无会话可重建；总数锚点缺失＝响应不是结果页，如实报错
            raise RuntimeError("金华市图书馆：检索未返回结果页（响应缺总数锚点，可能被源站拦截或改版）")
        r = _parse_search(text)
        total_pages = r["total_pages"]
        return _SearchResult(
            success=True,
            error="",
            statistics={
                "total_results": r["total_results"],
                "page": page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
            },
            books=r["books"],
        )

    def _fetch_detail(self, recno):
        url = f"{_BASE}/NTRdrBookRetrInfo.do?recno={recno}&libid="
        text = _open(urllib.request.Request(url, headers=_HEADERS))
        if _DETAIL_MARKER not in text:
            raise RuntimeError(f"金华市图书馆：详情页获取失败（响应无「{_DETAIL_MARKER}」标记）：{recno}")
        return text

    def get_holdings(self, book_id):
        recno = _check_recno(book_id)
        return _parse_holdings(self._fetch_detail(recno))

    def get_book_detail(self, book_id):
        recno = _check_recno(book_id)
        d = _parse_detail(self._fetch_detail(recno))
        if not d["title"]:
            raise RuntimeError(f"金华市图书馆：未找到该书详情：{book_id}")
        return _Book(record_id=recno, **d)


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"金华市图书馆搜索失败：{result.error}")

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
        # 契约测试要求已借出且带单册 item_id 时查归还时间；金华单册无 item_id（条码号不当
        # item_id 用），真网路径不会触发
        if not available and getattr(h, "item_id", ""):
            item["due_date"] = _client.get_return_date(h.item_id)
        items.append(item)
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(book_id: str) -> BookDetail:
    """指定图书的完整详情：书名、作者、出版社、出版年、ISBN、索书号、内容简介。

    内容简介取详情页内联「附注提要」原值；站方简介接口未启用，无附注则空串。
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
