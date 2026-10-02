"""宁波适配器:宁波市图书馆图创 tcc-opac 全市联合目录(opac.nblib.cn/999)
→ base.py 统一模型。

图创 tcc-opac(Java/Spring + Vue2 SPA)与穗杭的图创 Interlib 是不同产品线:
纯 JSON API + JWT 访客令牌,不能复用 interlib/ 家族。端点与参数形态由前端
JS 逆向(chunk-5a920f2a RefineResults / chunk-3f5b34c0 BookDetails+HoldingTable
组件)并实抓验证,见 tests/fixtures/ningbo/NOTES.md:

- 令牌 POST /system/user/getOpenApiAccessToken(匿名 {} 即发,expiresIn 秒级
  字符串,实测 2523~5108s)→ 请求头 ACCESS-TOKEN;code==1003 过期自动重取一次;
- 检索 POST /search/(注意尾斜杠;bookSearch 端点是给开放平台的,参数形态
  不同且曾长期「系统异常」,勿混用):body {current,size,searchWay,sortWay,
  sortOrder,hasholding,q,facetFieldSearch};hasholding 是二值过滤,1(或缺省)
  =只看有馆藏、0=只看无馆藏,两集合不相交(实测「三体」375 条 vs 32 条,
  且「缺省」与 1 结果完全一致),取 0 会拿到聚合条目所在的空壳子集,适配器
  固定传 1;searchWay 码表 marc=任意词/title/
  isbn/author…(与 Interlib 同款词表);响应无 code 字段=成功,顶层 numFound
  是字符串、bookList[] 雪花 id;code∈{43001,-1,-402} 触发前端滑块验证 →
  程序化停手抛错,不硬闯;
- 详情 POST /service/biblios/getbyid?id=&fields=300a,314a,327a,330a(参数走
  查询串,axios params 形态,空 body):data.biblios 主行 + data.fieldItem
  UNIMARC 字典(200$a/200$f/010$a/100$a/690$a…)+ data.fields 附注四字段;
  code==-1「数据不存在」= 检索聚合条目无本地书目(边界,见下);
- 馆藏 POST /service/hold/pagelist {current:1,size:500,bibliosId}(前端同款
  一页全量):data.records[] 单册级,statename 原生状态词(在馆/借出),
  returnTime 完整时间戳 → due_date 取日期段;curOrgName/curlocalName 是
  当前馆/当前地点(在借即所在),orgName/orglocalName 是所属馆/登记地点。

数据边界(原值照登,不做预设判断):
- 联合目录含慈溪/奉化等区县馆与城市书房,馆名带「慈溪_」类下划线前缀属
  源站原值;
- 聚合条目(新导入的雪花 id 1849… 段,booktype 同为 1)无本地书目:详情答
  「数据不存在」、馆藏 0 条,不是故障。它们属「无馆藏」子集,hasholding=1
  的检索不会返回;解析层仍按 code==-1/0 条防御(book_id 可能被外部直接传入);
- 「无馆藏」子集的检索条目 publisher/pubdate 常为空串(索引未富化);
  有馆藏条目实测带 publisher/pubdate/isbn/callno,完整字段仍以详情为准;
- 老书目 MARC 210/215 可能全空(出版项缺失),出版年兜底从 100$a 定长字段
  取「d+年份」段;
- 索书号:classno 是分类号不冒充索书号(南京口径),detail.call_number 取
  biblios.shelfno(常空),单册完整索书号在馆藏明细 callno;
- 馆藏一页 500 册封顶(前端同款),超出属数据边界。
"""
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from .base import BookDetail, BookSummary, Holding, SearchPage

_BASE = "https://opac.nblib.cn/api/tcc-opac/999"
_REFERER = "https://opac.nblib.cn/999"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA, "Referer": _REFERER, "Content-Type": "application/json"}
_THROTTLE = 4.0   # 秒/请求,按 spec 保守限速(令牌请求同样计入)
_TIMEOUT = 30     # 秒;检索实测 qtime ~1.3s,参数错误时源站会挂起(实测 25s+),及时止损
_MAX_SIZE = 50    # 检索每页条数上限(SPA 界面只给 10/15/20,后端容忍度未探边,保守)
_HOLD_SIZE = 500  # 馆藏一页全量,前端同款
_DETAIL_FIELDS = "300a,314a,327a,330a"  # 附注字段,前端同款
_CAPTCHA_CODES = (43001, -1, -402)      # 前端对 /search/ 的滑块验证触发码
_TOKEN_LEEWAY = 60  # 令牌提前 60 秒视为过期

_last_request = 0.0
_token = ""
_token_exp = 0.0  # time.monotonic() 基准


def _open(req, timeout=_TIMEOUT):
    """HTTP 入口:4 秒节流,返回响应文本。失败抛含馆名的 RuntimeError。"""
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as e:
        raise RuntimeError(f"宁波图书馆请求失败：{e}") from e


