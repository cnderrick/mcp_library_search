"""大连适配器：大连地区网上联合目录查询系统（SirsiDynix iLink）→ base.py 统一模型。

会话流：GET /uhtbin/cgisirsi/x/x/0/49/（根路径 http://ykt.dl-library.net.cn/ 是
meta-refresh 到此）→ 302 到带 ps token 的「快速检索」首页并落 session_security /
session_number cookie。检索是 POST 表单到首页 searchform 的 action（形如
/uhtbin/cgisirsi/?ps={token}/DALIANLIB/X/123，字段 searchdata1 + srchfield1 +
library + sort_by）。**ps token 每个响应都变**：一律从上一步响应里解析下一步的
form action / hitlist action，绝不硬编码拼 URL；全程同一 CookieJar 串行。

检索语义：源站裸词是**逐字 AND** 宽匹配、无相关度排序（所有字段「三体」实测 27944 条，
首条与题名无关；题名「三体」862 条，前两条亦不相关）。**ASCII 双引号才是短语检索**
（所有字段「"三体"」→ 132 条、题名「"三体"」→ 63 条，均相关）。故检索与详情重检索
一律先按短语下发；短语 0 命中或源站拒答（词含源站索引不收的字符，如罗马数字「Ⅲ」
会回 Error message 页）时退回裸词再试一次。

详情/馆藏没有可直接 GET 的 catkey URL：详情页是 hitlist 表单里「详细资料」按钮
（VIEW^N）POST 到 hitlist action（/X/9）的响应，N 是命中序号（会话内位置）。
catkey 本身不可检索（GENERAL 检索 catkey 实测 0 命中）。因此 book_id = "{catkey}:{题名}"，
get_book_detail / get_holdings 用题名（TI 字段）重检索命中列表、按 catkey 定位序号、
再 POST VIEW^N 取详情页。题名是列表页原值拼串（「题名＋资料类型＋版本＋责任者＋语种」），
整串即便是短语检索也 0 命中，故按候选梯度下发：短语截断题名 → 裸截断题名 → 裸整串
（实测《船舶结构与设备》短语截断题名命中 24 条、目标在第 1 位；见 NOTES）。题名短的候选
（如《上瘾》）命中可到数十条、目标落在第 2 页起，故候选内逐页翻找 catkey（≤5 页）；
**VIEW^N 的 N 是命中集全局序号**（第 2 页第 1 位＝21），页内序号需加页偏移。

数据边界：匿名「馆藏显示」页只到**索书号级**（分馆 + 索书号 + 复本数 + 馆藏类型 +
馆藏位置），无单册条码、无应还日期 → due_date 恒空串。可借口径保守：copy_info
（馆藏分布状况）含「在架上」判 available=True、status="在架上"；仅「馆藏于」等
无明确在架词判 available=False、status 原值照登，不做「馆藏于＝可借」预设。
"""
import http.cookiejar
import html
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from ..base import BookDetail, BookSummary, Holding, SearchPage

_BASE = "http://ykt.dl-library.net.cn"
_ENTRY = _BASE + "/uhtbin/cgisirsi/x/x/0/49/"  # 根路径 meta-refresh 的稳定目标
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
_HEADERS = {"User-Agent": _UA}
_THROTTLE = 4.0  # 秒/host；iLink 会话敏感，从严限速
_PAGE_SIZE = 20  # 源站固定每页 20 条（first_hit/last_hit），无每页条数参数
_DETAIL_MAX_PAGES = 5  # 详情定位翻页上限（每页 20 条 → 最多扫 100 条命中）

# srchfield1 下拉实抓取值（无 ISBN 选项）：
_SRCHFIELD_GENERAL = "GENERAL^SUBJECT^GENERAL^^所有字段"  # 通用检索；ISBN 形态也走这个
_SRCHFIELD_TITLE = "TI^TITLE^SERIES^Title Processing^题名"  # 题名；详情重定位用

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_last_request = 0.0


def _open(req, timeout=25):
    """HTTP 入口：CookieJar 会话 + 4 秒节流，返回 UTF-8 文本。失败抛含馆名的 RuntimeError。

    页面 charset 为 utf-8（HTTP 头在初始重定向页可能标 iso-8859-1，以内容为准），
    统一按 utf-8 解码、errors=replace。
    """
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"大连图书馆请求失败：{e}") from e


def _has_session():
    return any(c.name in ("session_security", "session_number") for c in _jar)


