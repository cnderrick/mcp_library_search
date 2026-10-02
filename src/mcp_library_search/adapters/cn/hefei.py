"""合肥适配器：安徽省图书馆 AH + 合肥市图书馆 HF 双源合并，照天津「一城多源」范本。

两源均为图创 Interlib（与穗杭同模板），结构差异只在应用上下文路径：
AH 是 /opac（家族默认），HF 是 /lib2（/opac 探测为 nginx 500）。家族三原语
硬编码 /opac 前缀，HF 不能直接套用，故本模块按源上下文自建三原语，HTTP 层与
解析器仍复用家族（interlib.client / interlib.parser）。

book_id 形态：AH:{bookrecno} / HF:{bookrecno}；跨源同 ISBN 命中合成复合 id
（成员按优先级 AH > HF 以 + 连接，如 AH:1901181704+HF:1001460005），书目字段
取最高优先级成员原值。归并与容错口径照天津，字段侦察结论（含详情页 tagTr 行
的家族解析器坑侦察与修复记录）见 tests/fixtures/hefei/NOTES.md。
"""
import json
import re
from dataclasses import dataclass, field, replace

from ...interlib import InterlibConfig
from ...interlib import client as il_client
from ...interlib import parser as il_parser
from ..base import BookDetail, BookSummary, Holding, SearchPage


@dataclass(frozen=True)
class _Source:
    """单源配置：book_id 前缀 + Interlib 配置 + 应用上下文路径。"""

    prefix: str           # book_id 源前缀，如 "AH"
    cfg: InterlibConfig   # base_url＝站点根；cfg.name_cn 兼作源级报错前缀
    ctx: str              # Interlib 应用上下文：AH＝/opac，HF＝/lib2（NOTES.md）


_AH = _Source("AH",
              InterlibConfig(city="ah", name_cn="安徽省图书馆",
                             base_url="https://opac.ahlib.com"),
              "/opac")
_HF = _Source("HF",
              InterlibConfig(city="hf", name_cn="合肥市图书馆",
                             base_url="https://opac.hflib.org.cn"),
              "/lib2")
# 归并优先级：省馆 > 市馆（复合 book_id 成员顺序与主记录取值同源）
_SOURCE_PRIORITY = ("AH", "HF")
_SOURCES = {s.prefix: s for s in (_AH, _HF)}


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
    available: bool = True
    item_id: str = ""
    due_date: str = ""

    def is_available(self):
        return self.available


# ---- ISBN 归并与复合 book_id（口径照天津，见 tests/fixtures/tianjin/NOTES.md） ----

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
    """跨源按归一 ISBN 归并：{prefix: [ _Book ]} → 归并后的 _Book 列表。

    口径照天津：
    - 同一 ISBN 每源至多一个成员（源内同 ISBN 多条——多卷/重印——保留首条，
      其余条目让位于首条的馆藏，spec 已接受该取舍）；
    - 多源命中合成复合 record_id（成员以 + 连接，按优先级排序），
      书目字段取优先级最高成员的原值；
    - 无 ISBN（含脏值）不参与归并，各自成条；
    - 顺序：ISBN 分组按首次出现顺序，未分组条目按源顺序排在最后。
    """
    order = []    # ISBN 首次出现顺序
    groups = {}   # 归一 ISBN -> {prefix: _Book}
    singles = []  # 无 ISBN 条目
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
    """复合/单成员 book_id → 按优先级排序的 [(prefix, record_id)]；形态非法即抛错。"""
    members = []
    for part in str(book_id or "").split("+"):
        source, sep, rid = part.strip().partition(":")
        if not sep or not rid or source not in _SOURCE_PRIORITY:
            raise RuntimeError(f"合肥图书馆：未知 book_id 形态：{book_id}")
        members.append((source, rid))
    return sorted(members, key=lambda m: _SOURCE_PRIORITY.index(m[0]))


# ---- 单源三原语（家族形态，路径按源上下文拼接；证据见 NOTES.md） ----


def _search_once(src, keyword, page, limit):
    params = {
        "q": keyword,
        "searchType": "standard",
        "searchWay0": "marc",
        "logical0": "AND",
        "rows": limit,
        "sortWay": "score",
        "sortOrder": "desc",
        "page": page,
    }
    if src.cfg.curlibcode:
        params["curlibcode"] = src.cfg.curlibcode
    html = il_client.get(src.cfg, src.ctx + "/search", params)
    return il_parser.parse_search(html)


def _search_raw(src, keyword, page=1, limit=20):
    """检索并返回家族 parser 原始结构（books 条目含 isbn 内部字段，供归并）。

    同家族 search_raw 口径：带连字符的 ISBN 在 marc 检索下命中不了，
    首搜为空时去连字符重试一次。
    """
    r = _search_once(src, keyword, page, limit)
    if not r["books"] and "-" in keyword:
        retry = _search_once(src, keyword.replace("-", ""), page, limit)
        if retry["books"]:
            r = retry
    return r


