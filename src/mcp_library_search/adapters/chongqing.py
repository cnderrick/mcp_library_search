"""重庆适配器：重庆图书馆 InDigLib「集群数字图书馆」→ base.py 统一模型。

会话流：GET frontV2/SearchIndex!simple.action 建立 JSESSIONID，再 POST
OpacMarcSearchSolr!simpleSearch.action（首页表单 action 是假入口，search.js
会改写）。翻页走结果页分页链接形态：GET 带 pageNo 等整串参数。
单册可借状态源站不公开（需读者登录，见 tests/fixtures/chongqing/NOTES.md），
holdings 只到「哪些分馆有」这一级。
"""
import http.cookiejar
import html
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from .base import BookDetail, BookSummary, Holding, SearchPage

_BASE = "http://222.177.237.197:8080"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA}
_THROTTLE = 3.0  # 秒；源站未见验证码，按 spec 保守限速

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_last_request = 0.0


def _open(req, timeout=20):
    """HTTP 入口：CookieJar 会话 + 3 秒节流，返回 UTF-8 文本。失败抛含馆名的 RuntimeError。"""
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"重庆图书馆请求失败：{e}") from e


def _has_session():
    return any(c.name == "JSESSIONID" for c in _jar)


def _reset_session():
    _jar.clear()
    global _last_request
    _last_request = 0.0


def _ensure_session():
    if not _has_session():
        url = f"{_BASE}/InDigLib/frontV2/SearchIndex!simple.action?opacType=local"
        _open(urllib.request.Request(url, headers=_HEADERS))


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


def _clean_publisher(text):
    """出版信息形如「重庆:重庆出版社 ,2022」，拆出纯出版社名。同深圳口径。"""
    s = re.sub(r",?\s*(?:19|20)\d{2}\S*$", "", str(text or "")).strip()
    if re.search(r"[:：]", s):
        s = re.split(r"[:：]", s, maxsplit=1)[1].strip()
    return s


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


# 结果页条目：题名著者出版社同址；链接带 showAsset=true 的是 <b> 内题名链接
_ENTRY = re.compile(
    r'BookDetail\.action\?metaid=(\d+)&(?:amp;)?metatable=([a-z_]+)&(?:amp;)?showAsset=true"'
    r"[^>]*>(.*?)</a>.*?<p>\s*<span>(.*?)</span>\s*<span>(.*?)</span>\s*<span>(.*?)</span>",
    re.S,
)
_TOTAL_PAGE = re.compile(r'id="totalPage"\s+value="(\d+)"')
_RESULT_TITLE = "opac检索结果页"


def _is_result_page(text):
    return _RESULT_TITLE in text


def _parse_search(text):
    """检索结果页 → {"books": [...], "total_pages": int}。total_results 源站不提供，为 None。"""
    books = [
        _Book(
            record_id=f"{table}:{metaid}",
            title=_clean(title),
            author=_clean(author),
            publisher=_clean_publisher(_clean(pub)),
            publish_year=_year(_clean(pub)),
            call_number=_clean(callno),
        )
        for metaid, table, title, author, pub, callno in _ENTRY.findall(text)
    ]
    m = _TOTAL_PAGE.search(text)
    return {"books": books, "total_pages": int(m.group(1)) if m else 1}


class _Client:
    """InDigLib 会话 client：把原始响应解析成与 vendor 对象同形的结构。"""

    def _fetch_search(self, select1, keyword, page, limit):
        if page <= 1:
            data = urllib.parse.urlencode({
                "select1": select1, "text1": keyword, "pageSize": str(limit),
            }).encode()
            req = urllib.request.Request(
                f"{_BASE}/InDigLib/OpacMarcSearchSolr!simpleSearch.action",
                data=data, headers=_HEADERS)
        else:
            # 结果页分页链接形态（fixture 实抓）：GET 带整串参数
            params = {
                "pageNo": str(page), "select1": select1, "select2": "", "select3": "",
                "text1": keyword, "text2": "", "text3": "",
                "occur1": "", "occur2": "", "occur3": "",
                "second": "", "table_CN": "",
                "lastSearchValue": f"{select1}FIELD_SPLITVALUE_SPLIT{keyword}",
                "startPublishTime": "", "endPublishTime": "",
                "pageSize": str(limit), "condition": "", "table": "", "type": "",
                "videoType": "", "listType": "list", "queryOrder": "1",
                "hasAsset": "false", "showAsset": "true",
                "format": "", "dataType": "", "sublib": "",
            }
            url = (f"{_BASE}/InDigLib/OpacMarcSearchSolr!simpleSearch.action?"
                   + urllib.parse.urlencode(params))
            req = urllib.request.Request(url, headers=_HEADERS)
        return _open(req)

    def search(self, keyword, page=1, limit=20):
        select1 = "isbn" if _looks_like_isbn(keyword) else "all"
        _ensure_session()
        text = self._fetch_search(select1, keyword, page, limit)
        if not _is_result_page(text):
            # 会话失效：响应退回检索首页 → 重建会话重试一次
            _reset_session()
            _ensure_session()
            text = self._fetch_search(select1, keyword, page, limit)
            if not _is_result_page(text):
                raise RuntimeError("重庆图书馆：检索未返回结果页（重复失败，可能会话无法建立）")
        r = _parse_search(text)
        total_pages = r["total_pages"]
        return _SearchResult(
            success=True,
            error="",
            statistics={
                "total_results": None,
                "page": page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
            },
            books=r["books"],
        )


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"重庆图书馆搜索失败：{result.error}")

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
