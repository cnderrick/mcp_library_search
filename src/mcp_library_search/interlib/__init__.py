"""图创 Interlib OPAC 家族模块：广州、杭州等城市共用。

接口契约见 docs/superpowers/specs/2026-10-01-three-city-adapters-design.md。
城市差异只允许以带默认值的 InterlibConfig 字段（quirk）新增，默认值即广州行为；
禁止改变本模块对外函数签名。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import client  # HTTP 层（测试的 monkeypatch 注入点：client.get）
from . import parser

if TYPE_CHECKING:
    from ..adapters.base import BookDetail, Holding, SearchPage


@dataclass(frozen=True)
class InterlibConfig:
    """Interlib 系图书馆的城市配置。

    quirk 字段（未来新增）必须带默认值，默认值即广州行为。
    """

    city: str       # 城市标识，如 "guangzhou"
    name_cn: str    # 报错与文档用的中文名，如 "广州图书馆"
    base_url: str   # OPAC 站点根地址，不含末尾斜杠，如 "https://opac.gzlib.org.cn"
    curlibcode: str = ""  # 多租户云托管馆按馆过滤（如 STC001），默认空 = 穗杭不带该参数


def _search_once(cfg: InterlibConfig, keyword: str, page: int, limit: int) -> dict:
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
    if cfg.curlibcode:
        params["curlibcode"] = cfg.curlibcode
    html = client.get(cfg, "/opac/search", params)
    return parser.parse_search(html)


def search_books(cfg: InterlibConfig, keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键字检索馆藏，返回统一分页结构。失败抛 RuntimeError（消息含中文馆名）。

    带连字符的 ISBN 在 marc 检索下命中不了（真网实测），首搜为空时
    去连字符重试一次。
    """
    r = _search_once(cfg, keyword, page, limit)
    if not r["books"] and "-" in keyword:
        retry = _search_once(cfg, keyword.replace("-", ""), page, limit)
        if retry["books"]:
            r = retry
    return {
        "total_results": r["total_results"],
        "page": page,
        "total_pages": r["total_pages"],
        "has_next": r["has_next"],
        "books": [
            {
                "book_id": b["book_id"],
                "title": b["title"],
                "author": b["author"],
                "publisher": b["publisher"],
                "publish_year": b["publish_year"],
                "availability_summary": b["availability_summary"],
            }
            for b in r["books"]
        ],
    }


def get_holdings(cfg: InterlibConfig, book_id: str, only_available: bool = True) -> list[Holding]:
    """指定书目在各分馆的馆藏与可借状态，可借的排前面。失败抛 RuntimeError。"""
    body = client.get(cfg, f"/opac/api/holding/{book_id}",
                      {"limitLibcodes": "", "isCluster": ""})
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{cfg.name_cn}：馆藏数据解析失败：{e}") from e
    holdings: list[Holding] = []
    for h in parser.parse_holdings(payload):
        available = parser.is_available_status(h["status"])
        if only_available and not available:
            continue
        holdings.append({
            "library": h["library"],
            "location": h["location"],
            "call_number": h["call_number"],
            "status": h["status"],
            "available": available,
            "due_date": h["due_date"],
        })
    holdings.sort(key=lambda h: (not h["available"], h["library"]))
    return holdings


def get_book_detail(cfg: InterlibConfig, book_id: str) -> BookDetail:
    """指定书目的完整介绍（ISBN、索书号、内容简介）。失败抛 RuntimeError。"""
    html = client.get(cfg, f"/opac/book/{book_id}")
    d = parser.parse_detail(html)
    if not d["title"]:
        raise RuntimeError(f"{cfg.name_cn}：未找到该书详情：{book_id}")
    return {
        "book_id": book_id,
        "title": d["title"],
        "author": d["author"],
        "publisher": d["publisher"],
        "publish_year": d["publish_year"],
        "isbn": d["isbn"],
        "call_number": d["call_number"],
        "summary": d["summary"],
    }
