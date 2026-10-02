"""台州适配器:图创 Interlib 家族(pro2018 新版模板变体)。

台州市图书馆(https://opac.tzlib.cn:8182,全市通借网络)。与广州/杭州同属 Interlib,
HTTP 层(client.get)与馆藏层(get_holdings,馆藏 JSON 与广州完全同构)直接复用家族;
但搜索页(libBookLi 模板)与详情页(bkTxt 左右两列模板)是家族内另一套页面模板——
广州基准的 bookmeta 容器、bookInfoTable 两列锚点在默认页面上均不存在,现有
InterlibConfig 的 quirk 字段(仅 curlibcode)表达不了「整套页面模板不同」。
这两页的解析暂放本模块(_parse_search/_parse_detail,返回结构与 interlib.parser
的 parse_search/parse_detail 对齐,含 isbn 内部字段),家族化迁移建议见交付报告;
字段侦察依据 tests/fixtures/taizhou/NOTES.md。

薄包装 + 契约测试兼容缝同广州/杭州:公开原语全部经由模块级 _client 取数,
契约测试(tests/test_adapter_contract.py)monkeypatch 的就是这个 _client,
因此不能把三个原语写成对底层函数的直连委托——那样 mock 会落空、
测试会真打图书馆网站。
"""
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from types import SimpleNamespace

from .. import interlib
from ..interlib import InterlibConfig
from .base import BookDetail, BookSummary, Holding, SearchPage

_CONFIG = InterlibConfig(
    city="taizhou", name_cn="台州市图书馆", base_url="https://opac.tzlib.cn:8182"
)


def _clean(text):
    """折叠空白、去 &nbsp;(\xa0),去首尾空格(同家族 parser 口径)。"""
    return " ".join(text.replace("\xa0", " ").split())


# ---------- 搜索页解析(libBookLi 模板,pro2018 新版皮肤) ----------
# 总数在 schResNumIn 元素;分页是 JS 配置(totalPage/currentPage)而非渲染锚点,
# 「下一页」只存在于 JS 字符串,广州的锚点探测法在此恒 False,不可用。
_TOTAL_RE = re.compile(r'schResNumIn">\s*([\d,]+)\s*</i>')
_TOTAL_PAGES_RE = re.compile(r"totalPage:\s*(\d+)")
_CURRENT_PAGE_RE = re.compile(r"currentPage:\s*(\d+)")
# 空结果页不渲染总数区,但有明确提示锚点(源站明说没有相关书目 → 判 0,不是猜测)
_NO_RESULT_RE = re.compile(r"notFindFt")
_BOOK_DETAIL_RE = re.compile(r"bookDetail\((\d+)")
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")


