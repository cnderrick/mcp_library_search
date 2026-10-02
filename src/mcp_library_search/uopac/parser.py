"""汇文 Libsys/uopac 家族页面解析：金陵（`uopac.jllib.cn`）与扬州（`ytlmopac.cn`）共用。

两站的检索结果页、详情页、馆藏表实测逐项同构（字段侦察结论见
tests/fixtures/nanjing/NOTES.md 与 tests/fixtures/yangzhou/NOTES.md），
差异只在传输层（扬州多一道 securitycam cookie，见 client.py）。

本模块是纯函数层：不发起任何请求。返回家族内部结构（Book/Holding/SearchResult），
统一模型（base.py 的 TypedDict）的包装与跨源归并留在各适配器——归并口径是城市级的。
"""
from __future__ import annotations

import html
import math
import re
from dataclasses import dataclass, field

# 源站固定每页条数，无参数可调（`limit` 对源站无效）
PAGE_SIZE = 20


@dataclass
class Book:
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
class SearchResult:
    success: bool = True
    error: str = ""
    statistics: dict = field(default_factory=dict)
    books: list = field(default_factory=list)


@dataclass
class Holding:
    library: str = ""
    location: str = ""
    call_number: str = ""
    status: str = ""
    available: bool = False
    item_id: str = ""
    due_date: str = ""

    def is_available(self):
        return self.available


def clean(text):
    """去标签、&nbsp; 与首尾空白，返回纯文本原值。"""
    s = re.sub(r"<[^>]+>", "", html.unescape(str(text or "")))
    return s.replace("\xa0", " ").strip()


def _year(text):
    m = re.search(r"(?:19|20)\d{2}", str(text or ""))
    return m.group(0) if m else ""


def clean_publisher(text):
    """出版发行项形如「重庆:重庆出版社,2016」，拆出纯出版社名。同深圳口径。"""
    s = re.sub(r",?\s*(?:19|20)\d{2}\S*$", "", str(text or "")).strip()
    if re.search(r"[:：]", s):
        s = re.split(r"[:：]", s, maxsplit=1)[1].strip()
    return s


def looks_like_isbn(keyword):
    """ISBN 形态判断：去连字符后 13 位（978/979 开头）或 10 位（末位可为 X）。同深圳口径。"""
    s = str(keyword or "").replace("-", "").strip()
    if len(s) == 13 and s.isdigit():
        return s[:3] in ("978", "979")
    if len(s) == 10 and s[:9].isdigit():
        return s[9].isdigit() or s[9] in "Xx"
    return False


def isbn_wildcard(keyword):
    """ISBN → 数字间插 * 的通配查询（如 9*7*8*7*…）。

    ISBN 索引是存储原样前缀匹配、各馆连字符形态不一（金陵/扬州两站均实证），
    通配子序列匹配下等长即数字全等，* 只吸收连字符；X 校验位统一大写。
    """
    digits = re.sub(r"[^0-9Xx]", "", str(keyword)).upper()
    return "*".join(digits)


def norm_isbn(isbn):
    """ISBN 归一：去连字符与空白并转大写；非 ISBN 形态返回空串（不参与归并）。"""
    s = re.sub(r"[\s-]", "", str(isbn or "")).upper()
    return s if looks_like_isbn(s) else ""


# ---------- 检索结果页 ----------

RESULT_MARK = '<div id="found">'
_FOUND_TOTAL = re.compile(r'有\s*<font color="red">(\d+)</font>\s*项')
_NUM_PAGES = re.compile(
    r'<font color=red>(\d+)</font>&nbsp; / &nbsp;<font color=black>(\d+)</font>')
_BLOCKS = re.compile(r'<div class="searchcontent"\s*>(.*?)<div class="clear">', re.S)
# 裸请求（无 Cookie）时 Tomcat 把 action URL 重写为 detail.action;jsessionid=…?id=
# （NOTES.md「jsessionid URL 重写」）→ 容忍两者之间的任意段
_ENTRY_LINK = re.compile(r'detail\.action[^?]*\?id=(\d+)">(.*?)</a>', re.S)
_META_LINE = re.compile(r'<p style=color:#666;>(.*?)</p>', re.S)
_LIBS_LINE = re.compile(r'所在馆：</strong>(.*?)</p>', re.S)


def _split_meta_line(line):
    """元信息行「责任者 / 出版社 / ISBN / 出版年」→ (author, publisher, year, isbn)。

    固定末三段为出版社/ISBN/年，其余拼回责任者（责任者本身可能含斜杠）；
    不足四段时防御性退化为只有责任者（ISBN 空串）。
    """
    parts = [clean(p) for p in str(line or "").split("/")]
    if len(parts) < 4:
        return (clean(line), "", "", "")
    author = "/".join(parts[:-3]).strip()
    publisher = parts[-3]
    year = _year(parts[-1])
    return author, publisher, year, parts[-2]


