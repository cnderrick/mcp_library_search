r"""Ex Libris ALEPH www_f_chi 家族 HTML 解析（纯函数，无 I/O）。

结构基准：天津主馆实抓 fixture（tests/fixtures/tianjin/NOTES.md）。
南京图书馆（tests/fixtures/nanjing_prov/NOTES.md）同版本同皮肤，标记逐项兼容。

被解析的三种页面：
- find-b 检索页：brief 列表（多条）或 ISB 单命中直出的完整记录页（1 条）；
- full-set-set / SYS 单命中详情页：publish section 注释块给结构化字段；
- item-global 单册页：`<!--Loan status-->` 等列注释定位单元格。

已知家族陷阱（已修，留档）：字段行的取值正则不能写 `\s*`——它会跨行，字段为空时
把下一行文本吞成值（如空 ISBN 吞掉下一行 SET-NUMBER/TITLE）。天津 fixture 各字段
全非空故从未暴露，南图的音像与古籍记录踩中；钉在
tests/test_nanjing_prov_recon.py 与 tests/fixtures/nanjing_prov/NOTES.md。
"""
from __future__ import annotations

import html
import math
import re
from dataclasses import dataclass, field

PAGE_SIZE = 10  # ALEPH brief 每页固定 10 条，short-jump 按记录偏移翻页


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
    available: bool = True
    item_id: str = ""
    due_date: str = ""

    def is_available(self):
        return self.available


def looks_like_isbn(keyword):
    """ISBN 形态判断：去连字符后 13 位（978/979 开头）或 10 位（末位可为 X）。同深圳口径。"""
    s = str(keyword or "").replace("-", "").strip()
    if len(s) == 13 and s.isdigit():
        return s[:3] in ("978", "979")
    if len(s) == 10 and s[:9].isdigit():
        return s[9].isdigit() or s[9] in "Xx"
    return False


def clean(text):
    """去标签、&nbsp; 与首尾空白，返回纯文本原值。"""
    s = re.sub(r"<[^>]+>", "", html.unescape(str(text or "")))
    return s.replace("\xa0", " ").strip()


def year(text):
    m = re.search(r"(?:19|20)\d{2}", str(text or ""))
    return m.group(0) if m else ""


# ---- brief 检索页 ----

COUNT = re.compile(r"记录\s*(\d+)\s*-\s*(\d+)\s*of\s*([\d,]+)")
JUMP = re.compile(r'(http://[^"\'\s>]*func=short-jump&jump=)\d+')
BRIEF_DOC = re.compile(r"DOC-NUMBER \(3300\)\s*=\s*(\d+)")
# 值前后只允许同行空白：`\s*` 会跨行，字段为空时把下一行（如 SET-NUMBER / TITLE）吞成值。
# 天津 fixture 各字段全非空故从未暴露；南图音像与古籍记录踩中（NOTES.md）。
BRIEF_ISBN = re.compile(r"Z13-ISBN-ISSN \(3100\)[^\S\n]*=[^\S\n]*([^\n<]+)")
TITLE = re.compile(r'<div class=itemtitle><a [^>]*>(.*?)</a>', re.S)


def brief_field(label, chunk):
    """brief 字段表：`{label}：<td class=content...>值` 到下一个 <td 为止。"""
    m = re.search(label + r"<td class=content[^>]*>(.*?)(?=<td|<tr|</table)", chunk, re.S)
    return clean(m.group(1)) if m else ""


