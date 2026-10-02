"""天津适配器：主馆 TJL01 + 少儿馆 TJC01（ALEPH）+ 中新友好（Interlib）三源合并。

book_id 形态：TJL01:{doc_number} / TJC01:{doc_number} / ZXYH:{bookrecno}；
同一 ISBN 多源命中合成复合 id（成员以 + 连接，主馆在前）。
ALEPH 侧结构细节全部见 tests/fixtures/tianjin/NOTES.md，解析与 HTTP 已上收到
`aleph/` 家族模块（南京图书馆同用）；本模块只留三源编排、ISBN 归并与统一模型包装。
"""
import re
from dataclasses import replace

from ... import aleph
from ...aleph import AlephConfig
from ...aleph import Book as _Book
from ...aleph import CaptchaError as _CaptchaError
from ...aleph import Holding as _Holding
from ...aleph import SearchResult as _SearchResult
from ...aleph.parser import looks_like_isbn as _looks_like_isbn
from ...interlib import InterlibConfig
from ...interlib import get_book_detail as il_detail
from ...interlib import get_holdings as il_holdings
from ...interlib import search_raw as il_search
from ..base import BookDetail, BookSummary, Holding, SearchPage

_THROTTLE = 4.0  # ALEPH 验证码墙按 IP 封，限速是硬约束（NOTES.md）
# 验证码墙按 IP 封，两台 ALEPH 可能同时被封：解封指引一次列全地址，免得解一个才发现另一个
_UNBLOCK_URLS = "、".join(
    f"{host}（{name}）" for host, name in (
        ("http://opacwh.tjl.tj.cn:8991", "天津图书馆"),
        ("http://opacse.tjl.tj.cn:8991", "天津市少年儿童图书馆"),
    ))
_SOURCES = {
    "TJL01": AlephConfig(source="TJL01", name_cn="天津图书馆",
                         base_url="http://opacwh.tjl.tj.cn:8991",
                         unblock_urls=_UNBLOCK_URLS, throttle=_THROTTLE),
    "TJC01": AlephConfig(source="TJC01", name_cn="天津市少年儿童图书馆",
                         base_url="http://opacse.tjl.tj.cn:8991",
                         unblock_urls=_UNBLOCK_URLS, throttle=_THROTTLE),
}
# 归并优先级：主馆 > 少儿馆 > 中新友好（复合 book_id 成员顺序与主记录取值同源）
_SOURCE_PRIORITY = ("TJL01", "TJC01", "ZXYH")
_ZXYH = InterlibConfig(city="zxyh", name_cn="中新友好图书馆",
                       base_url="http://sm.interlib.cn:8104", curlibcode="STC001")


# ---- ISBN 归并与复合 book_id（口径见 tests/fixtures/tianjin/NOTES.md） ----

def _norm_isbn(isbn):
    """ISBN 归一：去连字符与空白并转大写；非 ISBN 形态返回空串（不参与归并）。"""
    s = re.sub(r"[\s-]", "", str(isbn or "")).upper()
    return s if _looks_like_isbn(s) else ""


def _merge_books(per_source):
    """跨源按归一 ISBN 归并：{source: [ _Book ]} → 归并后的 _Book 列表。

    口径：
    - 同一 ISBN 每源至多一个成员（源内同 ISBN 多条——多卷/重印——保留首条，
      其余条目让位于首条的馆藏，spec 已接受该取舍）；
    - 多源命中合成复合 record_id（成员以 + 连接，按优先级排序），
      书目字段取优先级最高成员的原值；
    - 无 ISBN（含脏值）不参与归并，各自成条；
    - 顺序：ISBN 分组按首次出现顺序，未分组条目按源顺序排在最后。
    """
    order = []    # ISBN 首次出现顺序
    groups = {}   # 归一 ISBN -> {source: _Book}
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
    """复合/单成员 book_id → 按优先级排序的 [(source, record_id)]；形态非法即抛错。"""
    members = []
    for part in str(book_id or "").split("+"):
        source, sep, rid = part.strip().partition(":")
        if not sep or not rid or source not in _SOURCE_PRIORITY:
            raise RuntimeError(f"天津图书馆：未知 book_id 形态：{book_id}")
        members.append((source, rid))
    return sorted(members, key=lambda m: _SOURCE_PRIORITY.index(m[0]))


