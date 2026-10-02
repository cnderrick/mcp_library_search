"""青岛适配器：图创 Interlib 家族（检索走站点内嵌 Solr 通道）。

青岛市公共图书馆联合目录（http://124.129.202.157/opac/index，站点头部与 meta
keywords 自报的全称），全市 26 馆联合，主馆青岛市图书馆馆码 `QT`。

检索通道是本城相对广州基准的唯一结构差异：HTML 检索页 `/opac/search` 被滑动
验证码常态拦截（`slideVerify`，新会话首个检索请求即触发，非限速型，验证结果只
落在当次浏览器会话），但站点内嵌的 Solr 后端 `/opac/api/search` 开放且不经
验证码——检索原语改走该通道。Solr 侧形态（实抓验证，见
`tests/fixtures/qingdao/NOTES.md`）：

- 参数 `q` + `rows` + `page` + `wt=json`；服务端凭 `page` 自算
  `start = (page-1) × rows`，直接传 `start` 会被服务端忽略；
- 命中数在 `response.numFound`，书目在 `response.docs[]`，字段名带 `_meta`
  后缀（`title_meta`/`author_meta`/`publisher_meta`/`pubdate_meta`/`isbn_meta`），
  稳定 id 是 `docs[].id`，可直接用于详情与馆藏端点；
- `pubdate_meta` 可带月（如「2019.01」），取四位年份；
- 服务端默认 `fq` 是硬编码的状态白名单＋定位集合，自行追加 `fq` 会被整体覆盖；
  因此结果默认只含有馆藏的书目，`hasholding` 恒为 `y`（不构成可借概况）。

详情 `/opac/book/{id}` 与馆藏 `/opac/api/holding/{id}` 与广州基准完全同构，
且青岛详情无需 `curlibcode` 参数，直接复用家族 client 与 parser（family
`parse_detail`/`parse_holdings` 零改动全字段解析成功）。

节流：家族 client 无限速，本模块自带 ≥2 秒/host 保守节流（该站检索入口带
验证码门禁，实抓未观测到限频，仍留余量；单测 monkeypatch `_throttle` 关闭）。

薄包装 + 契约测试兼容缝同成都/台州：公开原语全部经由模块级 `_client` 取数，
契约测试（tests/test_adapter_contract.py）monkeypatch 的就是这个 `_client`，
因此不能把三个原语写成对底层函数的直连委托——那样 mock 会落空、
测试会真打图书馆网站。
"""
import json
import math
import re
import time
from dataclasses import dataclass
from types import SimpleNamespace

from .. import interlib
from ..interlib import InterlibConfig
from .base import BookDetail, BookSummary, Holding, SearchPage

_CONFIG = InterlibConfig(
    city="qingdao", name_cn="青岛市公共图书馆联合目录",
    base_url="http://124.129.202.157",
)

_THROTTLE = 2.0  # 秒/host 最小间隔（家族 client 无限速，本模块自带保守节流）
_last_request = 0.0

_YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def _throttle():
    """最小间隔限速：距上次请求不足 _THROTTLE 秒时睡足差值（单 host）。"""
    global _last_request
    wait = _THROTTLE - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    _last_request = time.monotonic()


def _clean(text):
    """Solr 字段值 → 原值字符串（None→空串），只去首尾空白，不改内容。"""
    if text is None:
        return ""
    return str(text).strip()


def _year(text):
    """pubdate_meta（「2017」/「2019.01」等）→ 四位年份；取不到返回空串。"""
    m = _YEAR_RE.search(str(text or ""))
    return m.group(0) if m else ""


def _parse_solr(payload):
    """Solr 检索响应（`wt=json`）→ 家族 search 原始结构（books + total_results）。

    `availability_summary` 恒空串：Solr 无逐书目可借概况，`hasholding` 因服务端
    默认 fq 限定而恒为 `y`（数据边界，原值不冒充概况）。

    缺少 `response` 键即视为接口形态漂移（Solr 出错时只返回 `responseHeader`＋
    `error`），抛错而非静默降级成 0 条结果。
    """
    if not isinstance(payload, dict) or "response" not in payload:
        raise RuntimeError(f"{_CONFIG.name_cn}：检索响应缺少 response（接口可能变更）")
    resp = payload.get("response") or {}
    try:
        total = int(resp.get("numFound") or 0)
    except (TypeError, ValueError):
        total = 0
    books = []
    for doc in resp.get("docs") or []:
        if not isinstance(doc, dict):
            continue
        book_id = _clean(doc.get("id"))
        if not book_id:
            continue
        books.append({
            "book_id": book_id,
            "title": _clean(doc.get("title_meta")),
            "author": _clean(doc.get("author_meta")),
            "publisher": _clean(doc.get("publisher_meta")),
            "publish_year": _year(doc.get("pubdate_meta")),
            "availability_summary": "",
        })
    return {"books": books, "total_results": total}


