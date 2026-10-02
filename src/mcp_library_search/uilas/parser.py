"""UILAS（ILAS 系 HTML OPAC）家族解析层：检索结果页／详情页／内联馆藏表。

纯函数、无网络。字段侦察结论见 tests/fixtures/jinhua/NOTES.md 与
tests/fixtures/zhoushan/NOTES.md。JSP 模板在单元格里留大量换行/制表符/
条件分支残片，取值前一律 `_clean` 压缩空白。
"""
from __future__ import annotations

import html
import re

# 状态词表仅这两词（用户定调口径）：「入藏」可借，「借出」不可借，词表外保守不可借
AVAILABLE_STATUS = {"入藏"}

_TOTAL = re.compile(r"共有\s*\[(\d*)\]条记录")       # 空结果页括号为空 → 0
_PAGENO = re.compile(r"页码:\s*(\d+)/(\d*)")          # 空结果页「页码: 1/」无总页数 → 1
_ENTRY_SPLIT = '<h3 class="title">'                   # 条目分块锚点（页面 JS 里也有 checkbox 字样，不能数裸字符串）
_RECNO = re.compile(r'name="bookItemCheckbox"\s+value="(\d+)"')
_RECNO_LINK = re.compile(r"recno=(\d+)")
_TITLE_A = re.compile(r"<a[^>]*>(.*?)</a>", re.S)

_DETAIL_TITLE = re.compile(r'<h3 class="title">\s*<a[^>]*>(.*?)</a>', re.S)
_SUMMARY = re.compile(r'<strong>附注提要</strong>.*?<div class="text"[^>]*>(.*?)</div>', re.S)

_HOLDING_ANCHOR = 'id="BookHolding"'
_TABLE = re.compile(r'<table[^>]*class="table"[^>]*>(.*?)</table>', re.S)
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TH = re.compile(r"<th[^>]*>(.*?)</th>", re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def clean(text):
    """去标签、解转义、压缩空白，返回纯文本原值。"""
    s = re.sub(r"<[^>]+>", "", html.unescape(str(text or "")))
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def year(text):
    """从出版日期原值提取公历年；民国纪年等提不到则空串（不做换算猜测）。同重庆口径。"""
    m = re.search(r"(?:19|20)\d{2}", str(text or ""))
    return m.group(0) if m else ""


def is_result_page(text):
    """总数锚点在＝结果页（空结果页也有「共有 []条记录」）；缺失＝被打回别的页。"""
    return bool(_TOTAL.search(text))


def _entry_field(label, chunk):
    m = re.search(label + r"：<span[^>]*>(.*?)</span>", chunk, re.S)
    return clean(m.group(1)) if m else ""


def parse_search(text):
    """检索结果页 → {"books", "total_results", "total_pages"}。列表页无状态词。"""
    books = []
    for chunk in text.split(_ENTRY_SPLIT)[1:]:
        m = _RECNO.search(chunk) or _RECNO_LINK.search(chunk)
        if not m:
            continue
        t = _TITLE_A.search(chunk)
        books.append({
            "book_id": m.group(1),
            "title": clean(t.group(1)) if t else "",
            "author": _entry_field("作者", chunk),
            "publisher": _entry_field("出版社", chunk),
            "publish_year": year(_entry_field("出版时间", chunk)),
        })
    tm = _TOTAL.search(text)
    total = int(tm.group(1)) if tm and tm.group(1) else 0
    pm = _PAGENO.search(text)
    total_pages = int(pm.group(2)) if pm and pm.group(2) else 1
    return {"books": books, "total_results": total, "total_pages": total_pages}


def _li_field(label, text):
    m = re.search(r"<li>" + label + r"：(.*?)</li>", text, re.S)
    return clean(m.group(1)) if m else ""


def parse_detail(text):
    """详情页 → 书目字段 dict。标题取 h3.title 第一个 <a>（形态「标题</a>/<a>作者」）。"""
    tm = _DETAIL_TITLE.search(text)
    sm = _SUMMARY.search(text)
    return {
        "title": clean(tm.group(1)) if tm else "",
        "author": _li_field("作者", text),
        "publisher": _li_field("出版社", text),
        "publish_year": year(_li_field("出版日期", text)),
        "isbn": _li_field("ISBN/ISSN", text),   # 查无 ISBN 时原值「书号不详」照登
        "call_number": _li_field("分类号", text),
        "summary": clean(sm.group(1)) if sm else "",  # 内联附注提要；无则空串
    }


def _cell(cells, idx, label):
    n = idx.get(label)
    return cells[n] if n is not None and n < len(cells) else ""


def parse_holdings(text):
    """详情页 div#BookHolding → 单册级馆藏 dict 列表。

    锚点切片天然排除其前的 CADAL 数字图书表；只有入藏复本时单表（「馆藏信息」），
    有借出复本时两表（＋「已外借馆藏」），全部遍历合并。列位按 th 标签映射
    （第 7 列两表文案不一：预借/预约，且属动作列不入数据）。借出无应还日期列，
    due_date 恒空。
    """
    i = text.find(_HOLDING_ANCHOR)
    if i < 0:
        return []
    holdings = []
    for tbl in _TABLE.findall(text[i:]):
        labels = [clean(x) for x in _TH.findall(tbl)]
        idx = {lab: n for n, lab in enumerate(labels)}
        for row in _TR.findall(tbl):
            cells = [clean(c) for c in _TD.findall(row)]
            if not cells:
                continue  # thead 行（只有 th）或空行
            h = {
                "library": _cell(cells, idx, "当前所在馆"),
                "location": _cell(cells, idx, "当前所在地点"),
                "call_number": _cell(cells, idx, "索书号"),
                "status": _cell(cells, idx, "馆藏状态"),
                "available": False,
                "item_id": "",
                "due_date": "",
            }
            if not (h["library"] or h["call_number"] or h["status"]):
                continue  # 模板空行防御（实抓未见）
            h["available"] = h["status"] in AVAILABLE_STATUS
            holdings.append(h)
    return holdings


def looks_like_isbn(keyword):
    """ISBN 形态判断：去连字符后 13 位（978/979 开头）或 10 位（末位可为 X）。同重庆/深圳口径。"""
    s = str(keyword or "").replace("-", "").strip()
    if len(s) == 13 and s.isdigit():
        return s[:3] in ("978", "979")
    if len(s) == 10 and s[:9].isdigit():
        return s[9].isdigit() or s[9] in "Xx"
    return False


def check_recno(book_id, name=""):
    """book_id 必须是裸 recno（纯数字，NOTES.md）；带前缀/异形直接报错。"""
    s = str(book_id or "").strip()
    if not re.fullmatch(r"\d+", s):
        prefix = f"{name}：" if name else ""
        raise RuntimeError(f"{prefix}book_id 应为纯数字 recno：{book_id}")
    return s