class _SearchParser(HTMLParser):
    """台州搜索结果页:li.libBookLi 容器定边界,class/标签锚点定字段。

    - 标题:第一个 a.libBookDetNm(序号 span 同 class,须按 a 标签区分);
      书目 ID 取其 href 的 bookDetail(数字,封面 img 的 bookrecno 属性兜底。
    - 字段标签是 span.libBkDetTit 文本(责任者/出版信息/ISBN),标签后随首个 <a>:
      作者、出版社取 a 文本;出版年是出版社 a 之后、下一个 <p> 之前的裸文本;
      ISBN 取封面 img 的 isbn 属性(内部字段,不进 BookSummary 契约)。
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.books = []
        self._cur = None
        self._label = ""        # 条目内最近一个 libBkDetTit 标签文本
        self._label_parts = []
        self._in_label = False
        self._a_text = None     # 正在抓取的 a 标签文本
        self._a_role = None     # title/author/publisher/None
        self._tail = False      # 出版社 a 结束后抓出版年裸文本
        self._tail_done = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "li" and "libBookLi" in cls:
            self._finish_book()
            self._cur = {"book_id": "", "title": "", "author": "",
                         "publisher": "", "publish_year": "", "isbn": ""}
            self._label = ""
            return
        if self._cur is None:
            return
        if tag == "img":
            # 封面 img 属性兜底:isbn 与 bookrecno
            if not self._cur["isbn"]:
                self._cur["isbn"] = (a.get("isbn") or "").strip()
            if not self._cur["book_id"]:
                self._cur["book_id"] = (a.get("bookrecno") or "").strip()
        elif tag == "span" and "libBkDetTit" in cls:
            self._in_label = True
            self._label_parts = []
        elif tag == "a":
            self._a_text = []
            href = a.get("href") or ""
            if "libBookDetNm" in cls and not self._cur["title"]:
                self._a_role = "title"
                m = _BOOK_DETAIL_RE.search(href)
                if m and not self._cur["book_id"]:
                    self._cur["book_id"] = m.group(1)
            elif self._label == "责任者" and not self._cur["author"]:
                self._a_role = "author"
            elif self._label == "出版信息" and not self._cur["publisher"]:
                self._a_role = "publisher"
            else:
                self._a_role = None
        elif tag == "p":
            # 出版年只在出版社 a 之后、本 <p> 结束前的裸文本里找
            self._tail = False

    def handle_endtag(self, tag):
        if self._cur is None:
            return
        if tag == "span" and self._in_label:
            self._label = _clean("".join(self._label_parts))
            self._in_label = False
        elif tag == "a" and self._a_text is not None:
            text = _clean("".join(self._a_text))
            if self._a_role == "title":
                self._cur["title"] = text
            elif self._a_role == "author":
                self._cur["author"] = text
            elif self._a_role == "publisher":
                self._cur["publisher"] = text
                self._tail = True
                self._tail_done = False
            self._a_text = None
            self._a_role = None
        # 条目内嵌套 li(馆藏信息 tab 等)不影响边界:只认 libBookLi class 开新条

    def handle_data(self, data):
        if self._cur is None:
            return
        if self._in_label:
            self._label_parts.append(data)
        if self._a_text is not None:
            self._a_text.append(data)
        if self._tail and not self._tail_done:
            m = _YEAR_RE.search(data)
            if m:
                self._cur["publish_year"] = m.group(0)
                self._tail_done = True

    def _finish_book(self):
        if self._cur is not None:
            if self._cur["book_id"]:
                self._cur["availability_summary"] = ""
                self.books.append(self._cur)
            self._cur = None


def _parse_search(html: str) -> dict:
    """解析台州搜索页(libBookLi 模板),返回结构与家族 parse_search 对齐。

    返回 {"books": [{book_id,title,author,publisher,publish_year,
    availability_summary,isbn}...], "total_results": int|None,
    "total_pages": int, "has_next": bool}。total_results:总数区缺失且无
    空结果提示时为 None;total_pages 解析不到保守取 1;
    has_next = currentPage < totalPage(JS 分页配置,页面无可点分页锚点)。
    """
    p = _SearchParser()
    p.feed(html)
    p._finish_book()
    m = _TOTAL_RE.search(html)
    if m:
        total_results = int(m.group(1).replace(",", ""))
    elif _NO_RESULT_RE.search(html):
        total_results = 0
    else:
        total_results = None
    tp = _TOTAL_PAGES_RE.search(html)
    cp = _CURRENT_PAGE_RE.search(html)
    total_pages = int(tp.group(1)) if tp else 1
    current_page = int(cp.group(1)) if cp else 1
    return {
        "books": p.books,
        "total_results": total_results,
        "total_pages": total_pages,
        "has_next": current_page < total_pages,
    }


# ---------- 详情页解析(bkTxt 模板,左右两列 li 标签) ----------
# 标签词表与广州 bookInfoTable 一致(ISBN/出版发行/内容提要/中图分类法/主要责任者);
# 字段分布在 bkTxtLeft 与 bkTxtRight 两列(页内 JS 会动态搬移 li),两列都要跟踪。
# 标题取 a.bkTxtTit(完整标题含副题名;view=simple 的「题名」行只有正题名,不用)。
# 简介:服务端 HTML 无「内容提要」行(样例),由第三方 API 异步注入不可依赖,
# 若个别记录带该 li 则按同标签照抓,否则 summary 为空串。
_DETAIL_LABELS = {
    "ISBN": "isbn",
    "出版发行": "publish",
    "内容提要": "summary",
    "中图分类法": "call_number",
    "主要责任者": "author",
}
_ISBN_RE = re.compile(r"[\d\-]{10,}")


class _DetailParser(HTMLParser):
    """台州默认详情页:bkTxtLeft/bkTxtRight 两列,每字段一个 li(标签：<span>值)。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fields = {k: "" for k in
                       ("title", "author", "publisher", "publish_year",
                        "isbn", "call_number", "summary")}
        self._depth = 0            # 字段列容器深度,0 = 不在容器内
        self._label = None         # 当前 li 的标签(None = 不在 li 内)
        self._label_parts = []
        self._in_span = False
        self._span_parts = []
        self._link_parts = None    # 非 None 表示正在抓值内首个 <a> 文本
        self._first_link = ""
        self._title_parts = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "a" and "bkTxtTit" in cls and not self.fields["title"]:
            self._title_parts = []
            return
        if tag == "div" and ("bkTxtLeft" in cls or "bkTxtRight" in cls):
            self._depth = 1        # 两列是兄弟容器,进入新列重置深度
            return
        if not self._depth:
            return
        if tag == "div":
            self._depth += 1
        elif tag == "li" and self._label is None:
            self._label = ""
            self._label_parts = []
        elif tag == "span" and self._label is not None and not self._in_span:
            self._in_span = True
            self._span_parts = []
            self._first_link = ""
        elif tag == "a" and self._in_span and self._link_parts is None:
            self._link_parts = []

    def handle_endtag(self, tag):
        if tag == "a" and self._title_parts is not None:
            self.fields["title"] = _clean("".join(self._title_parts))
            self._title_parts = None
            return
        if tag == "a" and self._link_parts is not None:
            self._first_link = _clean("".join(self._link_parts))
            self._link_parts = None
            return
        if not self._depth:
            return
        if tag == "div":
            self._depth -= 1
        elif tag == "span" and self._in_span:
            self._in_span = False
            self._assign_value()
        elif tag == "li":
            self._label = None

    def handle_data(self, data):
        if self._title_parts is not None:
            self._title_parts.append(data)
        if not self._depth:
            return
        if self._in_span:
            self._span_parts.append(data)
            if self._link_parts is not None:
                self._link_parts.append(data)
        elif self._label is not None:
            # li 内、span 前的文本是标签(「ISBN：」形态,全/半角冒号均现)
            self._label_parts.append(data)
            joined = "".join(self._label_parts)
            m = re.split("([：:])", joined, maxsplit=1)
            if len(m) > 1:
                self._label = m[0].strip()

    def _assign_value(self):
        label = self._label or ""
        value = _clean("".join(self._span_parts))
        if label not in _DETAIL_LABELS or not value:
            return
        kind = _DETAIL_LABELS[label]
        if kind == "isbn":
            m = _ISBN_RE.search(value)
            self.fields["isbn"] = m.group(0) if m else ""
        elif kind == "publish":
            # 出版社取首个 a 文本(去尾部逗号);出版年在整格文本里找
            self.fields["publisher"] = self._first_link.rstrip("，,").strip()
            m = _YEAR_RE.search(value)
            self.fields["publish_year"] = m.group(0) if m else ""
        elif kind == "summary":
            self.fields["summary"] = value
        elif kind == "call_number":
            self.fields["call_number"] = value.split("版次")[0].strip()
        elif kind == "author":
            self.fields["author"] = self._first_link or (value.split()[0] if value else "")


