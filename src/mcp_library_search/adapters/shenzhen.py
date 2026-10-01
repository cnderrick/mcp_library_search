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

from .base import BookDetail, BookSummary, Holding, SearchPage

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


def _year(text):
    """从文本里提取 4 位出版年份，找不到返回空串。"""
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


class _Client:
    """轻量 JSON API 客户端：把原始响应解析成与 vendor 对象同形的结构。"""

    def search(self, keyword, page=1, limit=20):
        body = _get("/api/opacservice/getQueryResult", {
            "v_value": keyword,
            "v_index": "title",
            "pageNum": str(limit),
            "v_page": str(page),
        })
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
