"""SirsiDynix iLink 页面解析（甘肃三站实测，2026-10-03）。

iLink 的检索/详情页与大连同构（同一产品线）：结果页 title「目录检索结果」、
详情页 title「馆藏显示」、`keep_ckeys_array.push` 记 catkey、`hit_list_row` 分包、
`dd.title/author/publisher/call_number/holdings_statement` 取字段、`copy_info` 判可借。
**甘肃与大连的唯一结构差异**：馆藏表没有 `id="display_holdings_table"`，
故 `holdings_rows` 不再靠表 id 锚定，改为全页扫描 `td.holdingslist` 数据行、
用单枚 `th.holdingsheader[align=left]`「分馆表头行」跟踪当前分馆。

字段侦察结论见 tests/fixtures/{gansu_prov,longnan,gannan}/NOTES.md。
"""
import html
import re

# ---- 页面形态判定（会话失效＝退回「快速检索」首页；结果页含非空/空两种）----
_RESULT_MARK = "目录检索结果"   # 结果页 title（空结果页仍含，靠「没找到所需文献」/总数区分）
_DETAIL_MARK = "馆藏显示"       # 详情页 title


def clean(text) -> str:
    """去标签（含 HTML 注释）、&nbsp; 与首尾空白，折叠内部空白，返回纯文本原值。"""
    s = re.sub(r"<[^>]+>", " ", html.unescape(str(text or "")))
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def year(text) -> str:
    m = re.search(r"(?:19|20)\d{2}", str(text or ""))
    return m.group(0) if m else ""


def is_result_page(text) -> bool:
    return _RESULT_MARK in (text or "")


def is_detail_page(text) -> bool:
    t = text or ""
    return _DETAIL_MARK in t or "display_holdings_table" in t


def is_entry_page(text) -> bool:
    """是否退回「快速检索」首页形态（会话失效的判据，区别于源站回 Error 页）。"""
    t = text or ""
    return "快速检索" in t and "searchform" in t


# ---- 从响应解析下一步 form action（ps token 每响应变，绝不硬编码）----
def searchform_action(text) -> str:
    m = re.search(r'<form[^>]*name="searchform"[^>]*action="([^"]+)"', text or "", re.I)
    if not m:
        m = re.search(r'<form[^>]*action="([^"]+)"[^>]*name="searchform"', text or "", re.I)
    return m.group(1) if m else ""


def hitlist_action(text) -> str:
    m = re.search(r'<form[^>]*name="hitlist"[^>]*action="([^"]+)"', text or "", re.I)
    if not m:
        m = re.search(r'<form[^>]*action="([^"]+)"[^>]*name="hitlist"', text or "", re.I)
    return m.group(1) if m else ""


def sort_by_value(text) -> str:
    """入口页 hidden sort_by 原值（甘肃实测 TI；缺省交调用方兜底）。"""
    m = re.search(r'name="sort_by"[^>]*value="([^"]*)"', text or "")
    if not m:
        m = re.search(r'value="([^"]*)"[^>]*name="sort_by"', text or "")
    return m.group(1) if m else ""


def hitlist_range(text, page_size: int):
    """结果页 hitlist 表单里的 first_hit/last_hit（当前页命中区间），缺省 1/page_size。

    翻页后区间随页变（第 2 页＝21/40），VIEW^N 的 N 是**当前页内**序号，
    故必须原样回传当前页区间，否则定位到别页的记录上。
    """
    t = text or ""
    out = []
    for field in ("first_hit", "last_hit"):
        m = re.search(r'name="' + field + r'"[^>]*value="(\d+)"', t) \
            or re.search(r'value="(\d+)"[^>]*name="' + field + r'"', t)
        out.append(int(m.group(1)) if m else 0)
    first, last = out
    return (first or 1, last or first + page_size - 1)


def abs_url(base, url) -> str:
    if not url:
        return ""
    return url if url.startswith("http") else base + url


# ---- 检索语义：裸词＝逐字 AND，ASCII 双引号＝短语检索（同大连）----
def is_quoted(keyword) -> bool:
    s = str(keyword or "").strip()
    return len(s) >= 2 and s.startswith('"') and s.endswith('"')


def phrase(keyword) -> str:
    """按短语下发：裸词是逐字 AND 宽匹配、无相关度，加 ASCII 双引号才是短语检索。
    已自带引号的输入原样保留，不二次包裹。
    """
    s = str(keyword or "").strip()
    return s if is_quoted(s) else f'"{s}"'


# 列表页题名拼串里的资料类型分隔词（「题名 专著 版本 责任者 语种」）
_TITLE_TYPE_MARK = re.compile(r"\s+(?:专著|期刊|会议录|学位论文|电子资源|音像制品|缩微品|地图|乐谱)")


def title_variants(title) -> list:
    """题名重检索候选梯度：短语截断题名 → 裸截断题名 → 裸整串 → 短语首段 → 裸首段。"""
    t = str(title or "").strip()
    if not t:
        return []
    short = _TITLE_TYPE_MARK.split(t, 1)[0].strip() or t
    out = [phrase(short), short]
    if t != short:
        out.append(t)
    head = t.split(" ")[0].strip()
    if head and head not in (short, t):
        out += [phrase(head), head]
    return out


