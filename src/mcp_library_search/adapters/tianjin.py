"""天津适配器：主馆 TJL01 + 少儿馆 TJC01（ALEPH）+ 中新友好（Interlib）三源合并。

book_id 形态：TJL01:{doc_number} / TJC01:{doc_number} / ZXYH:{bookrecno}；
同一 ISBN 多源命中合成复合 id（成员以 + 连接，主馆在前）。
ALEPH 结构细节（ISB 索引、short-jump 记录偏移翻页、ISB 单命中直接给完整记录页、
publish section 注释块字段）全部见 tests/fixtures/tianjin/NOTES.md。
"""
import html
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace
from http.cookiejar import CookieJar

from ..interlib import InterlibConfig
from ..interlib import get_book_detail as il_detail
from ..interlib import get_holdings as il_holdings
from ..interlib import search_raw as il_search
from .base import BookDetail, BookSummary, Holding, SearchPage

_SOURCES = {
    "TJL01": {"host": "http://opacwh.tjl.tj.cn:8991", "name": "天津图书馆"},
    "TJC01": {"host": "http://opacse.tjl.tj.cn:8991", "name": "天津市少年儿童图书馆"},
}
# 归并优先级：主馆 > 少儿馆 > 中新友好（复合 book_id 成员顺序与主记录取值同源）
_SOURCE_PRIORITY = ("TJL01", "TJC01", "ZXYH")
_ZXYH = InterlibConfig(city="zxyh", name_cn="中新友好图书馆",
                       base_url="http://sm.interlib.cn:8104", curlibcode="STC001")
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA}
_THROTTLE = 4.0   # ALEPH 验证码墙按 IP 封，限速是硬约束（NOTES.md）
_PAGE_SIZE = 10   # ALEPH brief 每页固定 10 条，short-jump 按记录偏移

_jar = CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))


class _Throttle:
    """最小间隔限速器：距上次 wait() 不足 interval 时睡足差值。

    clock/sleep 可注入供单测；真网默认 time.monotonic/time.sleep。
    """

    def __init__(self, interval, clock=time.monotonic, sleep=time.sleep):
        self.interval = interval
        self._clock = clock
        self._sleep = sleep
        self._last = None

    def wait(self):
        now = self._clock()
        if self._last is not None:
            deficit = self.interval - (now - self._last)
            if deficit > 0:
                self._sleep(deficit)
                now = self._clock()
        self._last = now


# 每 host 一个限速器：主馆与少儿馆是两台服务器，各自计时互不拖累
_throttles = {}


def _throttle_for(url):
    host = urllib.parse.urlsplit(url).netloc
    if host not in _throttles:
        _throttles[host] = _Throttle(_THROTTLE)
    return _throttles[host]


def _open(req, timeout=20):
    """HTTP 入口：CookieJar 会话（set_number 绑定会话）+ 每 host 节流，返回 UTF-8 文本。"""
    _throttle_for(req.full_url).wait()
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"天津图书馆请求失败：{e}") from e


class _CaptchaError(RuntimeError):
    """验证码墙：按 IP 的全局限速信号，必须穿透源级容错直达调用方，不静默降级。"""


def _check_captcha(text):
    """验证码墙：立即抛错，不重试硬闯（按 IP 封，硬闯只会延长封禁）。"""
    if "验证码" in text:
        raise _CaptchaError("天津图书馆：检索过于频繁触发验证码，请稍后再试")


def _looks_like_isbn(keyword):
    """ISBN 形态判断：去连字符后 13 位（978/979 开头）或 10 位（末位可为 X）。同深圳口径。"""
    s = str(keyword or "").replace("-", "").strip()
    if len(s) == 13 and s.isdigit():
        return s[:3] in ("978", "979")
    if len(s) == 10 and s[:9].isdigit():
        return s[9].isdigit() or s[9] in "Xx"
    return False


def _clean(text):
    """去标签、&nbsp; 与首尾空白，返回纯文本原值。"""
    s = re.sub(r"<[^>]+>", "", html.unescape(str(text or "")))
    return s.replace("\xa0", " ").strip()


def _year(text):
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
    available: bool = True
    item_id: str = ""
    due_date: str = ""

    def is_available(self):
        return self.available


# ---- ISBN 归并与复合 book_id（口径见 tests/fixtures/tianjin/NOTES.md） ----

