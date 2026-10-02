"""杭州适配器：杭州图书馆（Interlib 家族，HZ:）＋ 浙江图书馆（自研 JSON，ZJ:）双源合并。

book_id 形态：HZ:{bookrecno} / ZJ:{originalId}；跨源同 ISBN 命中合成复合 id
（成员按优先级 HZ > ZJ 以 + 连接，书目字段取 HZ 成员原值）。
**向后兼容**：0.3.0 已上线的裸数字 book_id（无前缀）一律视为 HZ 成员路由
（兼容垫片），搜索新返回的 book_id 一律带前缀。
杭图结构见 tests/fixtures/hangzhou/NOTES.md；浙图接口形态、状态码表与数据
边界（访客拿不到应还日期）见 tests/fixtures/zjlib/NOTES.md。

薄包装 + 契约测试兼容缝：公开原语全部经由模块级 _client 取数，
契约测试（tests/test_adapter_contract.py）monkeypatch 的就是这个 _client，
因此不能把三个原语写成对 interlib/_zjlib 函数的直连委托——那样 mock 会
落空、测试会真打图书馆网站。
"""
import re
from dataclasses import dataclass, field, replace

from ... import interlib
from ...interlib import InterlibConfig
from . import _zjlib
from ..base import BookDetail, BookSummary, Holding, SearchPage

_CONFIG = InterlibConfig(
    city="hangzhou", name_cn="杭州图书馆", base_url="https://my1.zjhzlib.cn"
)
# 归并优先级：杭州图书馆 > 浙江图书馆（复合 book_id 成员顺序与主记录取值同源）
_SOURCE_PRIORITY = ("HZ", "ZJ")
_SOURCE_NAMES = {"HZ": "杭州图书馆", "ZJ": "浙江图书馆"}


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


# ---- ISBN 归并与复合 book_id（口径同天津，见 tests/fixtures/tianjin/NOTES.md） ----

def _looks_like_isbn(text):
    """ISBN 形态判断：去连字符后 13 位（978/979 开头）或 10 位（末位可为 X）。"""
    s = str(text or "").replace("-", "").strip()
    if len(s) == 13 and s.isdigit():
        return s[:3] in ("978", "979")
    if len(s) == 10 and s[:9].isdigit():
        return s[9].isdigit() or s[9] in "Xx"
    return False


def _norm_isbn(isbn):
    """ISBN 归一归并键：去连字符与空白并转大写。

    浙图原值带脏后缀（如「9784152098702 :」，tests/fixtures/zjlib/NOTES.md），
    整体不合形态时按 ISBN 形态口径从脏串中提取（带数字边界断言，防误取长数字
    串片段）。仅作归并键使用，展示字段保持原值。非 ISBN 形态返回空串（不参与归并）。
    """
    s = re.sub(r"[\s-]", "", str(isbn or "")).upper()
    if _looks_like_isbn(s):
        return s
    m = re.search(r"(?<!\d)(?:97[89]\d{10}|\d{9}[\dX])(?!\d)", s)
    return m.group(0) if m else ""