def _search_once(keyword, page, limit):
    params = {"q": str(keyword or ""), "rows": limit, "page": page, "wt": "json"}
    body = interlib.client.get(_CONFIG, "/opac/api/search", params)
    try:
        payload = json.loads(body)
    except ValueError as e:
        raise RuntimeError(
            f"{_CONFIG.name_cn}：检索响应不是 JSON（可能被拦截或接口变更）：{body[:120]}"
        ) from e
    r = _parse_solr(payload)
    total = r["total_results"]
    total_pages = math.ceil(total / limit) if total > 0 and limit > 0 else 0
    return {
        "books": r["books"],
        "total_results": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
    }


def _search_raw(keyword, page=1, limit=20):
    """检索并返回原始结构。

    镜像家族 `search_raw` 语义：带连字符的 ISBN 在 Solr 检索下同样命中不了
    （真网实测，同广州 marc 检索），首搜为空且关键词含连字符时去连字符重试一次。
    """
    r = _search_once(keyword, page, limit)
    if not r["books"] and "-" in str(keyword or ""):
        retry = _search_once(str(keyword).replace("-", ""), page, limit)
        if retry["books"]:
            r = retry
    return r


# ---------- 契约缝（与成都/台州/广州同款） ----------


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


class _Client:
    """把家族解析返回值包装成契约测试期望的 attribute 对象形态。"""

    def search(self, keyword, page=1, limit=20):
        _throttle()
        r = _search_raw(keyword, page=page, limit=limit)
        return SimpleNamespace(
            success=True,
            error="",
            statistics={"total_results": r["total_results"], "page": page,
                        "total_pages": r["total_pages"], "has_next": r["has_next"]},
            # 家族 TypedDict 用 book_id，契约形态用 record_id，此处显式映射
            books=[SimpleNamespace(record_id=b["book_id"], title=b["title"],
                                   author=b["author"], publisher=b["publisher"],
                                   publish_year=b["publish_year"],
                                   availability_summary=b["availability_summary"])
                   for b in r["books"]],
        )

    def get_holdings(self, book_id):
        # 馆藏 JSON 与广州基准完全同构，直接走家族原语（NOTES.md 实抓验证：
        # 4 条全部解析成功，含 26 馆 libcodeMap 与 22 项 holdStateMap）
        _throttle()
        hs = interlib.get_holdings(_CONFIG, book_id, only_available=False)
        return [_Holding(**h) for h in hs]

    def get_book_detail(self, book_id):
        # 青岛详情无需 curlibcode 参数（裸 GET 即 200），家族原语默认不带该参数
        _throttle()
        return SimpleNamespace(**interlib.get_book_detail(_CONFIG, book_id))


_client = _Client()


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词搜索青岛市公共图书馆联合目录。上游报错抛 RuntimeError。"""
    result = _client.search(keyword=keyword, page=page, limit=limit)
    if not result.success:
        raise RuntimeError(f"{_CONFIG.name_cn}搜索失败：{result.error}")

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
    """指定图书在各成员馆的馆藏与可借状态，可借的排前面。

    联合目录含市南/市北/李沧/崂山/城阳等区级馆与城市书房分馆，馆名原值照登。
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
        # 契约测试要求已借出且带单册 item_id 时查归还时间；Interlib 的应还日期
        # 已在馆藏 JSON 里解析（loanWorkMap.returnDate），真网 item_id 恒空不会走到这
        if not available and getattr(h, "item_id", ""):
            item["due_date"] = _client.get_return_date(h.item_id)
        items.append(item)
    items.sort(key=lambda h: (not h["available"], h["library"]))
    return items


def get_book_detail(book_id: str) -> BookDetail:
    """指定图书的完整详情：书名、作者、出版社、出版年、ISBN、索书号、内容简介。

    `call_number` 取详情页「中图分类法」值（家族口径）；页内另有独立「索书号」行
    不参与解析，完整索书号在馆藏明细 `call_number` 里。
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