def _norm_isbn(isbn):
    """ISBN 归一：去连字符与空白并转大写；非 ISBN 形态返回空串（不参与归并）。"""
    s = re.sub(r"[\s-]", "", str(isbn or "")).upper()
    return s if _looks_like_isbn(s) else ""


def _merge_books(per_source):
    """跨源按归一 ISBN 归并：{source: [ _Book ]} → 归并后的 _Book 列表。

    口径：
    - 同一 ISBN 每源至多一个成员（源内同 ISBN 多条——多卷/重印——保留首条，
      其余条目让位于首条的馆藏，spec 已接受该取舍）；
    - 多源命中合成复合 record_id（成员以 + 连接，按优先级排序），
      书目字段取优先级最高成员的原值；
    - 无 ISBN（含脏值）不参与归并，各自成条；
    - 顺序：ISBN 分组按首次出现顺序，未分组条目按源顺序排在最后。
    """
    order = []    # ISBN 首次出现顺序
    groups = {}   # 归一 ISBN -> {source: _Book}
    singles = []  # 无 ISBN 条目
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
            raise RuntimeError(f"天津图书馆：未知 book_id 形态：{book_id}")
        members.append((source, rid))
    return sorted(members, key=lambda m: _SOURCE_PRIORITY.index(m[0]))


# ---- ALEPH 解析（结构证据：tests/fixtures/tianjin/NOTES.md） ----

_COUNT = re.compile(r"记录\s*(\d+)\s*-\s*(\d+)\s*of\s*([\d,]+)")
_JUMP = re.compile(r'(http://[^"\'\s>]*func=short-jump&jump=)\d+')
# brief 条目：publish section 注释块字段
_BRIEF_DOC = re.compile(r"DOC-NUMBER \(3300\)\s*=\s*(\d+)")
_BRIEF_ISBN = re.compile(r"Z13-ISBN-ISSN \(3100\)\s*=\s*([^\n<]+)")
_TITLE = re.compile(r'<div class=itemtitle><a [^>]*>(.*?)</a>', re.S)


def _brief_field(label, chunk):
    """brief 字段表：`{label}：<td class=content...>值` 到下一个 <td 为止。"""
    m = re.search(label + r"<td class=content[^>]*>(.*?)(?=<td|<tr|</table)", chunk, re.S)
    return _clean(m.group(1)) if m else ""


# 完整记录页（ISB 单命中 / full-set-set 详情共用）：publish section 注释块
_FULL_DOC = re.compile(r"DOC-NUMBER:\s*(\d+)")
_FULL_FIELDS = {
    "isbn": re.compile(r"ISBN:\s*([^\n]+)"),
    "title": re.compile(r"TITLE:\s*([^\n]+)"),
    "author": re.compile(r"AUTHOR:\s*([^\n]+)"),
    "imprint": re.compile(r"IMPRINT:\s*([^\n]+)"),
    "callno": re.compile(r"CALL-NO:\s*([^\n]+)"),
}


def _full_field(name, text):
    m = _FULL_FIELDS[name].search(text)
    return _clean(m.group(1)) if m else ""


def _parse_full_record(text, source):
    """ISB 单命中的完整记录页 → 单条 _Book（无命中返回 None）。"""
    m = _FULL_DOC.search(text)
    if not m:
        return None
    imprint = _full_field("imprint", text)
    return _Book(
        record_id=f"{source}:{m.group(1)}",
        title=_full_field("title", text),
        author=_full_field("author", text),
        publisher=imprint,
        publish_year=_year(imprint),
        isbn=_full_field("isbn", text),
        call_number=_full_field("callno", text),
    )


# ---- 单册页 item-global（列结构见 NOTES.md） ----

_ITEM_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
# 可借性原值在「应还日期」列（在架上/日期）；「单册状态」列是流通类型（阅览/中文图书借阅…）
_AVAIL_WORDS = ("在架", "在馆", "可借")


def _item_cell(row, marker):
    m = re.search(r"<!--" + marker + r"-->\s*<td[^>]*>(.*?)</td>", row, re.S)
    return _clean(m.group(1)) if m else ""


def _norm_due(text):
    """应还日期归一为 YYYY-MM-DD：支持 YYYYMMDD、YYYY-MM-DD、DD/MM/YYYY；非日期返回空串。"""
    s = str(text or "").strip()
    if re.fullmatch(r"\d{8}", s):
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return ""


