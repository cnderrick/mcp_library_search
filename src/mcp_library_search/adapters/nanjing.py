"""南京适配器：金陵图书馆联合目录（JL:）＋ 南京图书馆（NJL01:）双源合并。

金陵源＝汇文 uopac 区域联合 OPAC（uopac.jllib.cn，金陵运营，覆盖金陵＋12 区馆）；
南图源＝Ex Libris ALEPH（opac.jslib.org.cn，江苏省图，走 `aleph/` 家族原语）。
book_id 形态：JL:{uopac 数字 id} / NJL01:{doc_number}；跨源同 ISBN 命中合成复合
id（成员按优先级 JL > NJL01 以 + 连接，书目字段取 JL 成员原值）。
**向后兼容**：0.4.0 已上线的裸数字 book_id（无前缀）一律视为 JL 成员路由
（兼容垫片），搜索新返回的 book_id 一律带前缀。

金陵侧结构见 tests/fixtures/nanjing/NOTES.md；南图 ALEPH 侧的库代码表、会话形态与
两处坑（`doc_library` 与 `FIND-BASE` 可不同、item-global 的 `sub_library` 不能省略）
见 tests/fixtures/nanjing_prov/NOTES.md。

金陵自研 PHP OPAC(opac.jllib.cn/opac/*)整体登录墙(302 → login.php?
msg=login_to_continue,连根路径 JS 跳转的 presearch.php 也锁),匿名不可用;
其官网首页「馆际借阅」外链的 uopac 联合目录匿名全通、无 AES 反爬:

- 检索 GET /uopac/s/search_result.action?q=&meta=&page=:meta 20 任意/14 ISBN,
  真实总数,每页固定 20(limit 对源站无效),分面 fkey=facet_libs&fval=JL 可锁
  金陵(当前不启用,全市联合口径);
- 详情 GET /uopac/s/detail.action?id=:dl.booklist 字段,提要文摘附注=简介,
  无索书号字段(中图法分类号不冒充,call_number 恒空串);
- 馆藏:详情页每持有馆一个 loca_XX tab,span#data 相对 URL 经
  ajax_holding.action 由 uopac 服务端代理成员馆 libsys_view.php(金陵自站虽
  锁登录,代理路径匿名可取;裸请求与带会话逐字节相同 → 客户端完全无状态)。

金陵 ISBN 索引按存储原样字符串前缀匹配且各馆存储带/不带连字符不一 → ISBN 形态
关键词去连字符后每数字间插 `*` 走 meta=14(通配实证,子序列等长即数字全等)。
状态词表:「可借」→ available=True;「借出-应还日期：X」→ False+due_date;
词表外保守 False,原值照登。
"""
import html
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace

from .. import aleph
from ..aleph import AlephConfig
from ..aleph import CaptchaError
from .base import BookDetail, BookSummary, Holding, SearchPage

_BASE = "http://uopac.jllib.cn"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA}
_THROTTLE = 4.0  # 秒/host,按 spec 保守限速
_TIMEOUT = 90    # 秒;源站偶发慢响应/传输中途停顿(侦察与冒烟各实测一次),放宽
_PAGE_SIZE = 20  # 源站固定每页条数,无参数可调

_last_request = 0.0


def _open(req, timeout=_TIMEOUT, retries=1):
    """HTTP 入口:无状态(源站匿名可通,无需 Cookie)+ 4 秒节流,返回文本。

    失败抛含馆名的 RuntimeError。金陵源站偶发 chunked 传输中途停顿(≥60 秒后超时,
    NOTES.md 记「重试即好」)——网络类错误默认重试一次(每次重试照常节流);
    HTTP 状态错误是确定性的,不重试。
    """
    global _last_request
    last = None
    for _ in range(retries + 1):
        wait = _THROTTLE - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"金陵图书馆请求失败：{e}") from e
        except (urllib.error.URLError, OSError) as e:
            last = e
    raise RuntimeError(f"金陵图书馆请求失败：{last}") from last


# ---- 双源配置与归并口径 ----

