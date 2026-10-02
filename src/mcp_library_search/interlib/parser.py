"""Interlib 家族页面解析：搜索页 HTML、详情页书目、馆藏 JSON。

以广州 OPAC 实抓 fixture 为基准（见 tests/fixtures/guangzhou/NOTES.md）；
同族城市页面同模板，解析按结构标记（class/属性）而非字面文案匹配。
"""
import json
import re
from datetime import datetime, timedelta
from html.parser import HTMLParser

_PUB_YEAR_RE = re.compile(r"出版日期\s*[:：]?\s*((?:19|20)\d{2})")
_TOTAL_RE = re.compile(r"检索到\s*[:：]?\s*([\d,]+)\s*条")
_TOTAL_PAGES_RE = re.compile(r"共\s*(\d+)\s*页")
_ISBN_RE = re.compile(r"[\d\-]{10,}")
# 条目后随的 expressServiceTab div（bookmeta 的兄弟节点）带 ISBN 属性，
# 作内部字段供天津三源 ISBN 归并；不进 BookSummary 契约
_EXPRESS_ISBN_RE = re.compile(
    r'express_bookrecno="(\d+)"[^>]*?express_isbn="([^"]*)"')
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")


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
            "isbn": self._cur.get("isbn", ""),
        })
        self._cur = None


def parse_search(html: str) -> dict:
    """解析 Interlib 搜索页。

    返回 {"books": [{book_id,title,author,publisher,publish_year,
    availability_summary,isbn}...], "total_results": int|None,
    "total_pages": int, "has_next": bool}。total_results 解析不到为 None；
    total_pages 解析不到时保守取 1。isbn 为内部字段（express_isbn 属性），
    不进 BookSummary 契约。
    """
    p = _SearchParser()
    p.feed(html)
    p._finish_book()
    isbns = {rec: isbn.strip() for rec, isbn in _EXPRESS_ISBN_RE.findall(html)}
    for b in p.books:
        b["isbn"] = isbns.get(b["book_id"], "")
    return {
        "books": p.books,
        "total_results": p.total_results,
        "total_pages": p.total_pages if p.total_pages is not None else 1,
        "has_next": p.has_next,
    }


# 详情页标签 → 语义字段（值单元的归类在 _DetailParser 里按标签分派）
_DETAIL_LABELS = {
    "ISBN": "isbn",
    "出版发行": "publish",
    "内容提要": "summary",
    "中图分类法": "call_number",
    "主要责任者": "author",
}


