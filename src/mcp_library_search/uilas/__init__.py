"""UILAS（ILAS 系）家族共享模块：金华市图书馆、舟山市图书馆共用。

UILAS 知识检索平台（ILAS 系 HTML OPAC，Tomcat/JSP），与深圳的自研 JSON API
封装不同、不可复用。城市差异只允许以带默认值的 `UilasConfig` 字段（quirk）新增，
默认值即金华行为。HTTP 层见 `client.py`，页面解析见 `parser.py`。

`book_id` 为裸 recno（纯数字），检索 POST `NTRdrBookRetr.do`、翻页 GET 带
`nCurrentpage`（`SearchKey` 双重 URL 编码）、详情 GET `NTRdrBookRetrInfo.do?recno=`
（馆藏内联在详情页 `div#BookHolding`）。
"""
from __future__ import annotations

import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import client
from . import parser

if TYPE_CHECKING:
    from ..adapters.base import BookDetail, Holding, SearchPage


@dataclass(frozen=True)
class UilasConfig:
    """UILAS 系图书馆的城市配置。quirk 字段必须带默认值。"""

    city: str        # 城市标识，如 "jinhua"
    name_cn: str     # 报错与文档用的中文名，如 "金华市图书馆"
    base_url: str    # 站点根地址（含 /ILASOPAC 一类上下文），不含末尾斜杠
    ssl_ciphers: str = ""  # 旧式 TLS 站点（舟山）显式放行的密码套件串，默认空＝默认上下文


def _fetch_search(cfg: UilasConfig, search_type: str, keyword: str, page: int, limit: int) -> str:
    headers = {"User-Agent": client._UA}
    if page <= 1:
        data = urllib.parse.urlencode({
            "searchType": search_type,
            "searchKey": keyword,
            "searchWay": "searchWayPrv",
            "pageNum": str(limit),
            "matchType": "pubyear",
            "matchSort": "desc",
        }).encode()
        req = urllib.request.Request(
            f"{cfg.base_url}/NTRdrBookRetr.do", data=data, headers=headers)
    else:
        # 页内翻页链接原样（NOTES.md）：GET 带 nCurrentpage，SearchKey 双重
        # URL 编码——先 quote 一层，urlencode 再编码一层
        params = urllib.parse.urlencode({
            "nCurrentpage": str(page),
            "SearchType": search_type,
            "SearchKey": urllib.parse.quote(keyword, safe=""),
            "PageNum": str(limit),
            "searchWay": "searchWayPrv",
            "matchType": "pubyear",
            "matchSort": "desc",
        })
        req = urllib.request.Request(
            f"{cfg.base_url}/NTRdrBookRetr.do?{params}", headers=headers)
    return client.open(cfg, req)


def _fetch_detail(cfg: UilasConfig, recno: str) -> str:
    url = f"{cfg.base_url}/NTRdrBookRetrInfo.do?recno={recno}&libid="
    req = urllib.request.Request(url, headers={"User-Agent": client._UA})
    text = client.open(cfg, req)
    if "书目详细信息" not in text:
        raise RuntimeError(f"{cfg.name_cn}：详情页获取失败（响应无「书目详细信息」标记）：{recno}")
    return text


def search_raw(cfg: UilasConfig, keyword: str, page: int = 1, limit: int = 20) -> dict:
    """检索并返回 parser 原始结构；search_books 是它的契约形态包装。"""
    search_type = "isbnsrh" if parser.looks_like_isbn(keyword) else "text"
    text = _fetch_search(cfg, search_type, keyword, page, limit)
    if not parser.is_result_page(text):
        # 匿名可通无会话可重建；总数锚点缺失＝响应不是结果页，如实报错
        raise RuntimeError(
            f"{cfg.name_cn}：检索未返回结果页（响应缺总数锚点，可能被源站拦截或改版）")
    return parser.parse_search(text)


def search_books(cfg: UilasConfig, keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键字检索馆藏，返回统一分页结构。失败抛 RuntimeError（消息含中文馆名）。"""
    r = search_raw(cfg, keyword, page, limit)
    total_pages = r["total_pages"]
    return {
        "total_results": r["total_results"],
        "page": page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "books": [
            {
                "book_id": b["book_id"],
                "title": b["title"],
                "author": b["author"],
                "publisher": b["publisher"],
                "publish_year": b["publish_year"],
                "availability_summary": b.get("availability_summary", ""),
            }
            for b in r["books"]
        ],
    }


def get_holdings(cfg: UilasConfig, book_id: str, only_available: bool = True) -> list[Holding]:
    """指定图书的单册级馆藏，可借的排前面。失败抛 RuntimeError。

    状态词表仅「入藏（可借）/借出」，词表外保守不可借；借出单册源站不给应还
    日期 → due_date 恒空（数据边界，非故障）。
    """
    recno = parser.check_recno(book_id, cfg.name_cn)
    holdings: list[Holding] = []
    for h in parser.parse_holdings(_fetch_detail(cfg, recno)):
        if only_available and not h["available"]:
            continue
        holdings.append({
            "library": h["library"],
            "location": h["location"],
            "call_number": h["call_number"],
            "status": h["status"],
            "available": h["available"],
            "due_date": h["due_date"],
        })
    holdings.sort(key=lambda h: (not h["available"], h["library"]))
    return holdings


def get_book_detail(cfg: UilasConfig, book_id: str) -> BookDetail:
    """指定书目的完整介绍。失败抛 RuntimeError。

    内容简介取详情页内联「附注提要」原值；无附注则空串。
    """
    recno = parser.check_recno(book_id, cfg.name_cn)
    d = parser.parse_detail(_fetch_detail(cfg, recno))
    if not d["title"]:
        raise RuntimeError(f"{cfg.name_cn}：未找到该书详情：{book_id}")
    return {
        "book_id": recno,
        "title": d["title"],
        "author": d["author"],
        "publisher": d["publisher"],
        "publish_year": d["publish_year"],
        "isbn": d["isbn"],
        "call_number": d["call_number"],
        "summary": d["summary"],
    }