def _reset_session():
    _jar.clear()
    global _last_request
    _last_request = 0.0


def _clean(text):
    """去标签（含 HTML 注释）、&nbsp; 与首尾空白，折叠内部空白，返回纯文本原值。"""
    s = re.sub(r"<[^>]+>", " ", html.unescape(str(text or "")))
    return re.sub(r"\s+", " ", s.replace("\xa0", " ")).strip()


def _year(text):
    m = re.search(r"(?:19|20)\d{2}", str(text or ""))
    return m.group(0) if m else ""


def _is_quoted(keyword):
    """输入是否已自带成对 ASCII 双引号（调用方显式指定短语检索）。"""
    s = str(keyword or "").strip()
    return len(s) >= 2 and s.startswith('"') and s.endswith('"')


def _phrase(keyword):
    """按短语下发：源站裸词是逐字 AND 宽匹配（无相关度），加 ASCII 双引号才是短语检索。
    已自带引号的输入原样保留，不二次包裹。
    """
    s = str(keyword or "").strip()
    return s if _is_quoted(s) else f'"{s}"'


# 列表页题名拼串里的资料类型分隔词（「题名 专著 版本 责任者 语种」）
_TITLE_TYPE_MARK = re.compile(r"\s+(?:专著|期刊|会议录|学位论文|电子资源|音像制品|缩微品|地图|乐谱)")


def _title_variants(title):
    """题名重检索候选梯度：短语截断题名（首选）→ 裸截断题名 → 裸整串 → 短语首段 → 裸首段。

    列表页题名是拼串，源站短语索引只认题名主体——整串即便短语检索实测也 0 命中；
    截断题名若含罗马数字等非索引字符，短语会 0 命中，故用裸词兜底（逐字 AND）。
    老记录无「 专著」等资料类型分隔词（如「上瘾 辛卉著 陈毓华著」），再退到首个空格段。
    """
    t = str(title or "").strip()
    if not t:
        return []
    short = _TITLE_TYPE_MARK.split(t, 1)[0].strip() or t
    out = [_phrase(short), short]
    if t != short:
        out.append(t)
    head = t.split(" ")[0].strip()
    if head and head not in (short, t):
        out += [_phrase(head), head]
    return out


# ---- 页面形态判定（会话失效＝退回「快速检索」首页；结果页含非空/空两种）----
_RESULT_MARK = "目录检索结果"   # 结果页 title（空结果页仍含，靠「没找到所需文献」/总数区分）
_DETAIL_MARK = "馆藏显示"       # 详情页 title


def _is_result_page(text):
    return _RESULT_MARK in (text or "")


def _is_detail_page(text):
    return _DETAIL_MARK in (text or "") or "display_holdings_table" in (text or "")


def _is_entry_page(text):
    """是否退回「快速检索」首页形态（会话失效的判据，区别于源站回 Error 页）。"""
    t = text or ""
    return "快速检索" in t and "searchform" in t


# ---- 从响应解析下一步 form action（ps token 每响应变，绝不硬编码）----
def _searchform_action(text):
    m = re.search(r'<form[^>]*name="searchform"[^>]*action="([^"]+)"', text or "", re.I)
    if not m:
        m = re.search(r'<form[^>]*action="([^"]+)"[^>]*name="searchform"', text or "", re.I)
    return m.group(1) if m else ""


def _hitlist_action(text):
    m = re.search(r'<form[^>]*name="hitlist"[^>]*action="([^"]+)"', text or "", re.I)
    if not m:
        m = re.search(r'<form[^>]*action="([^"]+)"[^>]*name="hitlist"', text or "", re.I)
    return m.group(1) if m else ""


