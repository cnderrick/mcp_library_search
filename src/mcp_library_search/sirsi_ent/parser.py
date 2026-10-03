"""SirsiDynix Enterprise/VSE 页面解析（郑州实测，2026-10-03）。

三种解析：
- `parse_search`：检索结果页 HTML → 条目（entity/book_id、题名、著者、ISBN）。
- `parse_detail`：`detailnonmodal` 详情页 HTML → 书目字段（题名/著者/出版社/年/ISBN/
  索书号/提要）。
- `parse_holdings`：详情页内联单册表（资料类型/条形码/排架号/状态）＋
  `loadavailability` 可用性 JSON → 单册级馆藏。

字段侦察结论见 tests/fixtures/zhengzhou/NOTES.md。
"""
import re
from datetime import datetime

_ENTITY_RE = re.compile(r'value="(ent://[^"]+)"[^>]*id="da\d+"')
_ENTITY_RE2 = re.compile(r'id="da\d+"[^>]*value="(ent://[^"]+)"')
_TITLE_RE = re.compile(r'id="detailLink\d+"[^>]*>([^<]*)</a>')
_AUTHOR_RE = re.compile(
    r'INITIAL_AUTHOR_SRCH">[^<]*</div>\s*<div class="displayElementText[^"]*">\s*([^<]*)</div>')
_ISBN_RE = re.compile(r'value="([^"]*)"[^>]*class="isbnValue"')
_ISBN_RE2 = re.compile(r'class="isbnValue"[^>]*value="([^"]*)"')
_TOTAL_RE = re.compile(r'resultsToolbar_num_results">\s*([\d,]+)\s*找到结果')
_NO_RESULT_RE = re.compile(r"no_results_wrapper|本次检索未返回任何结果")
_CELL_RE = re.compile(r'id="results_cell(\d+)"')
_DETAIL_FIELD_RE = re.compile(
    r'displayElementLabel ([A-Z_0-9]+)_label">[^<]*</div>\s*'
    r'<div class="displayElementText[^"]*">\s*(.*?)\s*</div>', re.S)
_ROW_RE = re.compile(r'<tr class="detailItemsTableRow">(.*?)</tr>', re.S)
_TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_YEAR_RE = re.compile(r"(?:19|20)\d{2}")
_DUE_RE = re.compile(r"到期\s*(\d{2})-(\d{1,2})-(\d{1,2})")

# 不可借状态词：命中即不可借；「到期」另带 due_date。词表外观测值保守判不可借。
_UNAVAILABLE = ("到期", "在馆际调拨中", "调拨", "借出", "预约", "预借", "编目",
                "上架", "整理", "运送", "维修", "丢失", "剔除", "挂失", "保留",
                "订购", "注销", "闭架", "加工")


def _clean(text) -> str:
    """折叠空白、decode 常见 HTML 实体、去首尾空格。"""
    if text is None:
        return ""
    s = re.sub(r"<[^>]+>", "", str(text))
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return " ".join(s.split())


def decode_ent(raw: str) -> str:
    """Tapestry 实体编码 `ent:$002f$002fSD_ILS...` → `ent://SD_ILS...`。"""
    return (raw or "").replace("$002f", "/")


def _cell_blocks(html: str) -> list[str]:
    """按 results_cellN 切分检索结果条目块（无则返回空）。"""
    marks = list(_CELL_RE.finditer(html))
    blocks = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(html)
        blocks.append(html[m.start():end])
    return blocks


def parse_search(html: str) -> dict:
    """解析检索结果页。

    返回 {"books": [{book_id,title,author,publisher,publish_year,
    availability_summary,isbn}...], "total_results": int}。
    book_id 是 SirsiDynix 实体 URI（`ent://SD_ILS/<lib>/<id>`），详情/馆藏以此为凭。
    检索页不渲染出版社/出版年 → 二者空串（详情页有）。
    """
    total = 0
    m = _TOTAL_RE.search(html)
    if m:
        total = int(m.group(1).replace(",", ""))
    elif _NO_RESULT_RE.search(html):
        total = 0
    books = []
    for block in _cell_blocks(html):
        e = _ENTITY_RE.search(block) or _ENTITY_RE2.search(block)
        if not e:
            continue
        t = _TITLE_RE.search(block)
        a = _AUTHOR_RE.search(block)
        i = _ISBN_RE.search(block) or _ISBN_RE2.search(block)
        raw_title = _clean(t.group(1)) if t else ""
        title = raw_title.split(" /", 1)[0].strip() if " /" in raw_title else raw_title
        books.append({
            "book_id": e.group(1),
            "title": title,
            "author": _clean(a.group(1)) if a else "",
            "publisher": "",
            "publish_year": "",
            "availability_summary": "",
            "isbn": _clean(i.group(1)) if i else "",
        })
    return {"books": books, "total_results": total}