class _Client:
    """三源客户端：ALEPH 两源走家族原语，中新友好走 interlib 家族原语。"""

    def _search_aleph(self, source, keyword, page):
        """ALEPH 源：家族 search_raw（带 isbn 内部字段供归并）；失败上抛，容错在 search。"""
        return aleph.search_raw(_SOURCES[source], keyword, page=page)

    def _search_zxyh(self, keyword, page, limit):
        """中新友好源：家族 search_raw（带 isbn 内部字段）；失败上抛，容错在 search。"""
        zr = il_search(_ZXYH, keyword, page=page, limit=limit)
        return {
            "books": [
                _Book(record_id=f"ZXYH:{b['book_id']}", title=b["title"], author=b["author"],
                      publisher=b["publisher"], publish_year=b["publish_year"],
                      availability_summary=b["availability_summary"], isbn=b.get("isbn", ""))
                for b in zr["books"]
            ],
            "total_results": zr["total_results"],
            "total_pages": zr["total_pages"],
        }

    def search(self, keyword, page=1, limit=20):
        # 源级容错：≥1 源成功即返回存活源结果（数据原样）；三源全失败才报错
        per_source = {}
        errors = []
        for source in _SOURCES:
            try:
                per_source[source] = self._search_aleph(source, keyword, page)
            except _CaptchaError:
                raise  # 验证码墙是全局限速信号，快速失败给可操作提示
            except RuntimeError as e:
                errors.append(f"{_SOURCES[source].name_cn}：{e}")
        try:
            per_source["ZXYH"] = self._search_zxyh(keyword, page, limit)
        except RuntimeError as e:
            errors.append(f"{_ZXYH.name_cn}：{e}")
        if not per_source:
            raise RuntimeError("天津图书馆：三源检索均失败——" + "；".join(errors))
        books = _merge_books({s: r["books"] for s, r in per_source.items()})
        # 合计口径：任一存活源不提供总数（ZXYH 检索页无「检索到 N 条」）→ 合计不可知，
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

        容错口径：首成员（目标源）失败报错；附属源失败跳过，返回已查到部分。
        """
        holdings = []
        for i, (source, rid) in enumerate(_split_book_id(book_id)):
            try:
                holdings.extend(self._holdings_for(source, rid))
            except _CaptchaError:
                raise  # 封禁信号穿透聚合，不被附属源跳过逻辑静默
            except RuntimeError:
                if i == 0:
                    raise
        holdings.sort(key=lambda h: (not h.available, h.library))
        return holdings

    def _holdings_for(self, source, rid):
        """单成员馆藏：ZXYH 走家族原语，ALEPH 走 item-global 单册页。"""
        if source == "ZXYH":
            return [
                _Holding(library=h["library"], location=h["location"],
                         call_number=h["call_number"], status=h["status"],
                         available=h["available"], due_date=h.get("due_date", ""))
                for h in il_holdings(_ZXYH, rid, only_available=False)
            ]
        try:
            return aleph.get_holdings(_SOURCES[source], rid)
        except _CaptchaError:
            raise  # 封禁提示原样穿透，不加馆名包装
        except RuntimeError as e:
            raise RuntimeError(f"{_SOURCES[source].name_cn}馆藏查询失败：{e}") from e

    def get_book_detail(self, book_id):
        """复合 id 取优先级最高成员的详情；record_id 保留查询原样。目标源失败如实报错。

        ALEPH 详情走 SYS 系统号检索（单命中直出完整记录页，可无会话）；
        页内 full-set-set 链接是 set_number 会话形态，直连不可用（真网实测）。
        """
        source, rid = _split_book_id(book_id)[0]
        if source == "ZXYH":
            d = il_detail(_ZXYH, rid)
            return _Book(record_id=book_id, title=d["title"], author=d["author"],
                         publisher=d["publisher"], publish_year=d["publish_year"],
                         isbn=d["isbn"], call_number=d["call_number"],
                         summary=d["summary"])
        b = aleph.get_book_detail(_SOURCES[source], rid)
        return replace(b, record_id=book_id)

    def get_return_date(self, item_id):
        """天津无按单册查归还日期的接口：ALEPH 应还日期在单册页直取、ZXYH 在馆藏 JSON。

        天津馆藏不带 item_id，模块级 get_holdings 的补查分支真网永不触发；
        定义仅为对齐契约形状。
        """
        raise RuntimeError(f"天津图书馆：无单册归还日期接口：{item_id}")


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索三源合并馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"天津图书馆搜索失败：{result.error}")

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
        # 契约测试要求已借出且带单册 item_id 时查归还时间；天津馆藏无 item_id，真网不触发
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