def _hitlist_range(text):
    """结果页 hitlist 表单里的 first_hit/last_hit（当前页命中区间），缺省 1/20。

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
    return (first or 1, last or first + _PAGE_SIZE - 1)


def _abs(url):
    if not url:
        return ""
    return url if url.startswith("http") else _BASE + url


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


@dataclass
class _Holding:
    library: str = ""
    location: str = ""
    call_number: str = ""
    status: str = ""
    available: bool = False
    item_id: str = ""   # 大连匿名视图无单册条码 → 恒空串
    due_date: str = ""  # 匿名视图无应还日期 → 恒空串

    def is_available(self):
        return self.available


# ---- 检索结果页解析 ----
_TOTAL = re.compile(r"检索到\s*(\d+)")
_CKEYS = re.compile(r'keep_ckeys_array\.push\("(\d+)"\)')


def _parse_total(text):
    """总数取 searchsummary「检索到 <em>N</em> 题名」；先清标签再匹配。空结果页无此锚 → 0。"""
    m = re.search(r'<div class="searchsummary">(.*?)</div>', text or "", re.S)
    scope = _clean(m.group(1)) if m else ""
    n = _TOTAL.search(scope)
    return int(n.group(1)) if n else 0


def _find_ckey_position(text, ckey):
    """命中列表里 catkey 的 1-based 序号（VIEW^N 用）；找不到返回 None。"""
    for i, ck in enumerate(_CKEYS.findall(text or ""), 1):
        if ck == str(ckey):
            return i
    return None


_HIT_SPLIT = re.compile(r'<ul class="hit_list_row')


def _dd(block, cls):
    m = re.search(r'<dd class="' + re.escape(cls) + r'"[^>]*>(.*?)</dd>', block, re.S)
    return _clean(m.group(1)) if m else ""


def _parse_hits(text):
    """结果页 → _Book 列表。每条 hit 一个 <ul class="hit_list_row"> 块。"""
    books = []
    for blk in _HIT_SPLIT.split(text or "")[1:]:
        ck = re.search(r"put_keepremove_button\('(\d+)'", blk)
        if not ck:
            continue
        ckey = ck.group(1)
        title = _dd(blk, "title")
        yr = re.search(r'publishing_date_label"[^>]*>[^<]*</dt>\s*<dd[^>]*>(.*?)</dd>', blk, re.S)
        books.append(_Book(
            record_id=f"{ckey}:{title}",
            title=title,
            author=_dd(blk, "author"),
            publisher=_clean_publisher(_dd(blk, "publisher")),
            publish_year=_year(_clean(yr.group(1)) if yr else ""),
            call_number=_dd(blk, "call_number"),
            availability_summary=_dd(blk, "holdings_statement"),
        ))
    return books


def _clean_publisher(text):
    """出版者若形如「重庆 重庆出版社 2016」拆出纯社名；结果页出版者常为空，原值照登。"""
    s = str(text or "").strip()
    return s


# ---- 详情页解析 ----
def _detail_field(text, label):
    """简要展示 dl 里首个 label 的 dd 值（题名/著者/出版者/出版日期/ISBN…）。"""
    m = re.search(
        r"<dt[^>]*>\s*" + re.escape(label) + r"[:：]?\s*</dt>\s*<dd[^>]*>(.*?)</dd>",
        text or "", re.S)
    return _clean(m.group(1)) if m else ""


_HOLDINGS_TABLE = re.compile(r'id="display_holdings_table".*?</table>', re.S)
_COPY_INFO = re.compile(r'<dd class="copy_info">(.*?)</dd>', re.S)


def _copy_info(text):
    m = _COPY_INFO.search(text or "")
    return _clean(m.group(1)) if m else ""


def _holdings_rows(text):
    """display_holdings_table → [{library, call_number, copies, item_type, location}]。

    表按分馆分组：th.holdingsheader[align=left] 是分馆名表头，其后 td.holdingslist
    数据行是 [索书号, 复本数, 馆藏类型, 馆藏位置]。
    """
    m = _HOLDINGS_TABLE.search(text or "")
    if not m:
        return []
    rows = []
    cur_lib = ""
    for tr in re.finditer(r"<tr\b.*?</tr>", m.group(0), re.S):
        seg = tr.group(0)
        lib = re.search(r'<th[^>]*class="holdingsheader"[^>]*align="left"[^>]*>(.*?)</th>', seg, re.S)
        if not lib:
            lib = re.search(r'<th[^>]*align="left"[^>]*class="holdingsheader"[^>]*>(.*?)</th>', seg, re.S)
        if lib:
            cur_lib = _clean(lib.group(1))
            continue
        tds = [_clean(x) for x in re.findall(r"<td\b[^>]*>(.*?)</td>", seg, re.S)]
        tds = [t for t in tds if t != ""]
        if len(tds) >= 4:
            rows.append({
                "library": cur_lib,
                "call_number": tds[0],
                "copies": tds[1],
                "item_type": tds[2],
                "location": tds[3],
            })
    return rows


def _availability_from_copy_info(copy_info):
    """copy_info 含「在架上」→ (status="在架上", available=True)；否则 (原值短语, False)。

    词表以实抓为准：明确在架词只有「在架上」；「馆藏于」等仅表位置、不表可借，
    保守判 False，status 原值照登。
    """
    ci = copy_info or ""
    if "在架上" in ci:
        return "在架上", True
    if "馆藏于" in ci:
        return "馆藏于", False
    # 词表外：原值照登、保守不可借
    return (ci.strip().rstrip(".") if ci.strip() else ""), False


def _parse_holdings(text):
    """详情页 → _Holding 列表（索书号级）。available 由 copy_info 的在架词判定。"""
    status, available = _availability_from_copy_info(_copy_info(text))
    holdings = []
    for r in _holdings_rows(text):
        holdings.append(_Holding(
            library=r["library"],
            location=r["location"],
            call_number=r["call_number"],
            status=status,
            available=available,
            item_id="",
            due_date="",
        ))
    return holdings


def _split_book_id(book_id):
    """book_id 形如 "{catkey}:{题名}"；按首个冒号拆（题名可含冒号）。"""
    s = str(book_id or "")
    ckey, sep, title = s.partition(":")
    if not sep or not ckey.strip():
        raise RuntimeError(f"大连图书馆：book_id 格式应为 catkey:题名：{book_id}")
    return ckey.strip(), title.strip()


class _Client:
    """iLink 会话 client：ps token 逐步解析、CookieJar 串行，把 HTML 解析成 vendor 同形结构。"""

    def _get_entry(self):
        """GET 会话入口页，返回「快速检索」首页 HTML（含 fresh searchform action）。"""
        return _open(urllib.request.Request(_ENTRY, headers=_HEADERS))

    def _post(self, action, fields):
        data = urllib.parse.urlencode(fields).encode()
        return _open(urllib.request.Request(_abs(action), data=data, headers=_HEADERS))

    def _search_once(self, keyword, srchfield):
        """入口页取 fresh searchform action → POST 检索，返回结果页 HTML。"""
        entry = self._get_entry()
        action = _searchform_action(entry)
        if not action:
            return ""  # 入口页形态异常 → 交给上层判定/重建
        return self._post(action, {
            "searchdata1": keyword,
            "srchfield1": srchfield,
            "library": "ALL",
            "sort_by": "ANY",
        })

    def _jump(self, result_page, page):
        """从结果页解析 hitlist action → POST form_type=JUMP^{start} 翻页。"""
        action = _hitlist_action(result_page)
        if not action:
            return ""
        start = (page - 1) * _PAGE_SIZE + 1
        return self._post(action, {
            "first_hit": "1",
            "last_hit": str(_PAGE_SIZE),
            "form_type": f"JUMP^{start}",
        })

    def _view(self, result_page, position):
        """从结果页解析 hitlist action → POST VIEW^{position}=详细资料 取详情页。

        **position 是命中集的全局序号**（跨页累计，第 2 页第 1 位＝21），不是页内序号——
        实测页内序号会取到别页记录上；first_hit/last_hit 按当前页表单原值回传（不影响 N）。
        """
        action = _hitlist_action(result_page)
        if not action:
            return ""
        first, last = _hitlist_range(result_page)
        return self._post(action, {
            "first_hit": str(first),
            "last_hit": str(last),
            "form_type": "",
            f"VIEW^{position}": "详细资料",
        })

    # ---- 原语：search ----
    def search(self, keyword, page=1, limit=20):
        # iLink 无 ISBN 专用字段；ISBN 形态与通用关键词统一走 GENERAL（所有字段）
        srchfield = _SRCHFIELD_GENERAL
        query = _phrase(keyword)
        text = self._search_once(query, srchfield)
        if not _is_result_page(text):
            _reset_session()  # 会话失效：退回入口/异常 → 重建一次再试
            text = self._search_once(query, srchfield)
        total = _parse_total(text) if _is_result_page(text) else 0
        if (not _is_result_page(text) or total == 0) and query != str(keyword or "").strip() \
                and not _is_entry_page(text):
            # 短语被源站拒答（含非索引字符回 Error 页）或 0 命中 → 退回裸词再试一次
            bare = self._search_once(keyword, srchfield)
            if _is_result_page(bare) and _parse_total(bare) > 0:
                query, text, total = keyword, bare, _parse_total(bare)
        if not _is_result_page(text):
            raise RuntimeError("大连图书馆：检索未返回结果页（重复失败，可能会话无法建立）")
        if page > 1 and total > 0:
            jumped = self._jump(text, page)
            if _is_result_page(jumped):
                text = jumped
            else:
                _reset_session()
                text2 = self._search_once(query, srchfield)
                jumped = self._jump(text2, page) if _is_result_page(text2) else ""
                if not _is_result_page(jumped):
                    raise RuntimeError("大连图书馆：翻页失败（重复失败，可能会话无法建立）")
                text = jumped
        total_pages = max(1, math.ceil(total / _PAGE_SIZE))
        return _SearchResult(
            success=True,
            error="",
            statistics={
                "total_results": total,
                "page": page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
            },
            books=_parse_hits(text),
        )

    # ---- 详情/馆藏共用：题名候选梯度重检索 → catkey 定位（可翻页）→ VIEW^N ----
    def _detail_attempt(self, ckey, title):
        for query in _title_variants(title):
            text = self._search_once(query, _SRCHFIELD_TITLE)
            if not _is_result_page(text):
                if _is_entry_page(text):
                    return None  # 会话失效：交给上层重建后再试
                continue  # 源站拒答该候选（含非索引字符回 Error 页）→ 换下一个候选
            # 命中多于首页时逐页找 catkey（题名短的候选常把目标排到后面几页）
            pages = min(_DETAIL_MAX_PAGES,
                        max(1, math.ceil(_parse_total(text) / _PAGE_SIZE)))
            for page in range(1, pages + 1):
                if page > 1:
                    jumped = self._jump(text, page)
                    if not _is_result_page(jumped):
                        break  # 翻页失败：换下一个候选
                    text = jumped
                pos = _find_ckey_position(text, ckey)   # 页内序号
                if pos is None:
                    continue  # 该页没有目标 → 继续翻页
                # VIEW^N 取全局序号（跨页累计），页内序号需加页偏移
                detail = self._view(text, (page - 1) * _PAGE_SIZE + pos)
                if _is_detail_page(detail):
                    return detail
        return None

    def _fetch_detail(self, ckey, title):
        detail = self._detail_attempt(ckey, title)
        if detail is None:
            _reset_session()  # 会话失效或定位失败 → 重建一次再试
            detail = self._detail_attempt(ckey, title)
            if detail is None:
                raise RuntimeError(
                    "大连图书馆：详情获取失败（重复失败，可能会话无法建立或记录不可定位）")
        return detail

    def get_book_detail(self, book_id):
        ckey, title = _split_book_id(book_id)
        if not title:
            raise RuntimeError(f"大连图书馆：book_id 缺少题名，无法重检索定位：{book_id}")
        text = self._fetch_detail(ckey, title)
        t = _detail_field(text, "题名") or title
        rows = _holdings_rows(text)
        return _Book(
            record_id=book_id,
            title=t,
            author=_detail_field(text, "著者"),
            publisher=_detail_field(text, "出版者"),
            publish_year=_year(_detail_field(text, "出版日期")),
            isbn=_detail_field(text, "ISBN"),
            call_number=rows[0]["call_number"] if rows else "",
            summary="",  # 匿名详情页无内容提要字段
        )

    def get_holdings(self, book_id):
        ckey, title = _split_book_id(book_id)
        if not title:
            raise RuntimeError(f"大连图书馆：book_id 缺少题名，无法重检索定位：{book_id}")
        text = self._fetch_detail(ckey, title)
        return _parse_holdings(text)


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索馆藏。上游报错抛 RuntimeError。

    源站固定每页 20 条、无每页条数参数，limit 不生效（原值返回源站页）。
    """
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"大连图书馆搜索失败：{result.error}")

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
    """指定图书的索书号级馆藏：分馆、馆藏位置、索书号、状态原值。

    匿名视图无单册条码与应还日期（due_date 恒空串）。可借口径保守：copy_info
    含「在架上」判可借，仅「馆藏于」等判不可借（only_available=True 时后者被过滤）。
    """
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
        # 契约：已借出且带单册 item_id 才查归还时间；大连单册无 item_id，真网路径不触发
        if not available and getattr(h, "item_id", ""):
            item["due_date"] = _client.get_return_date(h.item_id)
        items.append(item)
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(book_id: str) -> BookDetail:
    """指定图书的完整详情：书名、作者、出版社、出版年、ISBN、索书号、内容简介。"""
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
