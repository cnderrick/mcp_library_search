"""Interlib 家族页面解析：搜索页 HTML、详情页书目、馆藏 JSON。

以广州 OPAC 实抓 fixture 为基准（见 tests/fixtures/guangzhou/NOTES.md）；
同族城市页面同模板，解析按结构标记（class/属性）而非字面文案匹配。
"""
import re
from html.parser import HTMLParser

_PUB_YEAR_RE = re.compile(r"出版日期\s*[:：]?\s*((?:19|20)\d{2})")
_TOTAL_RE = re.compile(r"检索到\s*[:：]?\s*([\d,]+)\s*条")
_TOTAL_PAGES_RE = re.compile(r"共\s*(\d+)\s*页")


def _clean(text):
    """折叠空白、去 &nbsp;（\xa0），去首尾空格。"""
    return " ".join(text.replace(" ", " ").split())


class _SearchParser(HTMLParser):
    """搜索结果页：bookmeta 容器定边界，class 锚点定字段。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.books = []
        self.total_results = None
        self.total_pages = None
        self.has_next = False
        self._cur = None
        self._depth = 0
        self._capture = None   # 正在按 class 抓取的字段名（title/author/publisher）
        self._a_text = None    # 正在抓取的 a 标签文本

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "div" and "bookmeta" in (a.get("class") or "").split():
            self._finish_book()
            self._cur = {"book_id": a.get("bookrecno", ""), "parts": []}
            self._depth = 1
            return
        if tag == "a":
            # a 文本全局捕获：分页「下一页」锚点在 bookmeta 容器之外
            self._a_text = []
            if self._cur is not None:
                cls = a.get("class") or ""
                if "title-link" in cls:
                    self._capture = "title"
                elif "author-link" in cls:
                    self._capture = "author"
                elif "publisher-link" in cls:
                    self._capture = "publisher"
        elif self._cur is not None and tag == "div":
            self._depth += 1

    def handle_endtag(self, tag):
        if tag == "a" and self._a_text is not None:
            text = _clean("".join(self._a_text))
            if self._cur is not None and self._capture and text:
                self._cur[self._capture] = text
            if "下一页" in text:
                self.has_next = True
            self._a_text = None
            self._capture = None
            return
        if tag == "div" and self._cur is not None:
            self._depth -= 1
            if self._depth <= 0:
                self._finish_book()

    def handle_data(self, data):
        if self._a_text is not None:
            self._a_text.append(data)
        if self._cur is not None:
            self._cur["parts"].append(data)
        m = _TOTAL_RE.search(data)
        if m:
            self.total_results = int(m.group(1).replace(",", ""))
        m = _TOTAL_PAGES_RE.search(data)
        if m:
            self.total_pages = int(m.group(1))

    def _finish_book(self):
        if self._cur is None:
            return
        text = "".join(self._cur["parts"])
        m = _PUB_YEAR_RE.search(text)
        self.books.append({
            "book_id": self._cur["book_id"],
            "title": self._cur.get("title", ""),
            "author": self._cur.get("author", ""),
            "publisher": self._cur.get("publisher", ""),
            "publish_year": m.group(1) if m else "",
            "availability_summary": "",
        })
        self._cur = None


def parse_search(html: str) -> dict:
    """解析 Interlib 搜索页。

    返回 {"books": [{book_id,title,author,publisher,publish_year,
    availability_summary}...], "total_results": int|None,
    "total_pages": int, "has_next": bool}。total_results 解析不到为 None；
    total_pages 解析不到时保守取 1。
    """
    p = _SearchParser()
    p.feed(html)
    p._finish_book()
    return {
        "books": p.books,
        "total_results": p.total_results,
        "total_pages": p.total_pages if p.total_pages is not None else 1,
        "has_next": p.has_next,
    }