def parse_find(text, source):
    """find-b 响应 → {"books", "total_results", "total_pages"}。

    两种形态：brief 列表（多条）与 ISB 单命中直接给的完整记录页（1 条）。
    brief 页的 publish section 注释块多于真实条目（13 vs 10），以 itemtitle 锚定并按
    DOC-NUMBER 去重。
    """
    if "class=itemtitle" not in text:
        b = parse_full_record(text, source)
        return {"books": [b] if b else [], "total_results": 1 if b else 0, "total_pages": 1}

    books = []
    seen = set()
    for chunk in text.split("<!-- publish section")[1:]:
        if "class=itemtitle" not in chunk:
            continue
        dm = BRIEF_DOC.search(chunk)
        if not dm or dm.group(1) in seen:
            continue
        seen.add(dm.group(1))
        tm = TITLE.search(chunk)
        im = BRIEF_ISBN.search(chunk)
        pub = brief_field("出版社：", chunk)
        books.append(Book(
            record_id=f"{source}:{dm.group(1)}",
            title=clean(tm.group(1)) if tm else "",
            author=brief_field("作者：", chunk),
            publisher=pub,
            publish_year=brief_field("年份：", chunk) or year(pub),
            isbn=clean(im.group(1)) if im else "",
            call_number=brief_field("索书号：", chunk),
        ))
    cm = COUNT.search(text)
    total = int(cm.group(3).replace(",", "")) if cm else len(books)
    return {"books": books, "total_results": total,
            "total_pages": max(1, math.ceil(total / PAGE_SIZE))}


# ---- 完整记录页（ISB/SYS 单命中 / full-set-set 详情共用） ----

FULL_DOC = re.compile(r"DOC-NUMBER:\s*(\d+)")
# 同 BRIEF_ISBN：值前后只吃同行空白。南图古籍记录 ISBN/IMPRINT 为空，原 `\s*`
# 会把下一行的 TITLE/CALL-NO 当成 ISBN/出版社返回（实抓 detail_guji_empty_fields.html）。
FULL_FIELDS = {
    "isbn": re.compile(r"ISBN:[^\S\n]*([^\n]+)"),
    "title": re.compile(r"TITLE:[^\S\n]*([^\n]+)"),
    "author": re.compile(r"AUTHOR:[^\S\n]*([^\n]+)"),
    "imprint": re.compile(r"IMPRINT:[^\S\n]*([^\n]+)"),
    "callno": re.compile(r"CALL-NO:[^\S\n]*([^\n]+)"),
}


def full_field(name, text):
    m = FULL_FIELDS[name].search(text)
    return clean(m.group(1)) if m else ""


def parse_full_record(text, source):
    """单命中的完整记录页 → 单条 Book（无命中返回 None）。"""
    m = FULL_DOC.search(text)
    if not m:
        return None
    imprint = full_field("imprint", text)
    return Book(
        record_id=f"{source}:{m.group(1)}",
        title=full_field("title", text),
        author=full_field("author", text),
        publisher=imprint,
        publish_year=year(imprint),
        isbn=full_field("isbn", text),
        call_number=full_field("callno", text),
    )


# ---- 单册页 item-global（列结构见 NOTES.md） ----

ITEM_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
# 可借性原值在「应还日期」列（在架上/日期）；「单册状态」列是流通类型（阅览/中文图书借阅…）
AVAIL_WORDS = ("在架", "在馆", "可借")


def item_cell(row, marker):
    m = re.search(r"<!--" + marker + r"-->\s*<td[^>]*>(.*?)</td>", row, re.S)
    return clean(m.group(1)) if m else ""


def norm_due(text):
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


def parse_item_global(text):
    """item-global 单册页 → Holding 列表。

    可借判定只看应还日期列：含「在架/在馆/可借」→ 可借；是日期 → 已借出（due_date 归一）；
    其余（含空）保守不可借。流通类型列不参与判定，但与状态原值一并保留在 status 里。
    """
    holdings = []
    for row in ITEM_ROW.findall(text):
        if "<!--Loan status-->" not in row:
            continue
        loan = item_cell(row, "Loan status")
        due = item_cell(row, "Due date")
        date = norm_due(due)
        if date:
            status, due_date, available = loan, date, False
        else:
            # 两列同值（真网实测：分配中/编目中/物流中）拼接会重复，去重不丢原值
            status = " ".join(dict.fromkeys(x for x in (loan, due) if x))
            due_date = ""
            available = any(w in due for w in AVAIL_WORDS)
        holdings.append(Holding(
            library=item_cell(row, "Sub-library"),
            location=item_cell(row, "Collection"),
            call_number=item_cell(row, "Location"),
            status=status,
            available=available,
            due_date=due_date,
        ))
    return holdings
