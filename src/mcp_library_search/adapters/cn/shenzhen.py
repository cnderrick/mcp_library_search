"""深圳适配器：深圳图书馆自研 JSON API → base.py 统一模型。

深圳与 Interlib 无关，完全独立：本模块自带轻量 client（urllib + json），
不打 HTML。三个能力对应 getQueryResult（搜索，真实总数 numFound）、
getBookDetail（详情 + 三桶馆藏 + 借出 ReturnDate）。book_id 用
"{tablename}:{recordid}"，详情接口需要成对 metaTable/metaId。
"""
import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from ..base import BookDetail, BookSummary, Holding, SearchPage

_BASE = "https://www.szlib.org.cn"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA, "Referer": "https://www.szlib.org.cn/opac/"}


def _get(path, params):
    """GET 请求深圳 JSON API，返回解析后的 dict；失败抛含馆名的 RuntimeError。"""
    params = {**params, "client_id": "t1"}
    url = _BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            json.JSONDecodeError, UnicodeDecodeError) as e:
        raise RuntimeError(f"深圳图书馆请求失败：{e}") from e


def _looks_like_isbn(keyword):
    """ISBN 形态判断：去连字符后 13 位（978/979 开头）或 10 位（末位可为 X）。"""
    s = str(keyword or "").replace("-", "").strip()
    if len(s) == 13 and s.isdigit():
        return s[:3] in ("978", "979")
    if len(s) == 10 and s[:9].isdigit():
        return s[9].isdigit() or s[9] in "Xx"
    return False


def _year(text):
    """从文本里提取 4 位出版年份，找不到返回空串。"""
    m = re.search(r"(?:19|20)\d{2}", str(text or ""))
    return m.group(0) if m else ""


def _split_book_id(book_id):
    """book_id 形如 "{tablename}:{recordid}"，拆成成对的 metaTable/metaId。"""
    table, _, rid = str(book_id).partition(":")
    if not table or not rid:
        raise RuntimeError(f"深圳图书馆：book_id 格式应为 tablename:recordid：{book_id}")
    return table, rid


def _normalize_date(text):
    """ReturnDate 为 YYYYMMDD（如 20151222），归一化为 YYYY-MM-DD。"""
    s = str(text or "").strip()
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return s


def _groups(bucket):
    """三桶容器形态不一：list[group] / 单个 group dict / null，统一成 group 列表。"""
    if isinstance(bucket, list):
        return [g for g in bucket if isinstance(g, dict)]
    if isinstance(bucket, dict):
        return [bucket]
    return []


def _records(group):
    """一个 group 里的单册列表。"""
    rl = group.get("recordList") or []
    if isinstance(rl, list):
        return [r for r in rl if isinstance(r, dict)]
    if isinstance(rl, dict):
        return [rl]
    return []


def _library_name(item, group):
    """馆名：借出单册在 libraryNotes，其余在 group 级 serviceaddrnotes，再退回单册 library 代码。"""
    return (item.get("libraryNotes") or group.get("serviceaddrnotes")
            or item.get("library") or "").strip()


def _clean_author(text):
    """detail 的 author 带责任方式后缀（如「冯唐著」），去掉末尾的著/编著/著译。"""
    return re.sub(r"(?:编著|著译|著)$", "", str(text or "").strip()).strip()


def _clean_publisher(text):
    """detail 的 publish/publishyear 是「城市:出版社,年份」全串，拆出纯出版社名。"""
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


class _Client:
    """轻量 JSON API 客户端：把原始响应解析成与 vendor 对象同形的结构。"""

    def search(self, keyword, page=1, limit=20):
        if _looks_like_isbn(keyword):
            # ISBN 必须走 isbn 索引；且该索引要求完整参数集，缺参会被静默忽略回退全库
            params = {
                "v_value": keyword,
                "v_index": "isbn",
                "library": "all",
                "v_tablearray": "bibliosm,serbibm,apabibibm,mmbibm,",
                "sortfield": "ptitle",
                "sorttype": "desc",
                "pageNum": str(limit),
                "cirtype": "",
                "v_secondquery": "",
                "v_startpubyear": "",
                "v_endpubyear": "",
                "v_page": str(page),
            }
        else:
            # 任意词索引（官网下拉第一项）：书名/作者/关键词混合
            params = {
                "v_value": keyword,
                "v_index": "all",
                "pageNum": str(limit),
                "v_page": str(page),
            }
        body = _get("/api/opacservice/getQueryResult", params)
        data = body.get("data") or {}
        num_found = data.get("numFound") or 0
        total_pages = math.ceil(num_found / limit) if limit > 0 else 1
        books = [
            _Book(
                record_id=f"{doc.get('tablename', '')}:{doc.get('recordid', '')}",
                title=(doc.get("ptitle") or doc.get("title") or doc.get("u_title") or "").strip(),
                author=(doc.get("author") or "").strip(),
                publisher=(doc.get("publisher") or "").strip(),
                publish_year=_year(doc.get("publishyear") or doc.get("u_publish") or ""),
            )
            for doc in (data.get("docs") or [])
        ]
        return _SearchResult(
            success=True,
            error="",
            statistics={
                "total_results": num_found,
                "page": page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
            },
            books=books,
        )

    def get_holdings(self, book_id):
        table, rid = _split_book_id(book_id)
        body = _get("/api/opacservice/getBookDetail", {
            "metaTable": table, "metaId": rid, "library": "all",
        })
        data = body.get("data", body) if isinstance(body, dict) else {}
        holdings = []
        for bucket, available in (("CanLoanBook", True),
                                  ("OnlyReadBook", False),
                                  ("BorrowedBook", False)):
            for group in _groups(data.get(bucket)):
                for item in _records(group):
                    holdings.append(_Holding(
                        library=_library_name(item, group),
                        location=(item.get("local") or item.get("location") or "").strip(),
                        call_number=(item.get("callno") or "").strip(),
                        status=(item.get("status") or "").strip(),
                        available=available,
                        item_id="",
                        due_date=_normalize_date(item.get("ReturnDate") or "") if not available else "",
                    ))
        return holdings

    def get_book_detail(self, book_id):
        table, rid = _split_book_id(book_id)
        body = _get("/api/opacservice/getBookDetail", {
            "metaTable": table, "metaId": rid, "library": "all",
        })
        data = body.get("data", body) if isinstance(body, dict) else {}
        title = (data.get("title") or "").strip()
        if not title:
            raise RuntimeError(f"深圳图书馆：未找到该书详情：{book_id}")
        publish_raw = data.get("publish") or data.get("publishyear") or ""
        return _Book(
            record_id=book_id,
            title=title,
            author=_clean_author(data.get("author") or ""),
            publisher=_clean_publisher(publish_raw),
            publish_year=_year(publish_raw),
            isbn=(data.get("isbn") or "").strip(),
            call_number=(data.get("callno") or "").strip(),
            summary=(data.get("abstract") or data.get("abstracts") or "").strip(),
        )


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"深圳图书馆搜索失败：{result.error}")

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
        # 契约测试要求已借出且带单册 item_id 时查归还时间；深圳数据无 item_id，真网路径不会触发
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