def _post(path, payload=None, params=None):
    """POST JSON 到 _BASE+path:payload 作 body(缺省空 JSON),params 拼查询串
    (getbyid 的 axios params 形态)。注入 ACCESS-TOKEN;code==1003(令牌失效)
    自动重取一次重试。响应非 JSON 视为被拦截/接口变更,抛错。"""
    url = _BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    body = json.dumps(payload if payload is not None else {}).encode("utf-8")

    def once(tk):
        headers = dict(_HEADERS)
        if tk:
            headers["ACCESS-TOKEN"] = tk
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        text = _open(req)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            raise RuntimeError(
                f"宁波图书馆：响应不是 JSON（可能被拦截或接口变更）：{text[:120]}"
            ) from e

    resp = once(_ensure_token())
    if isinstance(resp, dict) and resp.get("code") == 1003:
        resp = once(_ensure_token(force=True))
    return resp


def _ensure_token(force=False):
    """访客令牌:匿名 POST 即发,模块级缓存到 expiresIn(秒,源站给字符串)。"""
    global _token, _token_exp
    if not force and _token and time.monotonic() < _token_exp - _TOKEN_LEEWAY:
        return _token
    url = _BASE + "/system/user/getOpenApiAccessToken"
    req = urllib.request.Request(
        url, data=b"{}", headers=dict(_HEADERS), method="POST")
    text = _open(req)
    try:
        resp = json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        raise RuntimeError(f"宁波图书馆：令牌响应不是 JSON：{text[:120]}") from e
    data = resp.get("data") or {}
    tk = str(data.get("token") or "")
    if resp.get("code") != 200 or not tk:
        raise RuntimeError(
            f"宁波图书馆：获取访客令牌失败（code={resp.get('code')}）：{resp.get('desc') or ''}")
    try:
        expiry = float(data.get("expiresIn") or 3600)
    except (TypeError, ValueError):
        expiry = 3600.0
    _token = tk
    _token_exp = time.monotonic() + expiry
    return _token


def _clean(text):
    """JSON 字段值 → 原值字符串(None→空串),只去首尾空白,不改内容。"""
    if text is None:
        return ""
    return str(text).strip()


def _year(text):
    m = re.search(r"(?:19|20)\d{2}", str(text or ""))
    return m.group(0) if m else ""


def _year_from_100a(text):
    """UNIMARC 100$a 定长字段:形如「20160911d2003    km…」,d 后 4 位是出版年。"""
    m = re.search(r"d((?:19|20)\d{2})", str(text or ""))
    return m.group(1) if m else ""


def _date_only(text):
    """returnTime 完整时间戳「YYYY-MM-DD HH:MM:SS」→ 日期段;形态不符返回空串。"""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(text or ""))
    return m.group(1) if m else ""


def _check_book_id(book_id):
    """book_id 是 tcc-opac 原生雪花数字 id(单源,不加前缀)。"""
    s = str(book_id or "").strip()
    if not s.isdigit():
        raise RuntimeError(f"宁波图书馆：book_id 格式应为 tcc-opac 数字 id：{book_id}")
    return s


def _first(values):
    """fieldItem 的值是字符串列表,取首个非空原值。"""
    for v in values or []:
        s = _clean(v)
        if s:
            return s
    return ""


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