def _parse_libs(raw):
    """所在馆块 → 馆名列表（名称间是空白与 &nbsp;）。"""
    text = html.unescape(str(raw or "")).replace("\xa0", " ")
    text = re.sub(r"<[^>]+>", "", text)
    return [n for n in text.split() if n]


def parse_search(text, source_prefix=""):
    """结果页 → {"books", "total_results", "total_pages"}。

    ISBN 从元信息行取原值（供跨源归并）；record_id 前缀由 source_prefix 补，
    单源城市传空串即裸 id。
    """
    m = _FOUND_TOTAL.search(text)
    total = int(m.group(1)) if m else None
    m = _NUM_PAGES.search(text)
    if m:
        total_pages = int(m.group(2))
    else:
        # 空结果页无 num 分页区 → 按源站固定每页 20 条回退
        total_pages = math.ceil(total / PAGE_SIZE) if total else 0
    books = []
    for block in _BLOCKS.findall(text):
        link = _ENTRY_LINK.search(block)
        if not link:
            continue
        rid, title = link.group(1), clean(link.group(2))
        meta = _META_LINE.search(block)
        author, publisher, year, isbn = _split_meta_line(meta.group(1) if meta else "")
        libs = _LIBS_LINE.search(block)
        names = _parse_libs(libs.group(1)) if libs else []
        books.append(Book(
            record_id=f"{source_prefix}{rid}",
            title=title,
            author=author,
            publisher=publisher,
            publish_year=year,
            availability_summary=("所在馆：" + "、".join(names)) if names else "",
            isbn=isbn,
        ))
    return {"books": books, "total_results": total, "total_pages": total_pages}


# ---------- 详情页 ----------

_DD = re.compile(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", re.S)
_TAB_NAME = re.compile(r'<li><a href="#loca_([A-Za-z0-9_]+)">(.*?)</a></li>')
_TAB_DATA = re.compile(
    r'<div id="loca_([A-Za-z0-9_]+)">.*?<span id="data"\s*>(.*?)</span>', re.S)


def parse_detail(text):
    """详情页 → 书目字段 dict。无索书号字段，call_number 恒空串（NOTES.md）。"""
    fields = {}
    for dt, dd in _DD.findall(text):
        fields[clean(dt).rstrip("：:")] = clean(dd)
    title, _, author = fields.get("题名/责任者", "").partition("/")
    publish = fields.get("出版发行项", "")
    return {
        "title": title.strip(),
        "author": author.strip(),
        "publisher": clean_publisher(publish),
        "publish_year": _year(publish),
        "isbn": fields.get("ISBN", ""),
        "call_number": "",
        "summary": fields.get("提要文摘附注", ""),
    }


def parse_tabs(text, base_url):
    """详情页馆藏 tab → [(馆名, ajax 绝对 URL)]。span#data 是相对 URL，& 可能
    以 &amp; 出现（页面 JS 有 replace 防御），统一 unescape。"""
    names = {code: clean(name) for code, name in _TAB_NAME.findall(text)}
    tabs = []
    for code, rel in _TAB_DATA.findall(text):
        rel = html.unescape(rel).strip()
        if "ajax_holding.action" not in rel:
            continue
        tabs.append((names.get(code, code), f"{base_url}/uopac/s/{rel}"))
    return tabs


# ---------- 馆藏表（ajax_holding 响应） ----------

_ITEM_ROW = re.compile(
    r'<tr align="center" bgcolor="#FFFFFF">\s*'
    r'<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*'
    r'<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>',
    re.S,
)
_DUE_DATE = re.compile(r"应还日期[：:]\s*(\d{4}-\d{2}-\d{2})")


def parse_holding_rows(text, library):
    """馆藏表 → 单册级 Holding 列表。列序：索书号/条码号/年卷期/校区/馆藏地/状态。

    条码号与年卷期无契约字段，舍弃；location=校区+馆藏地（空格连接，空段跳过）。
    状态词表：「可借」→ True；其余（含「借出-应还日期：X」「借出」与词表外）
    保守 False，原值照登；应还日期仅认「应还日期：YYYY-MM-DD」标准形态，
    否则空串不猜（扬州站实测只给裸「借出」，不给应还日期）。
    """
    holdings = []
    for callno, _barcode, _issue, campus, loc, status in _ITEM_ROW.findall(text):
        status = clean(status)
        m = _DUE_DATE.search(status)
        holdings.append(Holding(
            library=library,
            location=" ".join(x for x in (clean(campus), clean(loc)) if x),
            call_number=clean(callno),
            status=status,
            available=(status == "可借"),
            due_date=m.group(1) if m else "",
        ))
    return holdings