def _publication_info(value: str) -> tuple[str, str]:
    """出版信息（如「重庆, 重庆出版社 2008 2017重印」）→ (出版社, 出版年)。

    取首个逗号后段；出版年是段内首个四位年，出版社取年之前、去尾部标点分隔符。
    """
    s = value or ""
    if "," in s or "，" in s:
        s = re.split(r"[,，]", s, maxsplit=1)[1]
    ym = _YEAR_RE.search(s)
    if not ym:
        return _clean(s), ""
    publisher = _clean(s[:ym.start()]).rstrip(" ,，·")
    return publisher, ym.group(0)


def parse_detail(html: str) -> dict:
    """解析 `detailnonmodal` 详情页 → 书目字段 dict（缺失为空串）。

    字段来自 `displayElementLabel X_label` / `displayElementText X` 对：
    `INITIAL_TITLE_SRCH`（「题名 /著者」形态）、`INITIAL_AUTHOR_SRCH`、`ISBN`、
    `PUBLICATION_INFO`、`GENERAL_NOTE`（提要）。索书号取内联单册表的「排架号」首值。
    """
    fields = {}
    for name, value in _DETAIL_FIELD_RE.findall(html):
        if name not in fields:
            fields[name] = _clean(value)

    raw_title = fields.get("INITIAL_TITLE_SRCH", "")
    if " /" in raw_title:
        title = raw_title.split(" /", 1)[0].strip()
    else:
        title = raw_title.strip()
    author = fields.get("INITIAL_AUTHOR_SRCH", "") or fields.get("ADDED_AUTHOR", "")
    publisher, year = _publication_info(fields.get("PUBLICATION_INFO", ""))

    call_number = ""
    rows = _ROW_RE.findall(html)
    if rows:
        cells = [_clean(c) for c in _TD_RE.findall(rows[0])]
        if len(cells) >= 3:
            call_number = cells[2]

    return {
        "title": title,
        "author": author,
        "publisher": publisher,
        "publish_year": year,
        "isbn": fields.get("ISBN", ""),
        "call_number": call_number,
        "summary": fields.get("GENERAL_NOTE", ""),
    }


def _due_date(text: str) -> str:
    """从「到期 24-3-8」提应还日期 → 2024-03-08；提不到空串。"""
    m = _DUE_RE.search(text or "")
    if not m:
        return ""
    yy, mm, dd = (int(x) for x in m.groups())
    try:
        return datetime(2000 + yy, mm, dd).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _is_available(text: str) -> bool:
    """可借判定：空串或命中不可借词 → False，否则（地点名）→ True。"""
    s = text or ""
    if not s:
        return False
    if any(w in s for w in _UNAVAILABLE):
        return False
    return True


def parse_holdings(html: str, avail: dict | None = None) -> list[dict]:
    """详情页内联单册表 + `loadavailability` JSON → 单册级馆藏。

    内联表列：资料类型 / 图书条形码 / 排架号 / 状态（状态由可用性 JSON 异步填）。
    JSON `{ids:[条形码...], strings:[状态/地点...], totalAvailable}` 中 `strings[i]`
    是该单册「状态」列原值：可借时为馆藏地点名，不可借时为「到期 YY-M-D」/
    「在馆际调拨中」等状态词。故：命中不可借词判不可借，否则视为可借、地点作 library。
    """
    avail = avail or {}
    ids = [str(x) for x in (avail.get("ids") or [])]
    strings = [str(x) for x in (avail.get("strings") or [])]
    text_by_barcode = {b: (strings[i] if i < len(strings) else "")
                      for i, b in enumerate(ids)}
    holdings = []
    for row in _ROW_RE.findall(html):
        cells = [_clean(c) for c in _TD_RE.findall(row)]
        if len(cells) < 3:
            continue
        barcode = cells[1]
        text = text_by_barcode.get(barcode, cells[3] if len(cells) > 3 else "")
        available = _is_available(text)
        holdings.append({
            "library": text if available else "",
            "location": "",
            "call_number": cells[2],
            "status": text,
            "available": available,
            "due_date": _due_date(text) if not available else "",
        })
    return holdings