def _parse_detail(html: str) -> dict:
    """解析台州默认详情页(bkTxt 模板),返回结构与家族 parse_detail 对齐,缺失字段为空串。"""
    p = _DetailParser()
    p.feed(html)
    return p.fields


# ---------- 契约缝(与广州/杭州同款) ----------


@dataclass
class _Holding:
    """与上海 vendor 客户端同形的馆藏对象(契约测试按此形态注入)。"""

    library: str = ""
    location: str = ""
    call_number: str = ""
    status: str = ""
    available: bool = True
    item_id: str = ""
    due_date: str = ""

    def is_available(self):
        return self.available


def _search_params(keyword: str, page: int, limit: int) -> dict:
    """检索参数与家族 _search_once 同款(台州站点实测该参数集原样可用)。"""
    return {
        "q": keyword,
        "searchType": "standard",
        "searchWay0": "marc",
        "logical0": "AND",
        "rows": limit,
        "sortWay": "score",
        "sortOrder": "desc",
        "page": page,
    }


class _Client:
    """把家族/本地解析返回值包装成契约测试期望的 attribute 对象形态。"""

    def _search_once(self, keyword, page, limit):
        html = interlib.client.get(_CONFIG, "/opac/search",
                                   _search_params(keyword, page, limit))
        return _parse_search(html)

    def search(self, keyword, page=1, limit=20):
        r = self._search_once(keyword, page, limit)
        # 镜像家族 search_raw 语义:带连字符 ISBN 在 marc 检索下可能命中不了,
        # 首搜为空时去连字符重试一次(台州未单独实测,防御性同族口径)
        if not r["books"] and "-" in keyword:
            retry = self._search_once(keyword.replace("-", ""), page, limit)
            if retry["books"]:
                r = retry
        return SimpleNamespace(
            success=True,
            error="",
            statistics={"total_results": r["total_results"], "page": page,
                        "total_pages": r["total_pages"], "has_next": r["has_next"]},
            # 家族 TypedDict 用 book_id,契约形态用 record_id,此处显式映射
            books=[SimpleNamespace(record_id=b["book_id"], title=b["title"],
                                   author=b["author"], publisher=b["publisher"],
                                   publish_year=b["publish_year"],
                                   availability_summary=b["availability_summary"])
                   for b in r["books"]],
        )

    def get_holdings(self, book_id):
        # 馆藏 JSON 与广州完全同构,直接走家族原语(NOTES.md 实测)
        hs = interlib.get_holdings(_CONFIG, book_id, only_available=False)
        return [_Holding(**h) for h in hs]

    def get_book_detail(self, book_id):
        html = interlib.client.get(_CONFIG, f"/opac/book/{book_id}")
        d = _parse_detail(html)
        if not d["title"]:
            raise RuntimeError(f"{_CONFIG.name_cn}：未找到该书详情：{book_id}")
        return SimpleNamespace(book_id=book_id, **d)


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"台州市图书馆搜索失败：{result.error}")

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
    """指定图书在各分馆的馆藏与可借状态,可借的排前面。"""
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
        # 契约测试要求已借出且带单册 item_id 时查归还时间;Interlib 的应还日期
        # 已在馆藏 JSON 里解析(loanWorkMap.returnDate),真网 item_id 恒空不会走到这
        if not available and getattr(h, "item_id", ""):
            item["due_date"] = _client.get_return_date(h.item_id)
        items.append(item)
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(book_id: str) -> BookDetail:
    """指定图书的完整详情:书名、作者、出版社、出版年、ISBN、索书号、内容简介。"""
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