# ---- 检索结果页解析 ----
_TOTAL = re.compile(r"检索到\s*(\d+)")
_CKEYS = re.compile(r'keep_ckeys_array\.push\("(\d+)"\)')
_HIT_SPLIT = re.compile(r'<ul class="hit_list_row')


def parse_total(text) -> int:
    """总数取 searchsummary「检索到 <em>N</em> 题名」；先清标签再匹配。空结果页无此锚 → 0。"""
    m = re.search(r'<div class="searchsummary">(.*?)</div>', text or "", re.S)
    scope = clean(m.group(1)) if m else ""
    n = _TOTAL.search(scope)
    return int(n.group(1)) if n else 0


def find_ckey_position(text, ckey):
    """命中列表里 catkey 的 1-based 序号（VIEW^N 用）；找不到返回 None。"""
    for i, ck in enumerate(_CKEYS.findall(text or ""), 1):
        if ck == str(ckey):
            return i
    return None


def _dd(block, cls) -> str:
    m = re.search(r'<dd class="' + re.escape(cls) + r'"[^>]*>(.*?)</dd>', block, re.S)
    return clean(m.group(1)) if m else ""


def parse_hits(text) -> list:
    """结果页 → 书本 dict 列表。每条 hit 一个 `<ul class="hit_list_row">` 块。"""
    books = []
    for blk in _HIT_SPLIT.split(text or "")[1:]:
        ck = re.search(r"put_keepremove_button\('(\d+)'", blk)
        if not ck:
            continue
        ckey = ck.group(1)
        title = _dd(blk, "title")
        yr = re.search(r'publishing_date_label"[^>]*>[^<]*</dt>\s*<dd[^>]*>(.*?)</dd>', blk, re.S)
        books.append({
            "catkey": ckey,
            "record_id": f"{ckey}:{title}",
            "title": title,
            "author": _dd(blk, "author"),
            "publisher": _dd(blk, "publisher"),
            "publish_year": year(clean(yr.group(1)) if yr else ""),
            "call_number": _dd(blk, "call_number"),
            "availability_summary": _dd(blk, "holdings_statement"),
        })
    return books


# ---- 详情页解析 ----
def detail_field(text, label) -> str:
    """简要展示 dl 里首个 label 的 dd 值（题名/著者/出版者/出版日期/ISBN…）。"""
    m = re.search(
        r"<dt[^>]*>\s*" + re.escape(label) + r"[:：]?\s*</dt>\s*<dd[^>]*>(.*?)</dd>",
        text or "", re.S)
    return clean(m.group(1)) if m else ""


_COPY_INFO = re.compile(r'<dd class="copy_info">(.*?)</dd>', re.S)


def copy_info(text) -> str:
    m = _COPY_INFO.search(text or "")
    return clean(m.group(1)) if m else ""


_ALL_LIB_HEADERS = re.compile(r'<th[^>]*class="holdingsheader"[^>]*>(.*?)</th>', re.S)


def holdings_rows(text) -> list:
    """→ [{library, call_number, copies, item_type, location}]。

    甘肃 iLink 馆藏表无 `id`，全页扫描 `<tr>`：
    - 含 `td.holdingslist` 的为数据行（列序：索书号 / 复本号 / 馆藏类型 / 馆藏位置）；
      后续复本的索书号格是 `&nbsp;`，沿用上一行的索书号（分馆分组内）。
    - 恰好一枚 `th.holdingsheader` 的行是分馆表头（列头行有多枚），取其文本为当前分馆。
    """
    rows = []
    cur_lib = ""
    last_call = ""
    for tr in re.finditer(r"<tr\b.*?</tr>", text or "", re.S):
        seg = tr.group(0)
        if 'class="holdingslist"' not in seg:
            ths = _ALL_LIB_HEADERS.findall(seg)
            if len(ths) == 1:
                name = clean(ths[0])
                if name:
                    cur_lib = name
            continue
        tds = [clean(x) for x in re.findall(r"<td\b[^>]*>(.*?)</td>", seg, re.S)]
        if len(tds) < 4:
            continue
        call = tds[0] or last_call
        if tds[0]:
            last_call = tds[0]
        rows.append({
            "library": cur_lib,
            "call_number": call,
            "copies": tds[1],
            "item_type": tds[2],
            "location": tds[3],
        })
    return rows


def availability_from_copy_info(ci):
    """copy_info 含「在架上」→ (status="在架上", available=True)；否则 (原值短语, False)。

    词表以实抓为准：明确在架词只有「在架上」；「馆藏于」等仅表位置、不表可借，
    保守判 False，status 原值照登。词表外文案同样原值照登、保守 False。
    """
    s = ci or ""
    if "在架上" in s:
        return "在架上", True
    if "馆藏于" in s:
        return "馆藏于", False
    return (s.strip().rstrip(".") if s.strip() else ""), False