def _parse_item_global(text):
    """item-global 单册页 → _Holding 列表。

    可借判定只看应还日期列：含「在架/在馆/可借」→ 可借；是日期 → 已借出（due_date 归一）；
    其余（含空）保守不可借。流通类型列不参与判定，但与状态原值一并保留在 status 里。
    """
    _check_captcha(text)
    holdings = []
    for row in _ITEM_ROW.findall(text):
        if "<!--Loan status-->" not in row:
            continue
        loan = _item_cell(row, "Loan status")
        due = _item_cell(row, "Due date")
        date = _norm_due(due)
        if date:
            status, due_date, available = loan, date, False
        else:
            status = " ".join(x for x in (loan, due) if x)
            due_date = ""
            available = any(w in due for w in _AVAIL_WORDS)
        holdings.append(_Holding(
            library=_item_cell(row, "Sub-library"),
            location=_item_cell(row, "Collection"),
            call_number=_item_cell(row, "Location"),
            status=status,
            available=available,
            due_date=due_date,
        ))
    return holdings


def _parse_find(text, source):
    """find-b 响应 → {"books", "total_results", "total_pages"}。

    两种形态：brief 列表（多条）与 ISB 单命中直接给的完整记录页（1 条）。
    brief 页的 publish section 注释块多于真实条目（13 vs 10），以 itemtitle 锚定并按
    DOC-NUMBER 去重。
    """
    _check_captcha(text)
    if "class=itemtitle" not in text:
        b = _parse_full_record(text, source)
        return {"books": [b] if b else [], "total_results": 1 if b else 0, "total_pages": 1}

    books = []
    seen = set()
    for chunk in text.split("<!-- publish section")[1:]:
        if "class=itemtitle" not in chunk:
            continue
        dm = _BRIEF_DOC.search(chunk)
        if not dm or dm.group(1) in seen:
            continue
        seen.add(dm.group(1))
        tm = _TITLE.search(chunk)
        im = _BRIEF_ISBN.search(chunk)
        pub = _brief_field("出版社：", chunk)
        books.append(_Book(
            record_id=f"{source}:{dm.group(1)}",
            title=_clean(tm.group(1)) if tm else "",
            author=_brief_field("作者：", chunk),
            publisher=pub,
            publish_year=_brief_field("年份：", chunk) or _year(pub),
            isbn=_clean(im.group(1)) if im else "",
            call_number=_brief_field("索书号：", chunk),
        ))
    cm = _COUNT.search(text)
    total = int(cm.group(3).replace(",", "")) if cm else len(books)
    return {"books": books, "total_results": total,
            "total_pages": max(1, math.ceil(total / _PAGE_SIZE))}


