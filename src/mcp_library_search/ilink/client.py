"""SirsiDynix iLink 家族 HTTP 层与会话流。

成员：甘肃省图书馆（`gansu_prov`）、陇南市图书馆（`longnan`）、甘南州图书馆
（`gannan`），三站共用甘肃省图同一套 iLink 实例（`search.gslib.com.cn`），差别只在
检索表单的 `library` 馆别过滤值。大连接口同构但仍是独立实现（见 cn.md 3.8）。

会话流：GET 入口 `/uhtbin/cgisirsi/x/x/0/49/`（返回「快速检索」首页）→ 解析
`searchform` 的 action（带当次 ps token）→ POST 检索 → 解析 `hitlist` 的 action
翻页 / VIEW^N 看详情。**ps token 每响应都变**：一律从上一步响应里解析下一步
action，绝不硬编码；全程同一 CookieJar 串行。节流 ≥4 秒/host。

检索一律按 ASCII 双引号短语下发，短语 0 命中或源站拒答时退回裸词再试一次。
详情/馆藏无 catkey 直链，靠题名（TI）候选梯度重检索定位 catkey 的全局序号，
再 POST VIEW^N 取详情页（同大连）。book_id 形如 "{catkey}:{题名}"。
"""
import http.cookiejar
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from . import parser

if TYPE_CHECKING:
    from . import IlinkConfig

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
_HEADERS = {"User-Agent": _UA}

_jar = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_jar))
_last_request = 0.0


def _open(cfg: "IlinkConfig", req, timeout=25):
    """HTTP 入口：CookieJar 会话 + 可配节流，返回 UTF-8 文本。失败抛含馆名的 RuntimeError。

    页面 charset 为 utf-8（HTTP 头在初始重定向页可能标 iso-8859-1，以内容为准）。
    """
    global _last_request
    wait = cfg.throttle - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    try:
        with _opener.open(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"{cfg.name_cn}请求失败：{e}") from e


def _reset_session():
    _jar.clear()
    global _last_request
    _last_request = 0.0


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
    item_id: str = ""   # 匿名视图无单册条码 → 恒空串
    due_date: str = ""  # 匿名视图无应还日期 → 恒空串

    def is_available(self):
        return self.available


def _entry_url(cfg: "IlinkConfig") -> str:
    return cfg.base_url + cfg.entry_path


def _get_entry(cfg: "IlinkConfig") -> str:
    return _open(cfg, urllib.request.Request(_entry_url(cfg), headers=_HEADERS))


def _post(cfg: "IlinkConfig", action, fields):
    data = urllib.parse.urlencode(fields).encode()
    return _open(cfg, urllib.request.Request(
        parser.abs_url(cfg.base_url, action), data=data, headers=_HEADERS))


def _search_once(cfg: "IlinkConfig", keyword, srchfield):
    """入口页取 fresh searchform action → POST 检索（带馆别过滤），返回结果页 HTML。"""
    entry = _get_entry(cfg)
    action = parser.searchform_action(entry)
    if not action:
        return ""  # 入口页形态异常 → 交给上层判定/重建
    sort_by = parser.sort_by_value(entry) or cfg.sort_by
    return _post(cfg, action, {
        "searchdata1": keyword,
        "srchfield1": srchfield,
        "library": cfg.library_code,
        "sort_by": sort_by,
    })


def _jump(cfg: "IlinkConfig", result_page, page):
    """从结果页解析 hitlist action → POST form_type=JUMP^{start} 翻页。"""
    action = parser.hitlist_action(result_page)
    if not action:
        return ""
    start = (page - 1) * cfg.page_size + 1
    return _post(cfg, action, {
        "first_hit": "1",
        "last_hit": str(cfg.page_size),
        "form_type": f"JUMP^{start}",
    })


def _view(cfg: "IlinkConfig", result_page, position):
    """从结果页解析 hitlist action → POST VIEW^{position}=详细资料 取详情页。

    **position 是命中集的全局序号**（跨页累计，第 2 页第 1 位＝page_size+1）。
    """
    action = parser.hitlist_action(result_page)
    if not action:
        return ""
    first, last = parser.hitlist_range(result_page, cfg.page_size)
    return _post(cfg, action, {
        "first_hit": str(first),
        "last_hit": str(last),
        "form_type": "",
        f"VIEW^{position}": "详细资料",
    })


