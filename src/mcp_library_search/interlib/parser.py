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


def parse_solr(payload: dict, name: str = "") -> dict:
    """站点内嵌 Solr 检索响应（`wt=json`）→ {"books", "total_results"}。

    形态（青岛及一批带滑动验证码的 Interlib 站点共用，见
    tests/fixtures/qingdao/NOTES.md）：命中数 `response.numFound`，书目在
    `response.docs[]`，字段名带 `_meta` 后缀（`title_meta`/`author_meta`/
    `publisher_meta`/`pubdate_meta`/`isbn_meta`），稳定 id 是 `docs[].id`。
    `availability_summary` 恒空串（Solr 无逐书目可借概况）。缺少 `response`
    键即视为接口形态漂移或 Solr 查询出错，抛错而非静默返回 0 条。
    """
    if not isinstance(payload, dict) or "response" not in payload:
        detail = ""
        if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
            detail = f"：{str(payload['error'].get('msg') or '').strip()}"
        prefix = f"{name}：" if name else ""
        raise RuntimeError(f"{prefix}检索响应缺少 response（Solr 查询出错或接口变更）{detail}")
    resp = payload.get("response") or {}
    try:
        total = int(resp.get("numFound") or 0)
    except (TypeError, ValueError):
        total = 0
    books = []
    for doc in resp.get("docs") or []:
        if not isinstance(doc, dict):
            continue
        book_id = "" if doc.get("id") is None else str(doc.get("id")).strip()
        if not book_id:
            continue
        pub = str(doc.get("pubdate_meta") or "")
        ym = _YEAR_RE.search(pub)
        books.append({
            "book_id": book_id,
            "title": _clean(doc.get("title_meta")),
            "author": _clean(doc.get("author_meta")),
            "publisher": _clean(doc.get("publisher_meta")),
            "publish_year": ym.group(0) if ym else "",
            "availability_summary": "",
            "isbn": _clean(doc.get("isbn_meta")),
        })
    return {"books": books, "total_results": total}


def parse_detail_api(payload: dict) -> dict:
    """解析 `/api/book/{recno}` JSON 的书目字段（api_detail 城市用）。

    返回与 parse_detail 同形的 dict。字段：`biblios.title/author/publisher/
    pubdate(→四位年)/isbn/classNo/summary`，缺失为空串。
    """
    b = (payload or {}).get("biblios") or {}

    def s(key):
        v = b.get(key)
        return "" if v is None else str(v).strip()

    ym = _YEAR_RE.search(s("pubdate"))
    return {
        "title": s("title"),
        "author": s("author"),
        "publisher": s("publisher"),
        "publish_year": ym.group(0) if ym else "",
        "isbn": s("isbn"),
        "call_number": s("classNo"),
        "summary": s("summary"),
    }


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


# ---------- pro2018 模板代解析（台州/成都/绍兴共用，2026-10-02 家族化） ----------

_PRO2018_TOTAL_RE = re.compile(r'schResNumIn">\s*([\d,]+)\s*</i>')
_PRO2018_TOTAL_PAGES_RE = re.compile(r"totalPage:\s*(\d+)")
_PRO2018_CURRENT_PAGE_RE = re.compile(r"currentPage:\s*(\d+)")
# 空结果页不渲染总数区，但有明确提示锚点（源站明说没有相关书目 → 判 0，不是猜测）
_PRO2018_NO_RESULT_RE = re.compile(r"notFindFt")
_PRO2018_BOOK_DETAIL_RE = re.compile(r"bookDetail\((\d+)")
_PRO2018_YEAR_RE = re.compile(r"(?:19|20)\d{2}")