class _Client:
    """三源客户端：ALEPH 两源 + 中新友好（interlib 租户，复用家族原语）。"""

    def _fetch_find(self, source, keyword, page):
        cfg = _SOURCES[source]
        find_code = "ISB" if _looks_like_isbn(keyword) else "WRD"
        url = (f"{cfg['host']}/F?func=find-b&request={urllib.parse.quote(keyword)}"
               f"&find_code={find_code}&local_base={source}")
        text = _open(urllib.request.Request(url, headers=_HEADERS))
        _check_captcha(text)
        if page > 1:
            # 同会话 short-jump：jump=(page-1)*10+1，必须用页内会话 URL（F/VV... 前缀）
            m = _JUMP.search(text)
            if m:
                jump_url = m.group(1) + str((page - 1) * _PAGE_SIZE + 1)
                text = _open(urllib.request.Request(jump_url, headers=_HEADERS))
                _check_captcha(text)
        return text

    def _search_zxyh(self, keyword, page, limit):
        """中新友好源：家族 search_raw（带 isbn 内部字段）；失败上抛，容错在 search。"""
        zr = il_search(_ZXYH, keyword, page=page, limit=limit)
        return {
            "books": [
                _Book(record_id=f"ZXYH:{b['book_id']}", title=b["title"], author=b["author"],
                      publisher=b["publisher"], publish_year=b["publish_year"],
                      availability_summary=b["availability_summary"], isbn=b.get("isbn", ""))
                for b in zr["books"]
            ],
            "total_results": zr["total_results"],
            "total_pages": zr["total_pages"],
        }

    def search(self, keyword, page=1, limit=20):
        # 源级容错：≥1 源成功即返回存活源结果（数据原样）；三源全失败才报错
        per_source = {}
        errors = []
        for source in _SOURCES:
            try:
                per_source[source] = _parse_find(
                    self._fetch_find(source, keyword, page), source)
            except _CaptchaError:
                raise  # 验证码墙是全局限速信号，快速失败给可操作提示
            except RuntimeError as e:
                errors.append(f"{_SOURCES[source]['name']}：{e}")
        try:
            per_source["ZXYH"] = self._search_zxyh(keyword, page, limit)
        except RuntimeError as e:
            errors.append(f"{_ZXYH.name_cn}：{e}")
        if not per_source:
            raise RuntimeError("天津图书馆：三源检索均失败——" + "；".join(errors))
        books = _merge_books({s: r["books"] for s, r in per_source.items()})
        # 合计口径：任一存活源不提供总数（ZXYH 检索页无「检索到 N 条」）→ 合计不可知，
        # 如实 None，不拿部分源的数编造全城总数
        totals = [r["total_results"] for r in per_source.values()]
        total = None if any(t is None for t in totals) else sum(totals)
        return _SearchResult(
            success=True,
            error="",
            statistics={
                "total_results": total,
                "page": page,
                "total_pages": max(r["total_pages"] for r in per_source.values()),
                "has_next": any(page < r["total_pages"] for r in per_source.values()),
            },
            books=books,
        )

    def get_holdings(self, book_id):
        """复合 book_id 拆成员逐个查询后聚合（可借在前、馆名升序）；单成员同一路径。

        容错口径：首成员（目标源）失败报错；附属源失败跳过，返回已查到部分。
        """
        holdings = []
        for i, (source, rid) in enumerate(_split_book_id(book_id)):
            try:
                holdings.extend(self._holdings_for(source, rid))
            except RuntimeError:
                if i == 0:
                    raise
        holdings.sort(key=lambda h: (not h.available, h.library))
        return holdings

    def _holdings_for(self, source, rid):
        """单成员馆藏：ZXYH 走家族原语，ALEPH 走 item-global 单册页。"""
        if source == "ZXYH":
            return [
                _Holding(library=h["library"], location=h["location"],
                         call_number=h["call_number"], status=h["status"],
                         available=h["available"], due_date=h.get("due_date", ""))
                for h in il_holdings(_ZXYH, rid, only_available=False)
            ]
        url = (f"{_SOURCES[source]['host']}/F?func=item-global"
               f"&doc_library={source}&doc_number={rid}")
        try:
            text = _open(urllib.request.Request(url, headers=_HEADERS))
            return _parse_item_global(text)
        except RuntimeError as e:
            raise RuntimeError(f"{_SOURCES[source]['name']}馆藏查询失败：{e}") from e

    def get_book_detail(self, book_id):
        """复合 id 取优先级最高成员的详情；record_id 保留查询原样。目标源失败如实报错。"""
        source, rid = _split_book_id(book_id)[0]
        if source == "ZXYH":
            d = il_detail(_ZXYH, rid)
            return _Book(record_id=book_id, title=d["title"], author=d["author"],
                         publisher=d["publisher"], publish_year=d["publish_year"],
                         isbn=d["isbn"], call_number=d["call_number"],
                         summary=d["summary"])
        url = (f"{_SOURCES[source]['host']}/F?func=full-set-set"
               f"&doc_library={source}&doc_number={rid}&format=999")
        try:
            text = _open(urllib.request.Request(url, headers=_HEADERS))
        except RuntimeError as e:
            raise RuntimeError(f"{_SOURCES[source]['name']}详情查询失败：{e}") from e
        _check_captcha(text)
        b = _parse_full_record(text, source)
        if b is None:
            raise RuntimeError(f"{_SOURCES[source]['name']}：未找到该书详情：{book_id}")
        return replace(b, record_id=book_id)

    def get_return_date(self, item_id):
        """天津无按单册查归还日期的接口：ALEPH 应还日期在单册页直取、ZXYH 在馆藏 JSON。

        天津馆藏不带 item_id，模块级 get_holdings 的补查分支真网永不触发；
        定义仅为对齐契约形状。
        """
        raise RuntimeError(f"天津图书馆：无单册归还日期接口：{item_id}")


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索三源合并馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"天津图书馆搜索失败：{result.error}")

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
        # 契约测试要求已借出且带单册 item_id 时查归还时间；天津馆藏无 item_id，真网不触发
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