# 南图源：ALEPH 家族。检索库、馆藏库、book_id 前缀都用 NJL01（中文文献库）。
# 验证码墙按 IP、按 host 独立封禁（解南图不解天津），解封指引只列本 host。
_PROV = AlephConfig(
    source="NJL01", name_cn="南京图书馆", base_url="https://opac.jslib.org.cn",
    unblock_urls="https://opac.jslib.org.cn/F/（南京图书馆）", throttle=_THROTTLE,
    # 南图实测：year/volume/sub_library 可留空但不能整个省略（否则返回错误页）
    item_global_all_params=True,
)
_SOURCE_PRIORITY = ("JL", "NJL01")   # 市馆 > 省馆，同杭州口径（HZ > ZJ）
_SOURCE_NAMES = {"JL": "金陵图书馆", "NJL01": "南京图书馆"}


def _looks_like_isbn(keyword):
    """ISBN 形态判断:去连字符后 13 位(978/979 开头)或 10 位(末位可为 X)。同深圳口径。"""
    s = str(keyword or "").replace("-", "").strip()
    if len(s) == 13 and s.isdigit():
        return s[:3] in ("978", "979")
    if len(s) == 10 and s[:9].isdigit():
        return s[9].isdigit() or s[9] in "Xx"
    return False


def _isbn_wildcard(keyword):
    """ISBN → 数字间插 * 的通配查询(如 9*7*8*7*…)。

    ISBN 索引是存储原样前缀匹配、各馆连字符形态不一(NOTES.md 实证),通配
    子序列匹配下等长即数字全等,* 只吸收连字符;X 校验位统一大写。
    """
    digits = re.sub(r"[^0-9Xx]", "", str(keyword)).upper()
    return "*".join(digits)


def _clean(text):
    """去标签、&nbsp; 与首尾空白,返回纯文本原值。"""
    s = re.sub(r"<[^>]+>", "", html.unescape(str(text or "")))
    return s.replace("\xa0", " ").strip()


def _year(text):
    m = re.search(r"(?:19|20)\d{2}", str(text or ""))
    return m.group(0) if m else ""


def _clean_publisher(text):
    """出版发行项形如「重庆:重庆出版社,2016」,拆出纯出版社名。同深圳口径。"""
    s = re.sub(r",?\s*(?:19|20)\d{2}\S*$", "", str(text or "")).strip()
    if re.search(r"[:：]", s):
        s = re.split(r"[:：]", s, maxsplit=1)[1].strip()
    return s


def _check_jl_id(book_id):
    """金陵成员 id 是 uopac 原生数字（源前缀已由 _split_book_id 剥掉）。"""
    s = str(book_id or "").strip()
    if not s.isdigit():
        raise RuntimeError(f"金陵图书馆：book_id 格式应为 uopac 数字 id：{book_id}")
    return s


# ---- 跨源 ISBN 归并（口径同天津/杭州适配器） ----

def _norm_isbn(isbn):
    """ISBN 归一：去连字符与空白并转大写；非 ISBN 形态返回空串（不参与归并）。"""
    s = re.sub(r"[\s-]", "", str(isbn or "")).upper()
    return s if _looks_like_isbn(s) else ""


def _merge_books(per_source):
    """跨源按归一 ISBN 归并：{source: [ _Book ]} → 归并后的 _Book 列表。

    口径（天津/杭州口径的南京变体——差别在源内重复与排列）：
    - **只有跨源命中的 ISBN 才合并**：该 ISBN 出现在两个源里才合成一条复合
      record_id（成员按源优先级 JL > NJL01 排列，源内保持原顺序），条目落在
      首个成员的位置上。
    - 南京不采用天津的「同一 ISBN 每源至多留一条」：金陵是联合目录，同一本书
      各成员馆常各编一条记录（实抓 20 条里 3 组同 ISBN），只留首条会把其余记录
      的馆藏一并丢掉。单源重复因此逐条原位返回，一条不丢。
    - 无 ISBN（含脏值）不参与归并，原位保留——检索结果顺序即各源的相关度顺序，
      不把任何条目挪到末尾（天津口径是分组前置、散条后置）。
    - 复合条目书目字段取优先级最高成员的原值。
    """
    flat = []     # 按源优先级展平的原始顺序
    for source in _SOURCE_PRIORITY:
        flat.extend(per_source.get(source, []))
    # 归一键 = 出现在 ≥2 个源里的 ISBN；单源重复不算
    sources_of = {}
    for b in flat:
        key = _norm_isbn(b.isbn)
        if key:
            sources_of.setdefault(key, set()).add(b.record_id.split(":")[0])
    merge_keys = {k for k, seen in sources_of.items() if len(seen) > 1}

    groups = {}
    for b in flat:
        key = _norm_isbn(b.isbn)
        if key in merge_keys:
            groups.setdefault(key, []).append(b)

    merged = []
    emitted = set()
    for b in flat:
        key = _norm_isbn(b.isbn)
        if key not in merge_keys:
            merged.append(b)        # 无 ISBN 与单源重复：原位原样
            continue
        if key in emitted:
            continue                # 已随复合条目输出
        emitted.add(key)
        members = groups[key]
        merged.append(members[0] if len(members) == 1 else
                      replace(members[0],
                              record_id="+".join(m.record_id for m in members)))
    return merged