class _DetailParser(HTMLParser):
    """详情页 bookInfoTable：leftTD 是标签、rightTD 是值，标题在首个 h2。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fields = {k: "" for k in
                       ("title", "author", "publisher", "publish_year",
                        "isbn", "call_number", "summary")}
        self._cell = None        # None | "label" | "value"
        self._label_parts = []
        self._label = ""
        self._value_parts = []
        self._link_parts = None      # 非 None 表示正在抓 <a> 文本
        self._first_link = ""        # 值单元格里第一个 <a> 的文本
        self._title_parts = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "td":
            if "leftTD" in cls:
                self._cell = "label"
                self._label_parts = []
            elif "rightTD" in cls:
                self._cell = "value"
                self._value_parts = []
                self._first_link = ""
            return
        if tag == "h2" and not self.fields["title"]:
            self._title_parts = []
            return
        if (tag == "a" and self._cell == "value"
                and not self._first_link and self._link_parts is None):
            self._link_parts = []

    def handle_endtag(self, tag):
        if tag == "a" and self._link_parts is not None:
            self._first_link = _clean("".join(self._link_parts))
            self._link_parts = None
            return
        if tag == "h2" and self._title_parts is not None:
            self.fields["title"] = _clean("".join(self._title_parts))
            self._title_parts = None
            return
        if tag == "td" and self._cell == "label":
            self._label = _clean("".join(self._label_parts)).rstrip("：:").strip()
            self._cell = None
            return
        if tag == "td" and self._cell == "value":
            self._finish_value()
            self._cell = None
            return

    def handle_data(self, data):
        if self._title_parts is not None:
            self._title_parts.append(data)
        if self._link_parts is not None:
            self._link_parts.append(data)
        if self._cell == "label":
            self._label_parts.append(data)
        elif self._cell == "value":
            self._value_parts.append(data)

    def _finish_value(self):
        label, value, link = self._label, _clean("".join(self._value_parts)), self._first_link
        # 标签与值一对一消费：无 leftTD 的 rightTD（如 tagTr「标签」行）
        # 不得继承上一行已消费的陈旧标签（2026-10-02，江阴/温州独立实证）
        self._label = ""
        if label not in _DETAIL_LABELS or not value:
            return
        kind = _DETAIL_LABELS[label]
        if kind == "isbn":
            m = _ISBN_RE.search(value)
            self.fields["isbn"] = m.group(0) if m else ""
        elif kind == "publish":
            self.fields["publisher"] = link
            m = _YEAR_RE.search(value)
            self.fields["publish_year"] = m.group(0) if m else ""
        elif kind == "summary":
            self.fields["summary"] = value
        elif kind == "call_number":
            self.fields["call_number"] = value.split("版次")[0].strip()
        elif kind == "author":
            self.fields["author"] = link or (value.split()[0] if value else "")


def parse_detail(html: str) -> dict:
    """解析 Interlib 详情页书目字段，缺失字段为空串。"""
    p = _DetailParser()
    p.feed(html)
    return p.fields


# 可借/不可借状态词：命中不可借词优先，都不中保守判不可借（计划 Review Focus）。
# 词表覆盖 holdStateMap 已知 29 项中的流通语义（在馆/借出/闭架/丢失/剔除/编目……），
# 未来新增状态未识别时一律不可借，避免读者白跑。
_UNAVAILABLE_WORDS = ("借出", "预约", "预借", "阅览", "闭架", "丢失", "剔除",
                      "编目", "运送", "维修", "赔偿", "加工", "挂失", "保留",
                      "订购", "还回", "交换", "赠送", "注销")
_AVAILABLE_WORDS = ("在馆", "可借", "在架")

_EPOCH_BASE = datetime(1970, 1, 1)
_DATE_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def is_available_status(status: str) -> bool:
    """按状态文本判可借：命中不可借词优先，命中可借词次之，都不中保守不可借。"""
    s = status or ""
    if any(w in s for w in _UNAVAILABLE_WORDS):
        return False
    if any(w in s for w in _AVAILABLE_WORDS):
        return True
    return False


def _to_date(value) -> str:
    """应还日期归一为 YYYY-MM-DD。支持 epoch 毫秒（Interlib 实测形态，按 UTC+8
    解释，与馆方系统时区一致）、YYYY-MM-DD、YYYYMMDD；取不到返回空串。"""
    s = str(value or "").strip()
    if not s:
        return ""
    if s.isdigit() and len(s) >= 12:
        return (_EPOCH_BASE + timedelta(milliseconds=int(s), hours=8)).strftime("%Y-%m-%d")
    m = _DATE_ISO_RE.match(s)
    if m:
        return m.group(0)
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:]}"
    return ""


def _holding_due_date(item: dict, loan_work: dict) -> str:
    """借出单册的应还日期：优先 loanWorkMap[barcode].returnDate，退回单册 loan 字段。"""
    barcode = str(item.get("barcode") or "")
    work = loan_work.get(barcode)
    if isinstance(work, dict):
        due = _to_date(work.get("returnDate") or work.get("retudate") or "")
        if due:
            return due
    loan = item.get("loan")
    if isinstance(loan, dict):
        return _to_date(loan.get("returnDate") or loan.get("retudate") or "")
    return ""


def parse_holdings(payload: dict) -> list[dict]:
    """解析馆藏 JSON（/opac/api/holding/{bookrecno} 的响应体）。

    返回 [{"library","location","call_number","status","due_date"}...]；
    馆码/位置码/状态码分别经 libcodeMap/localMap/holdStateMap 翻译，查不到回退码本身。
    可借与否不在此处判定（见 is_available_status，由接线层使用）。
    """
    payload = payload or {}
    items = payload.get("holdingList") or []
    state_map = payload.get("holdStateMap") or {}
    lib_map = payload.get("libcodeMap") or {}
    local_map = payload.get("localMap") or {}
    loan_work = payload.get("loanWorkMap") or {}
    holdings = []
    for it in items:
        if not isinstance(it, dict):
            continue
        state = state_map.get(str(it.get("state"))) or {}
        holdings.append({
            "library": str(lib_map.get(str(it.get("curlib")), it.get("curlib") or "")),
            "location": str(local_map.get(str(it.get("curlocal")), it.get("curlocal") or "")),
            "call_number": str(it.get("callno") or ""),
            "status": str(state.get("stateName") or ""),
            "due_date": _holding_due_date(it, loan_work),
        })
    return holdings