def _merge_books(per_source):
    """跨源按归一 ISBN 归并：{source: [ _Book ]} → 归并后的 _Book 列表。

    口径（同天津 _merge_books）：
    - 同一 ISBN 每源至多一个成员（源内同 ISBN 多条——多卷/重印——保留首条）；
    - 多源命中合成复合 record_id（成员以 + 连接，按优先级 HZ > ZJ 排序），
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
    """复合/单成员 book_id → 按优先级排序的 [(source, record_id)]；形态非法即抛错。

    兼容垫片：无前缀的裸数字 id 一律视为 HZ 成员——0.3.0 已上线的 hangzhou
    book_id 是裸 bookrecno，必须继续可用（浙图 originalId 也是纯数字，但从未
    以裸形态发布过，裸数字按发布史只会是杭图 id）。
    """
    members = []
    for part in str(book_id or "").split("+"):
        part = part.strip()
        source, sep, rid = part.partition(":")
        if not sep:
            if part.isdigit():
                source, rid = "HZ", part
            else:
                raise RuntimeError(f"杭州：未知 book_id 形态：{book_id}")
        if not rid or source not in _SOURCE_PRIORITY:
            raise RuntimeError(f"杭州：未知 book_id 形态：{book_id}")
        members.append((source, rid))
    return sorted(members, key=lambda m: _SOURCE_PRIORITY.index(m[0]))


class _Client:
    """双源客户端：HZ＝Interlib 家族原语，ZJ＝浙图 BFF JSON API（_zjlib）。"""

    def _search_hz(self, keyword, page, limit):
        """杭图源：家族 search_raw（带 isbn 内部字段供归并）；失败上抛，容错在 search。"""
        r = interlib.search_raw(_CONFIG, keyword, page=page, limit=limit)
        return self._wrap_search(r, "HZ")

    def _search_zj(self, keyword, page, limit):
        """浙图源：_zjlib.search（同样带 isbn 内部字段）；失败上抛，容错在 search。"""
        r = _zjlib.search(keyword, page=page, limit=limit)
        return self._wrap_search(r, "ZJ")

    @staticmethod
    def _wrap_search(r, source):
        return {
            "books": [
                _Book(record_id=f"{source}:{b['book_id']}", title=b["title"],
                      author=b["author"], publisher=b["publisher"],
                      publish_year=b["publish_year"],
                      availability_summary=b.get("availability_summary", ""),
                      isbn=b.get("isbn", ""))
                for b in r["books"]
            ],
            "total_results": r["total_results"],
            "total_pages": r["total_pages"],
            "has_next": r["has_next"],
        }

    def search(self, keyword, page=1, limit=20):
        # 源级容错：≥1 源存活即返回存活源结果（数据原样）；双源全失败才报错
        per_source = {}
        errors = []
        for source, fn in (("HZ", self._search_hz), ("ZJ", self._search_zj)):
            try:
                per_source[source] = fn(keyword, page, limit)
            except RuntimeError as e:
                errors.append(f"{_SOURCE_NAMES[source]}：{e}")
        if not per_source:
            raise RuntimeError("杭州：双源检索均失败——" + "；".join(errors))
        books = _merge_books({s: r["books"] for s, r in per_source.items()})
        # 合计口径（同天津）：任一存活源不提供总数 → 合计不可知，如实 None，
        # 不拿部分源的数编造全城总数
        totals = [r["total_results"] for r in per_source.values()]
        total = None if any(t is None for t in totals) else sum(totals)
        return _SearchResult(
            success=True,
            error="",
            statistics={
                "total_results": total,
                "page": page,
                "total_pages": max(r["total_pages"] for r in per_source.values()),
                "has_next": any(r["has_next"] for r in per_source.values()),
            },
            books=books,
        )

    def get_holdings(self, book_id):
        """复合 book_id 拆成员逐个查询后聚合（可借在前、馆名升序）；单成员与裸 id 同一路径。

        容错口径（同天津）：首成员（目标源）失败报错；附属源失败跳过，返回已查到部分。
        """
        holdings = []
        for i, (source, rid) in enumerate(_split_book_id(book_id)):
            try:
                holdings.extend(self._holdings_for(source, rid))
            except RuntimeError:
                if i == 0:
                    raise
        holdings.sort(key=lambda h: (not h.available, h.library))
        return holdings

    def _holdings_for(self, source, rid):
        """单成员馆藏：HZ 走家族原语（应还日期已在馆藏 JSON），ZJ 走 _zjlib 两跳链。"""
        if source == "ZJ":
            return [_Holding(**h) for h in _zjlib.get_holdings(rid)]
        return [_Holding(**h) for h in
                interlib.get_holdings(_CONFIG, rid, only_available=False)]

    def get_book_detail(self, book_id):
        """复合 id 取优先级最高成员的详情；record_id 保留查询原样。目标源失败如实报错。"""
        source, rid = _split_book_id(book_id)[0]
        d = (_zjlib.get_work_detail(rid) if source == "ZJ"
             else interlib.get_book_detail(_CONFIG, rid))
        return _Book(record_id=book_id, title=d["title"], author=d["author"],
                     publisher=d["publisher"], publish_year=d["publish_year"],
                     isbn=d["isbn"], call_number=d["call_number"],
                     summary=d["summary"])

    def get_return_date(self, item_id):
        """杭州无按单册查归还日期的接口：HZ 应还日期在馆藏 JSON 直取、ZJ 访客视角没有。

        杭州馆藏不带 item_id，模块级 get_holdings 的补查分支真网永不触发；
        定义仅为对齐契约形状。
        """
        raise RuntimeError(f"杭州：无单册归还日期接口：{item_id}")


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索双源合并馆藏。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"杭州图书馆搜索失败：{result.error}")

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
        # 契约测试要求已借出且带单册 item_id 时查归还时间；HZ 的应还日期已在
        # 馆藏 JSON 里解析、ZJ 访客视角恒空，真网 item_id 恒空不会走到这
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