class _Client:
    """tcc-opac 轻量 client:令牌 + 三原语,原始 JSON → 与 vendor 对象同形结构。"""

    def _check_search(self, resp):
        """/search/ 成功响应无 code 字段;带 code 即异常——43001/-1/-402 是前端
        滑块验证触发码(程序化停手,不硬闯),desc 原值照登。"""
        if isinstance(resp, dict) and "code" in resp:
            code = resp.get("code")
            desc = _clean(resp.get("desc"))
            if code in _CAPTCHA_CODES:
                raise RuntimeError(
                    f"宁波图书馆：检索命中滑块验证/风控（code={code}）：{desc}")
            if code != 200:
                raise RuntimeError(f"宁波图书馆：检索失败（code={code}）：{desc}")
        if not isinstance(resp, dict) or "bookList" not in resp:
            raise RuntimeError("宁波图书馆：检索响应缺少 bookList（接口可能变更）")
        return resp

    def search(self, keyword, page=1, limit=20):
        try:
            size = max(1, min(int(limit), _MAX_SIZE))
        except (TypeError, ValueError):
            size = 20
        page = max(1, int(page or 1))
        payload = {
            "current": page,
            "size": size,
            "searchWay": "marc",  # 任意词;isbn 专有码表项因存储连字符形态不一未启用
            "sortWay": "score",
            "sortOrder": "desc",
            "hasholding": 1,      # 1=只看有馆藏(源站默认,与缺省等价);0=只看无馆藏,勿用
            "q": str(keyword or ""),
            "facetFieldSearch": {},
        }
        resp = self._check_search(_post("/search/", payload))
        try:
            total = int(resp.get("numFound") or 0)  # 源站给字符串
        except (TypeError, ValueError):
            total = 0
        books = [
            _Book(
                record_id=_clean(it.get("id")),
                title=_clean(it.get("title")),
                author=_clean(it.get("author")),
                publisher=_clean(it.get("publisher")),
                publish_year=_year(it.get("pubdate")),
                availability_summary="",  # 检索条目无馆藏概况(数据边界)
            )
            for it in (resp.get("bookList") or [])
            if isinstance(it, dict) and _clean(it.get("id"))
        ]
        total_pages = math.ceil(total / size) if total else 0
        return _SearchResult(
            success=True,
            error="",
            statistics={
                "total_results": total,
                "page": page,
                "total_pages": total_pages,
                "has_next": page < total_pages,
            },
            books=books,
        )

    def get_holdings(self, book_id):
        bid = _check_book_id(book_id)
        resp = _post("/service/hold/pagelist",
                     {"current": 1, "size": _HOLD_SIZE, "bibliosId": bid})
        if not isinstance(resp, dict):
            raise RuntimeError("宁波图书馆：馆藏响应形态异常")
        code = resp.get("code")
        if code == -1:
            # 「数据不存在」:聚合条目无本地书目 → 视同无馆藏(空列表),原值照登于注释
            return []
        if code != 200:
            raise RuntimeError(
                f"宁波图书馆：馆藏查询失败（code={code}）：{_clean(resp.get('desc'))}")
        records = (resp.get("data") or {}).get("records") or []
        holdings = []
        for r in records:
            if not isinstance(r, dict):
                continue
            status = _clean(r.get("statename")) or _clean(r.get("stateStr"))
            holdings.append(_Holding(
                library=_clean(r.get("curOrgName")) or _clean(r.get("orgName")),
                location=_clean(r.get("curlocalName")) or _clean(r.get("orglocalName")),
                call_number=_clean(r.get("callno")),
                status=status,
                available=(status == "在馆"),  # 词表外状态保守不可借,原值照登
                due_date=_date_only(r.get("returnTime")),
            ))
        return holdings

    def get_book_detail(self, book_id):
        bid = _check_book_id(book_id)
        resp = _post("/service/biblios/getbyid", None,
                     params={"id": bid, "fields": _DETAIL_FIELDS})
        if not isinstance(resp, dict):
            raise RuntimeError("宁波图书馆：详情响应形态异常")
        code = resp.get("code")
        if code == -1:
            raise RuntimeError(
                f"宁波图书馆：未找到该书详情：{book_id}（{_clean(resp.get('desc')) or '数据不存在'}；"
                "检索聚合条目可能无本地书目）")
        if code != 200:
            raise RuntimeError(
                f"宁波图书馆：详情查询失败（code={code}）：{_clean(resp.get('desc'))}")
        data = resp.get("data") or {}
        b = data.get("biblios") or {}
        fi = data.get("fieldItem") or {}
        notes = data.get("fields") or {}
        title = _clean(b.get("title")) or _first(fi.get("200$a"))
        if not title:
            raise RuntimeError(f"宁波图书馆：未找到该书详情：{book_id}")
        summary = ""
        for marc in ("330", "327", "300"):  # 内容提要 → 内容附注 → 一般性附注
            summary = _clean(notes.get(marc + "a")) or _first(fi.get(marc + "$a"))
            if summary:
                break
        return _Book(
            record_id=bid,
            title=title,
            author=_clean(b.get("author")) or _first(fi.get("200$f")),
            publisher=_clean(b.get("publisher")) or _first(fi.get("210$c")),
            publish_year=(_year(b.get("pubdate"))
                          or _year(_first(fi.get("210$d")))
                          or _year_from_100a(_first(fi.get("100$a")))),
            isbn=_clean(b.get("isbn")) or _first(fi.get("010$a")),
            call_number=_clean(b.get("shelfno")),  # classno 分类号不冒充索书号
            summary=summary,
        )


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索宁波全市联合目录(市馆＋慈溪/奉化等区县馆＋城市书房)。

    上游报错抛 RuntimeError;命中滑块验证/风控同样抛错停手,不硬闯。
    """
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"宁波图书馆搜索失败：{result.error}")

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

    单册级;借出馆藏带 due_date(源站 returnTime 完整时间戳,取日期段)。
    一页 500 册封顶(前端同款,数据边界)。
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
        # 契约形态兼容分支:宁波 due_date 解析期已取全,item_id 恒空,真网路径不触发
        if not available and getattr(h, "item_id", ""):
            item["due_date"] = _client.get_return_date(h.item_id)
        items.append(item)
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(book_id: str) -> BookDetail:
    """指定图书的完整详情:书名、作者、出版社、出版年、ISBN、索书号、内容简介。

    检索聚合条目可能无本地书目(「数据不存在」),抛 RuntimeError;老书目出版项
    可能缺失,原值照登为空串。
    """
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
