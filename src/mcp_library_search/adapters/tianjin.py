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
from dataclasses import dataclass, field
from http.cookiejar import CookieJar

from ..interlib import InterlibConfig
from .base import BookDetail, BookSummary, Holding, SearchPage

_SOURCES = {
    "TJL01": {"host": "http://opacwh.tjl.tj.cn:8991", "name": "天津图书馆"},
    "TJC01": {"host": "http://opacse.tjl.tj.cn:8991", "name": "天津市少年儿童图书馆"},
}
_ZXYH = InterlibConfig(city="zxyh", name_cn="中新友好图书馆",
                       base_url="http://sm.interlib.cn:8104", curlibcode="STC001")
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA}
_THROTTLE = 4.0   # ALEPH 验证码墙按 IP 封，限速是硬约束（NOTES.md）
_PAGE_SIZE = 10   # ALEPH brief 每页固定 10 条，short-jump 按记录偏移

_jar = CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_last_request = 0.0


def _open(req, timeout=20):
    """HTTP 入口：CookieJar 会话（set_number 绑定会话）+ 节流，返回 UTF-8 文本。"""
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"天津图书馆请求失败：{e}") from e


def _check_captcha(text):
    """验证码墙：立即抛错，不重试硬闯（按 IP 封，硬闯只会延长封禁）。"""
    if "验证码" in text:
        raise RuntimeError("天津图书馆：检索过于频繁触发验证码，请稍后再试")


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
    """三源客户端：本任务先实现 ALEPH 两源检索；ZXYH 与归并在后续任务接入。"""

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

    def search(self, keyword, page=1, limit=20):
        per_source = {}
        for source in _SOURCES:
            per_source[source] = _parse_find(self._fetch_find(source, keyword, page), source)
        books = [b for source in _SOURCES for b in per_source[source]["books"]]
        total = sum(r["total_results"] for r in per_source.values())
        total_pages = max(r["total_pages"] for r in per_source.values())
        return _SearchResult(
            success=True,
            error="",
            statistics={
                "total_results": total,
                "page": page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
            },
            books=books,
        )


_client = _Client()
