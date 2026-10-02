"""无锡适配器：图星 LibStar Find（无锡市新吴区图书馆）。

站点 `http://wxxqlsp.xw.i-wnd.cn:8013`。协议、解析与两个必需请求头
（`Referer`＋`groupcode`）见 `libstar/` 家族；本模块是家族之上的薄层。

当前单源——无锡市新吴区图书馆（libCode 80050700001）；无锡市图书馆（主馆）
源码 `WXST` 已按天津口径预留，接入后在同一城市标识下按 ISBN 归并，既有
book_id 契约不变。多实例归并是本城相对家族单实例原语的唯一差异。
"""
import math
import re
from dataclasses import dataclass, replace
from functools import partial
from types import SimpleNamespace

from ... import libstar
from ...libstar import LibStarConfig
from ...libstar import parser as _parser
from ...libstar.client import request as _family_request
from ..base import BookDetail, BookSummary, Holding, SearchPage

_NAME = "无锡市新吴区图书馆"
_BASE = "http://wxxqlsp.xw.i-wnd.cn:8013"
_GROUPCODE = "800507"

_CONFIG = LibStarConfig(city="wuxi", name_cn=_NAME,
                        base_url=_BASE, groupcode=_GROUPCODE)

# 兼容缝：单测直接引用家族检索模板与解析器；家族解析器带可选 name，此处绑定本馆名。
_SEARCH_BODY = libstar.SEARCH_BODY
_parse_search = partial(_parser.parse_search, name=_NAME)
_parse_detail = partial(_parser.parse_detail, name=_NAME)
_parse_holdings = partial(_parser.parse_holdings, name=_NAME)

# 数据源表：新增源只需在此加一条（天津口径）。WXST（无锡市图书馆）为预留槽位，
# 尚未接入——补上配置即可启用，book_id 形态与归并逻辑都已就位。
_SOURCES = {
    "WXXW": {"name_cn": _NAME},
    # "WXST": {"name_cn": "无锡市图书馆"},   # 预留：主馆，接入后按 ISBN 归并
}
# 归并优先级：主馆在前（复合 book_id 成员顺序与主记录取值同源）
_SOURCE_PRIORITY = ("WXST", "WXXW")


@dataclass
class _Book:
    """跨源归并用的轻量书目；`isbn` 是内部字段，不进 BookSummary 契约。"""

    record_id: str
    title: str = ""
    author: str = ""
    publisher: str = ""
    publish_year: str = ""
    availability_summary: str = ""
    isbn: str = ""


@dataclass
class _Holding:
    """与上海 vendor 客户端同形的馆藏对象（契约测试按此形态注入）。"""

    library: str = ""
    location: str = ""
    call_number: str = ""
    status: str = ""
    available: bool = True
    item_id: str = ""
    due_date: str = ""

    def is_available(self):
        return self.available


def _request(path, payload=None, params=None):
    """本城 HTTP 出口：委托家族 client，注入 Referer 与 groupcode 两个必需头。"""
    return _family_request(_CONFIG, path, payload=payload, params=params)


# ---- ISBN 归并与复合 book_id（口径照天津/合肥） ----


def _looks_like_isbn(keyword):
    """ISBN 形态判断：去连字符后 13 位（978/979 开头）或 10 位（末位可为 X）。"""
    s = str(keyword or "").replace("-", "").strip()
    if len(s) == 13 and s.isdigit():
        return s[:3] in ("978", "979")
    if len(s) == 10 and s[:9].isdigit():
        return s[9].isdigit() or s[9] in "Xx"
    return False


def _norm_isbn(isbn):
    """ISBN 归一：去连字符与空白并转大写；非 ISBN 形态返回空串（不参与归并）。"""
    s = re.sub(r"[\s-]", "", str(isbn or "")).upper()
    return s if _looks_like_isbn(s) else ""


def _merge_books(per_source):
    """跨源按归一 ISBN 归并：{source: [ _Book ]} → 归并后的 _Book 列表。

    口径同天津：同 ISBN 每源至多一个成员（源内重复保留首条）；多源命中合成复合
    record_id（`+` 连接，按优先级排序），书目字段取优先级最高成员的原值；无 ISBN
    （含脏值）不参与归并、各自成条，按源优先级排在分组条目之后。当前只有单源，
    此函数是预留结构——市图接入后无需改动归并逻辑。
    """
    order = []    # ISBN 首次出现顺序
    groups = {}   # 归一 ISBN -> {source: _Book}
    singles = []
    for source in _SOURCE_PRIORITY:
        for b in per_source.get(source, []):
            key = _norm_isbn(b.isbn)
            if not key:
                singles.append(b)
                continue
            members = groups.setdefault(key, {})
            if source in members:
                continue
            if not members:
                order.append(key)
            members[source] = b
    merged = []
    for key in order:
        ordered = [groups[key][s] for s in _SOURCE_PRIORITY if s in groups[key]]
        if len(ordered) == 1:
            merged.append(ordered[0])
        else:
            merged.append(replace(ordered[0],
                                  record_id="+".join(m.record_id for m in ordered)))
    merged.extend(singles)
    return merged