def _holdings_for(src, rid):
    """单成员馆藏：Ajax JSON 接口 {ctx}/api/holding/{bookrecno}，家族 parser 解析。"""
    body = il_client.get(src.cfg, f"{src.ctx}/api/holding/{rid}",
                         {"limitLibcodes": "", "isCluster": ""})
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{src.cfg.name_cn}：馆藏数据解析失败：{e}") from e
    holdings = []
    for h in il_parser.parse_holdings(payload):
        holdings.append(_Holding(
            library=h["library"], location=h["location"],
            call_number=h["call_number"], status=h["status"],
            available=il_parser.is_available_status(h["status"]),
            due_date=h["due_date"]))
    return holdings


def _detail_for(src, rid):
    """单成员详情：{ctx}/book/{bookrecno}，家族 parse_detail 解析。

    详情页 tagTr（读者标签）行的裸标签单元格曾触发家族解析器陈旧标签覆盖
    （AH 布局下 author 被覆盖成「没有标签」），家族已于 2026-10-02 修复
    （标签一对一消费，江阴/温州独立实证同坑）；侦察证据与回归钉子见 NOTES.md。
    """
    html = il_client.get(src.cfg, f"{src.ctx}/book/{rid}")
    d = il_parser.parse_detail(html)
    if not d["title"]:
        raise RuntimeError(f"{src.cfg.name_cn}：未找到该书详情：{rid}")
    return d


class _Client:
    """双源客户端：AH（安徽省图书馆）+ HF（合肥市图书馆），合并口径照天津。"""

    def _search_source(self, src, keyword, page, limit):
        r = _search_raw(src, keyword, page=page, limit=limit)
        return {
            "books": [
                _Book(record_id=f"{src.prefix}:{b['book_id']}", title=b["title"],
                      author=b["author"], publisher=b["publisher"],
                      publish_year=b["publish_year"],
                      availability_summary=b["availability_summary"],
                      isbn=b.get("isbn", ""))
                for b in r["books"]
            ],
            "total_results": r["total_results"],
            "total_pages": r["total_pages"],
        }

    def search(self, keyword, page=1, limit=20):
        # 源级容错：≥1 源存活即返回存活源结果（数据原样）；两源全失败才报错。
        # il_client 的报错已含各源中文馆名，直接收集原文汇总。
        per_source = {}
        errors = []
        for prefix in _SOURCE_PRIORITY:
            src = _SOURCES[prefix]
            try:
                per_source[prefix] = self._search_source(src, keyword, page, limit)
            except RuntimeError as e:
                errors.append(str(e))
        if not per_source:
            raise RuntimeError("合肥图书馆：两源检索均失败——" + "；".join(errors))
        books = _merge_books({s: r["books"] for s, r in per_source.items()})
        # 合计口径：任一存活源不提供总数（「检索到 N 条」解析不到）→ 合计不可知，
        # 如实 None，不拿部分源的数编造全城总数
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

        容错口径照天津：首成员（目标源）失败报错；附属源失败跳过，返回已查到部分。
        """
        holdings = []
        for i, (prefix, rid) in enumerate(_split_book_id(book_id)):
            try:
                holdings.extend(_holdings_for(_SOURCES[prefix], rid))
            except RuntimeError:
                if i == 0:
                    raise
        holdings.sort(key=lambda h: (not h.available, h.library))
        return holdings

    def get_book_detail(self, book_id):
        """复合 id 取优先级最高成员的详情；record_id 保留查询原样。目标源失败如实报错。"""
        prefix, rid = _split_book_id(book_id)[0]
        d = _detail_for(_SOURCES[prefix], rid)
        return _Book(record_id=book_id, title=d["title"], author=d["author"],
                     publisher=d["publisher"], publish_year=d["publish_year"],
                     isbn=d["isbn"], call_number=d["call_number"],
                     summary=d["summary"])

    def get_return_date(self, item_id):
        """合肥双源无按单册查归还日期的接口：Interlib 应还日期已在馆藏 JSON 解析。

        合肥馆藏不带 item_id，模块级 get_holdings 的补查分支真网永不触发；
        定义仅为对齐契约形状。
        """
        raise RuntimeError(f"合肥图书馆：无单册归还日期接口：{item_id}")


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索双源合并馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"合肥图书馆搜索失败：{result.error}")

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
    """指定图书在各分馆的馆藏与可借状态，可借的排前面。"""
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
        # 契约测试要求已借出且带单册 item_id 时查归还时间；Interlib 的应还日期
        # 已在馆藏 JSON 里解析（interlib.parser._holding_due_date），真网 item_id 恒空不会走到这
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