def _split_book_id(book_id):
    """复合/单成员 book_id → 按优先级排序的 [(source, record_id)]；形态非法即抛错。

    兼容垫片：无前缀的裸数字 id 一律视为 JL 成员——0.4.0 已上线的 nanjing
    book_id 是裸 uopac 数字 id，必须继续可用（南图成员一律带 NJL01: 前缀，
    从未以裸形态发布过）。
    """
    members = []
    for part in str(book_id or "").split("+"):
        part = part.strip()
        source, sep, rid = part.partition(":")
        if not sep:
            if part.isdigit():
                source, rid = "JL", part
            else:
                raise RuntimeError(f"金陵图书馆：未知 book_id 形态：{book_id}")
        if not rid or source not in _SOURCE_PRIORITY:
            raise RuntimeError(f"金陵图书馆：未知 book_id 形态：{book_id}")
        members.append((source, rid))
    return sorted(members, key=lambda m: _SOURCE_PRIORITY.index(m[0]))


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
    item_id: str = ""
    due_date: str = ""

    def is_available(self):
        return self.available


# ---------- 检索结果页 ----------

_RESULT_MARK = '<div id="found">'
_FOUND_TOTAL = re.compile(r'有\s*<font color="red">(\d+)</font>\s*项')
_NUM_PAGES = re.compile(
    r'<font color=red>(\d+)</font>&nbsp; / &nbsp;<font color=black>(\d+)</font>')
_BLOCKS = re.compile(r'<div class="searchcontent"\s*>(.*?)<div class="clear">', re.S)
# 裸请求(无 Cookie)时 Tomcat 把 action URL 重写为 detail.action;jsessionid=…?id=
# (NOTES.md「jsessionid URL 重写」)→ 容忍两者之间的任意段
_ENTRY_LINK = re.compile(r'detail\.action[^?]*\?id=(\d+)">(.*?)</a>', re.S)
_META_LINE = re.compile(r'<p style=color:#666;>(.*?)</p>', re.S)
_LIBS_LINE = re.compile(r'所在馆：</strong>(.*?)</p>', re.S)


def _split_meta_line(line):
    """元信息行「责任者 / 出版社 / ISBN / 出版年」→ (author, publisher, year, isbn)。

    固定末三段为出版社/ISBN/年,其余拼回责任者(责任者本身可能含斜杠);
    不足四段时防御性退化为只有责任者(ISBN 空串)。
    """
    parts = [_clean(p) for p in str(line or "").split("/")]
    if len(parts) < 4:
        return (_clean(line), "", "", "")
    author = "/".join(parts[:-3]).strip()
    publisher = parts[-3]
    year = _year(parts[-1])
    return author, publisher, year, parts[-2]


def _parse_libs(raw):
    """所在馆块 → 馆名列表(名称间是空白与 &nbsp;)。"""
    text = html.unescape(str(raw or "")).replace("\xa0", " ")
    text = re.sub(r"<[^>]+>", "", text)
    return [n for n in text.split() if n]