class _Pro2018SearchParser(HTMLParser):
    """pro2018 搜索结果页：li.libBookLi 容器定边界，class/标签锚点定字段。

    - 标题：第一个 a.libBookDetNm；书目 ID 取其 href 的 bookDetail（数字，
      封面 img 的 bookrecno 属性兜底（条目内该属性散落多处，均同值）。
    - 字段标签是 span.libBkDetTit 文本（责任者/出版信息），标签后随首个 <a>：
      作者、出版社取 a 文本；出版年是出版社 a 之后、下一个 <p> 之前的裸文本
      （「,2010.11」形态）；ISBN 取封面 img 的 isbn 属性（内部字段，不进契约）。
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
            # 封面 img 属性兜底：isbn 与 bookrecno
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
                m = _PRO2018_BOOK_DETAIL_RE.search(href)
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
        # 条目内嵌套 li（馆藏信息 tab 等）不影响边界：只认 libBookLi class 开新条

    def handle_data(self, data):
        if self._cur is None:
            return
        if self._in_label:
            self._label_parts.append(data)
        if self._a_text is not None:
            self._a_text.append(data)
        if self._tail and not self._tail_done:
            m = _PRO2018_YEAR_RE.search(data)
            if m:
                self._cur["publish_year"] = m.group(0)
                self._tail_done = True

    def _finish_book(self):
        if self._cur is not None:
            if self._cur["book_id"]:
                self._cur["availability_summary"] = ""
                self.books.append(self._cur)
            self._cur = None


def _parse_search_pro2018(html: str) -> dict:
    """解析 pro2018 搜索页（libBookLi 模板），返回结构与家族 parse_search 对齐。

    返回 {"books": [{book_id,title,author,publisher,publish_year,
    availability_summary,isbn}...], "total_results": int|None,
    "total_pages": int, "has_next": bool}。total_results：总数区缺失且无
    空结果提示时为 None；total_pages 解析不到保守取 1；
    has_next = currentPage < totalPage（JS 分页配置，页面无可点分页锚点）。
    """
    p = _Pro2018SearchParser()
    p.feed(html)
    p._finish_book()
    m = _PRO2018_TOTAL_RE.search(html)
    if m:
        total_results = int(m.group(1).replace(",", ""))
    elif _PRO2018_NO_RESULT_RE.search(html):
        total_results = 0
    else:
        total_results = None
    tp = _PRO2018_TOTAL_PAGES_RE.search(html)
    cp = _PRO2018_CURRENT_PAGE_RE.search(html)
    total_pages = int(tp.group(1)) if tp else 1
    current_page = int(cp.group(1)) if cp else 1
    return {
        "books": p.books,
        "total_results": total_results,
        "total_pages": total_pages,
        "has_next": current_page < total_pages,
    }


# ---------- pro2018 详情页解析（bkTxt 模板 + 可选引文块责任者兜底） ----------
# 标签词表：ISBN/出版发行/中图分类法（内容提要/主要责任者按记录可选，
# 实抓记录均缺，保留词表位以待有记录带该 li 时照抓）；标题取 a.bkTxtTit。
# 责任者兜底（cite_author=True 时启用，绍兴实证）：引文块 div.sendToConIn
# 「刘慈欣著.三体.重庆出版社,2010.11.」取首个句点前段（原值照登，含「著/编」字样）；
# 简介无标签行则恒空串（数据边界）。
_PRO2018_DETAIL_LABELS = {
    "ISBN": "isbn",
    "出版发行": "publish",
    "内容提要": "summary",
    "中图分类法": "call_number",
    "主要责任者": "author",
}
_PRO2018_ISBN_RE = re.compile(r"[\d\-]{10,}")


class _Pro2018DetailParser(HTMLParser):
    """pro2018 默认详情页：bkTxtLeft/bkTxtRight 两列，每字段一个 li（标签：<span>值）；
    责任者可选从引文块 sendToConIn 兜底。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.fields = {k: "" for k in
                       ("title", "author", "publisher", "publish_year",
                        "isbn", "call_number", "summary")}
        self._depth = 0            # 字段列容器深度，0 = 不在容器内
        self._label = None         # 当前 li 的标签（None = 不在 li 内）
        self._label_parts = []
        self._in_span = False
        self._span_parts = []
        self._link_parts = None    # 非 None 表示正在抓值内首个 <a> 文本
        self._first_link = ""
        self._title_parts = None
        self._cite_parts = None    # 非 None 表示正在抓引文块文本
        self._citation = ""        # 首个 sendToConIn 的完整文本

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if tag == "a" and "bkTxtTit" in cls and not self.fields["title"]:
            self._title_parts = []
            return
        if tag == "div" and "sendToConIn" in cls and not self._citation:
            self._cite_parts = []
            return
        if tag == "div" and ("bkTxtLeft" in cls or "bkTxtRight" in cls):
            self._depth = 1        # 两列是兄弟容器，进入新列重置深度
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
        if tag == "div" and self._cite_parts is not None:
            self._citation = _clean("".join(self._cite_parts))
            self._cite_parts = None
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
        if self._cite_parts is not None:
            self._cite_parts.append(data)
        if not self._depth:
            return
        if self._in_span:
            self._span_parts.append(data)
            if self._link_parts is not None:
                self._link_parts.append(data)
        elif self._label is not None:
            # li 内、span 前的文本是标签（「ISBN：」形态，全/半角冒号均现）
            self._label_parts.append(data)
            joined = "".join(self._label_parts)
            m = re.split("([：:])", joined, maxsplit=1)
            if len(m) > 1:
                self._label = m[0].strip()

    def _assign_value(self):
        label = self._label or ""
        value = _clean("".join(self._span_parts))
        if label not in _PRO2018_DETAIL_LABELS or not value:
            return
        kind = _PRO2018_DETAIL_LABELS[label]
        if kind == "isbn":
            m = _PRO2018_ISBN_RE.search(value)
            self.fields["isbn"] = m.group(0) if m else ""
        elif kind == "publish":
            # 出版社取首个 a 文本（去尾部逗号）；出版年在整格文本里找
            self.fields["publisher"] = self._first_link.rstrip("，,").strip()
            m = _PRO2018_YEAR_RE.search(value)
            self.fields["publish_year"] = m.group(0) if m else ""
        elif kind == "summary":
            self.fields["summary"] = value
        elif kind == "call_number":
            self.fields["call_number"] = value.split("版次")[0].strip()
        elif kind == "author":
            self.fields["author"] = self._first_link or (value.split()[0] if value else "")

    def finish(self):
        """引文块兜底：标签行无责任者时，取引文首个句点前段（「刘慈欣著.三体.…」）。"""
        if not self.fields["author"] and self._citation:
            self.fields["author"] = self._citation.split(".", 1)[0].strip()


def _parse_detail_pro2018(html: str, cite_author: bool = False) -> dict:
    """解析 pro2018 默认详情页（bkTxt 模板），返回结构与家族 parse_detail 对齐，
    缺失字段为空串；cite_author=True 启用引文块责任者兜底（绍兴实证）。"""
    p = _Pro2018DetailParser()
    p.feed(html)
    if cite_author:
        p.finish()
    return p.fields


def parse_search_pro2018(html: str) -> dict:
    """pro2018 模板代搜索结果页解析（家族化自台州/成都/绍兴适配器，2026-10-02）。"""
    return _parse_search_pro2018(html)


def parse_detail_pro2018(html: str, cite_author: bool = False) -> dict:
    """pro2018 模板代详情页解析；cite_author=True 启用引文块责任者兜底（绍兴）。"""
    return _parse_detail_pro2018(html, cite_author=cite_author)