def _split_book_id(book_id):
    """复合/单成员 book_id → 按优先级排序的 [(source, record_id)]；形态非法即抛错。"""
    members = []
    for part in str(book_id or "").split("+"):
        source, sep, rid = part.strip().partition(":")
        if not sep or not rid or source not in _SOURCE_PRIORITY:
            raise RuntimeError(f"{_NAME}：未知 book_id 形态：{book_id}")
        members.append((source, rid))
    return sorted(members, key=lambda m: _SOURCE_PRIORITY.index(m[0]))


def _source(source):
    """取已接入源的配置；预留槽位（如 WXST）给出明确报错而非静默空结果。"""
    cfg = _SOURCES.get(source)
    if cfg is None:
        raise RuntimeError(f"{_NAME}：数据源 {source} 尚未接入（预留槽位）")
    return cfg


# ---------- 契约缝（与成都/台州/青岛同款） ----------


class _Client:
    """按源表分派：当前单源；源级容错口径同天津——≥1 源成功即返回存活源结果。"""

    def _search_source(self, source, keyword, page, limit):
        payload = dict(_SEARCH_BODY, searchFieldContent=str(keyword or ""),
                       page=page, rows=limit)
        r = _parse_search(_request("/find/unify/search", payload=payload))
        total, books = r["total_results"], r["books"]
        return {
            "books": [
                _Book(record_id=f"{source}:{b['book_id']}", title=b["title"],
                      author=b["author"], publisher=b["publisher"],
                      publish_year=b["publish_year"],
                      availability_summary=b["availability_summary"], isbn=b["isbn"])
                for b in books
            ],
            "total_results": total,
            "total_pages": math.ceil(total / limit) if total > 0 and limit > 0 else 0,
        }

    def search(self, keyword, page=1, limit=20):
        per_source, errors = {}, []
        for source, cfg in _SOURCES.items():
            try:
                per_source[source] = self._search_source(source, keyword, page, limit)
            except RuntimeError as e:
                errors.append(f"{cfg['name_cn']}：{e}")
        if not per_source:
            raise RuntimeError(f"{_NAME}：检索失败——" + "；".join(errors))
        books = _merge_books({s: r["books"] for s, r in per_source.items()})
        totals = [r["total_results"] for r in per_source.values()]
        # 合计口径同天津：任一存活源不提供总数 → 合计不可知，如实 None
        total = None if any(t is None for t in totals) else sum(totals)
        total_pages = max(r["total_pages"] for r in per_source.values())
        return SimpleNamespace(
            success=True,
            error="",
            statistics={"total_results": total, "page": page,
                        "total_pages": total_pages, "has_next": page < total_pages},
            books=books,
        )

    def _holdings_for(self, source, rid):
        _source(source)  # 预留源在此报错
        return [_Holding(**h) for h in
                _parse_holdings(_request("/find/physical/groupItemsByLibCode",
                                         payload={"recordId": rid}))]

    def get_holdings(self, book_id):
        """复合 book_id 拆成员逐个查询后聚合；容错口径同天津（首成员失败报错）。"""
        holdings = []
        for i, (source, rid) in enumerate(_split_book_id(book_id)):
            try:
                holdings.extend(self._holdings_for(source, rid))
            except RuntimeError:
                if i == 0:
                    raise
        holdings.sort(key=lambda h: (not h.available, h.library))
        return holdings

    def get_book_detail(self, book_id):
        """复合 id 取优先级最高成员的详情；record_id 保留查询原样（天津口径）。"""
        source, rid = _split_book_id(book_id)[0]
        _source(source)
        # 详情必须 GET（同参数 POST 回 9999，实抓验证）
        d = _parse_detail(_request("/find/searchResultDetail/getBookDetail",
                                   params={"recordId": rid}))
        return SimpleNamespace(record_id=book_id, **d)

    def get_return_date(self, item_id):
        """应还日期已内嵌在馆藏 `processType` 里，无按单册查的接口。

        定义仅为对齐契约形状（同天津）；模块级 get_holdings 的补查分支真网不触发。
        """
        raise RuntimeError(f"{_NAME}：无单册归还日期接口：{item_id}")


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索无锡市新吴区图书馆馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"{_NAME}搜索失败：{result.error}")

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
    """指定图书的馆藏与可借状态，可借的排前面。

    全站单馆（新吴区），馆藏地下沉到街道分馆与社区服务点，馆名原值照登。
    借出单册自带应还日期（藏在状态串里），访客视角即可拿到。
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
        # 契约测试要求已借出且带单册 item_id 时查归还时间。本城应还日期已内嵌在
        # 馆藏 processType 里解析出来，故仅在日期缺失时才补查——真网永不走到
        # （青岛/天津是同款分支但 item_id 恒空；本城 item_id 非空，必须显式判空）
        if not available and getattr(h, "item_id", "") and not item["due_date"]:
            item["due_date"] = _client.get_return_date(h.item_id)
        items.append(item)
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(book_id: str) -> BookDetail:
    """指定图书的完整详情：书名、作者、出版社、出版年、ISBN、索书号、内容简介。

    `call_number` 取详情「中图法分类号」（cnb67，同青岛家族口径）；完整索书号在
    馆藏明细的 `call_number` 里。老书目出版项无出版社段时（`北京,2017`）
    `publisher` 为空串，属数据边界。
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