def search(cfg: "IlinkConfig", keyword, page=1, limit=20) -> _SearchResult:
    """检索；短语优先、0 命中或拒答退回裸词；翻页走 JUMP。源站每页固定，limit 不生效。"""
    srchfield = cfg.general_field
    query = parser.phrase(keyword)
    text = _search_once(cfg, query, srchfield)
    if not parser.is_result_page(text):
        _reset_session()  # 会话失效：退回入口/异常 → 重建一次再试
        text = _search_once(cfg, query, srchfield)
    total = parser.parse_total(text) if parser.is_result_page(text) else 0
    if (not parser.is_result_page(text) or total == 0) and query != str(keyword or "").strip() \
            and not parser.is_entry_page(text):
        # 短语被源站拒答（含非索引字符回 Error 页）或 0 命中 → 退回裸词再试一次
        bare = _search_once(cfg, keyword, srchfield)
        if parser.is_result_page(bare) and parser.parse_total(bare) > 0:
            query, text, total = keyword, bare, parser.parse_total(bare)
    if not parser.is_result_page(text):
        raise RuntimeError(f"{cfg.name_cn}：检索未返回结果页（重复失败，可能会话无法建立）")
    if page > 1 and total > 0:
        jumped = _jump(cfg, text, page)
        if parser.is_result_page(jumped):
            text = jumped
        else:
            _reset_session()
            text2 = _search_once(cfg, query, srchfield)
            jumped = _jump(cfg, text2, page) if parser.is_result_page(text2) else ""
            if not parser.is_result_page(jumped):
                raise RuntimeError(f"{cfg.name_cn}：翻页失败（重复失败，可能会话无法建立）")
            text = jumped
    total_pages = max(1, math.ceil(total / cfg.page_size))
    return _SearchResult(
        success=True,
        error="",
        statistics={
            "total_results": total,
            "page": page,
            "total_pages": total_pages,
            "has_next": page < total_pages,
        },
        books=[
            _Book(
                record_id=b["record_id"], title=b["title"], author=b["author"],
                publisher=b["publisher"], publish_year=b["publish_year"],
                availability_summary=b["availability_summary"],
            )
            for b in parser.parse_hits(text)
        ],
    )


# ---- 详情/馆藏共用：题名候选梯度重检索 → catkey 定位（可翻页）→ VIEW^N ----
def _detail_attempt(cfg: "IlinkConfig", ckey, title):
    for query in parser.title_variants(title):
        text = _search_once(cfg, query, cfg.title_field)
        if not parser.is_result_page(text):
            if parser.is_entry_page(text):
                return None  # 会话失效：交给上层重建后再试
            continue  # 源站拒答该候选（含非索引字符回 Error 页）→ 换下一个候选
        pages = min(cfg.detail_max_pages,
                    max(1, math.ceil(parser.parse_total(text) / cfg.page_size)))
        for page in range(1, pages + 1):
            if page > 1:
                jumped = _jump(cfg, text, page)
                if not parser.is_result_page(jumped):
                    break  # 翻页失败：换下一个候选
                text = jumped
            pos = parser.find_ckey_position(text, ckey)   # 页内序号
            if pos is None:
                continue  # 该页没有目标 → 继续翻页
            detail = _view(cfg, text, (page - 1) * cfg.page_size + pos)
            if parser.is_detail_page(detail):
                return detail
    return None


def _fetch_detail(cfg: "IlinkConfig", ckey, title):
    detail = _detail_attempt(cfg, ckey, title)
    if detail is None:
        _reset_session()  # 会话失效或定位失败 → 重建一次再试
        detail = _detail_attempt(cfg, ckey, title)
        if detail is None:
            raise RuntimeError(
                f"{cfg.name_cn}：详情获取失败（重复失败，可能会话无法建立或记录不可定位）")
    return detail


def split_book_id(book_id):
    """book_id 形如 "{catkey}:{题名}"；按首个冒号拆（题名可含冒号）。"""
    s = str(book_id or "")
    ckey, sep, title = s.partition(":")
    if not sep or not ckey.strip():
        raise RuntimeError(f"iLink：book_id 格式应为 catkey:题名：{book_id}")
    return ckey.strip(), title.strip()


def get_book_detail(cfg: "IlinkConfig", book_id) -> _Book:
    ckey, title = split_book_id(book_id)
    if not title:
        raise RuntimeError(f"{cfg.name_cn}：book_id 缺少题名，无法重检索定位：{book_id}")
    text = _fetch_detail(cfg, ckey, title)
    t = parser.detail_field(text, "题名") or title
    rows = parser.holdings_rows(text)
    return _Book(
        record_id=book_id,
        title=t,
        author=parser.detail_field(text, "著者"),
        publisher=parser.detail_field(text, "出版者"),
        publish_year=parser.year(parser.detail_field(text, "出版日期")),
        isbn=parser.detail_field(text, "ISBN"),
        call_number=rows[0]["call_number"] if rows else "",
        summary="",  # 匿名详情页无内容提要字段
    )


def get_holdings(cfg: "IlinkConfig", book_id) -> list:
    ckey, title = split_book_id(book_id)
    if not title:
        raise RuntimeError(f"{cfg.name_cn}：book_id 缺少题名，无法重检索定位：{book_id}")
    text = _fetch_detail(cfg, ckey, title)
    status, available = parser.availability_from_copy_info(parser.copy_info(text))
    return [
        _Holding(
            library=r["library"],
            location=r["location"],
            call_number=r["call_number"],
            status=status,
            available=available,
            item_id="",
            due_date="",
        )
        for r in parser.holdings_rows(text)
    ]