def _parse_search(text):
    """结果页 → {"books", "total_results", "total_pages"}。

    ISBN 从元信息行取原值（供跨源归并）；record_id 前缀 JL: 由调用方补。
    """
    m = _FOUND_TOTAL.search(text)
    total = int(m.group(1)) if m else None
    m = _NUM_PAGES.search(text)
    if m:
        total_pages = int(m.group(2))
    else:
        # 空结果页无 num 分页区 → 按源站固定每页 20 条回退
        total_pages = math.ceil(total / _PAGE_SIZE) if total else 0
    books = []
    for block in _BLOCKS.findall(text):
        link = _ENTRY_LINK.search(block)
        if not link:
            continue
        rid, title = link.group(1), _clean(link.group(2))
        meta = _META_LINE.search(block)
        author, publisher, year, isbn = _split_meta_line(meta.group(1) if meta else "")
        libs = _LIBS_LINE.search(block)
        names = _parse_libs(libs.group(1)) if libs else []
        books.append(_Book(
            record_id=f"JL:{rid}",
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


def _parse_detail(text):
    """详情页 → 书目字段 dict。无索书号字段,call_number 恒空串(NOTES.md)。"""
    fields = {}
    for dt, dd in _DD.findall(text):
        fields[_clean(dt).rstrip("：:")] = _clean(dd)
    title, _, author = fields.get("题名/责任者", "").partition("/")
    publish = fields.get("出版发行项", "")
    return {
        "title": title.strip(),
        "author": author.strip(),
        "publisher": _clean_publisher(publish),
        "publish_year": _year(publish),
        "isbn": fields.get("ISBN", ""),
        "call_number": "",
        "summary": fields.get("提要文摘附注", ""),
    }


def _parse_tabs(text):
    """详情页馆藏 tab → [(馆名, ajax 绝对 URL)]。span#data 是相对 URL,& 可能
    以 &amp; 出现(页面 JS 有 replace 防御),统一 unescape。"""
    names = {code: _clean(name) for code, name in _TAB_NAME.findall(text)}
    tabs = []
    for code, rel in _TAB_DATA.findall(text):
        rel = html.unescape(rel).strip()
        if "ajax_holding.action" not in rel:
            continue
        tabs.append((names.get(code, code), f"{_BASE}/uopac/s/{rel}"))
    return tabs


# ---------- 馆藏表(ajax_holding 响应) ----------

_ITEM_ROW = re.compile(
    r'<tr align="center" bgcolor="#FFFFFF">\s*'
    r'<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*'
    r'<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>',
    re.S,
)
_DUE_DATE = re.compile(r"应还日期[：:]\s*(\d{4}-\d{2}-\d{2})")


def _parse_holding_rows(text, library):
    """馆藏表 → 单册级 _Holding 列表。列序:索书号/条码号/年卷期/校区/馆藏地/状态。

    条码号与年卷期无契约字段,舍弃;location=校区+馆藏地(空格连接,空段跳过)。
    状态词表:「可借」→ True;其余(含「借出-应还日期：X」与词表外)保守 False,
    原值照登;应还日期仅认「应还日期：YYYY-MM-DD」标准形态,否则空串不猜。
    """
    holdings = []
    for callno, _barcode, _issue, campus, loc, status in _ITEM_ROW.findall(text):
        status = _clean(status)
        m = _DUE_DATE.search(status)
        holdings.append(_Holding(
            library=library,
            location=" ".join(x for x in (_clean(campus), _clean(loc)) if x),
            call_number=_clean(callno),
            status=status,
            available=(status == "可借"),
            due_date=m.group(1) if m else "",
        ))
    return holdings


class _Client:
    """双源客户端：JL＝金陵 uopac 联合目录，NJL01＝南京图书馆 ALEPH 家族原语。

    把两源原始响应解析成与 vendor 对象同形的结构，再按 ISBN 归并成城市级结果。
    """

    def _fetch(self, url):
        return _open(urllib.request.Request(url, headers=_HEADERS))

    # ---- JL（金陵 uopac 联合目录） ----

    def _search_jl(self, keyword, page=1, limit=20):
        if _looks_like_isbn(keyword):
            params = {"q": _isbn_wildcard(keyword), "meta": "14", "page": str(page)}
        else:
            params = {"q": str(keyword or ""), "meta": "20", "page": str(page)}
        url = f"{_BASE}/uopac/s/search_result.action?" + urllib.parse.urlencode(params)
        text = self._fetch(url)
        if _RESULT_MARK not in text:
            raise RuntimeError("金陵图书馆：检索未返回结果页（可能被拦截或接口变更）")
        return _parse_search(text)

    def _jl_detail_page(self, rid):
        return self._fetch(f"{_BASE}/uopac/s/detail.action?id={_check_jl_id(rid)}")

    def _holdings_jl(self, rid):
        tabs = _parse_tabs(self._jl_detail_page(rid))
        holdings = []
        for library, url in tabs:
            try:
                text = self._fetch(url)
            except RuntimeError:
                # 单馆代理失败(成员馆不可达等)→ 该馆 0 条,不拖垮整体
                continue
            holdings.extend(_parse_holding_rows(text, library))
        return holdings

    def _detail_jl(self, rid):
        d = _parse_detail(self._jl_detail_page(rid))
        if not d["title"]:
            raise RuntimeError(f"金陵图书馆：未找到该书详情：{rid}")
        return _Book(
            record_id=str(rid),
            title=d["title"],
            author=d["author"],
            publisher=d["publisher"],
            publish_year=d["publish_year"],
            isbn=d["isbn"],
            call_number=d["call_number"],
            summary=d["summary"],
        )

    # ---- NJL01（南京图书馆 ALEPH） ----

    def _search_prov(self, keyword, page=1, limit=20):
        return aleph.search_raw(_PROV, keyword, page=page)

    def _holdings_prov(self, rid):
        return aleph.get_holdings(_PROV, rid)

    def _detail_prov(self, rid):
        return aleph.get_book_detail(_PROV, rid)

    # ---- 双源编排 ----

    def search(self, keyword, page=1, limit=20):
        # 源级容错：≥1 源成功即返回存活源结果（数据原样）；两源全失败才报错。
        # 各源错误消息已自带馆名，不再二次包装。
        per_source = {}
        errors = []
        for source, fn in (("JL", self._search_jl), ("NJL01", self._search_prov)):
            try:
                per_source[source] = fn(keyword, page, limit)
            except CaptchaError:
                raise  # 验证码墙是全局限速信号，快速失败给可操作提示
            except RuntimeError as e:
                errors.append(str(e))
        if not per_source:
            raise RuntimeError("南京：两源检索均失败——" + "；".join(errors))
        books = _merge_books({s: r["books"] for s, r in per_source.items()})
        # 合计口径：任一存活源不提供总数 → 合计不可知，如实 None
        totals = [r["total_results"] for r in per_source.values()]
        total = None if any(t is None for t in totals) else sum(totals)
        return _SearchResult(
            success=True,
            error="",
            statistics={
                "total_results": total,
                "page": page,
                "total_pages": max(r["total_pages"] for r in per_source.values()),
                "has_next": any(page < r["total_pages"] for r in per_source.values()),
            },
            books=books,
        )

    def get_holdings(self, book_id):
        """复合 book_id 拆成员逐个查询后聚合（可借在前、馆名升序）；单成员同一路径。

        容错口径：首成员（目标源）失败报错；附属源失败跳过，返回已查到部分。
        """
        holdings = []
        for i, (source, rid) in enumerate(_split_book_id(book_id)):
            try:
                fn = self._holdings_prov if source == "NJL01" else self._holdings_jl
                holdings.extend(fn(rid))
            except CaptchaError:
                raise  # 封禁信号穿透聚合，不被附属源跳过逻辑静默
            except RuntimeError:
                if i == 0:
                    raise
        holdings.sort(key=lambda h: (not h.available, h.library))
        return holdings

    def get_book_detail(self, book_id):
        """复合 id 取优先级最高成员的详情；record_id 保留查询原样。目标源失败如实报错。"""
        source, rid = _split_book_id(book_id)[0]
        if source == "NJL01":
            return replace(self._detail_prov(rid), record_id=str(book_id))
        return self._detail_jl(rid)

    def get_return_date(self, item_id):
        """南京两源都无按单册查归还日期的接口：应还日期在馆藏响应里直取。

        南京馆藏不带 item_id，模块级 get_holdings 的补查分支真网永不触发；
        定义仅为对齐契约形状。
        """
        raise RuntimeError(f"南京：无单册归还日期接口：{item_id}")


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索南京全市联合目录(金陵图书馆+各区馆)。上游报错抛 RuntimeError。

    源站每页固定 20 条,limit 参数不生效(数据边界,翻页请用 page)。
    """
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"金陵图书馆搜索失败：{result.error}")

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
    """指定图书在各成员馆的馆藏与可借状态,可借的排前面。

    每持有馆一次代理请求(1+N),多馆持有的书响应较慢(4 秒节流)。
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
        # 契约形态兼容分支:南京数据无 item_id,真网路径不会触发
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
