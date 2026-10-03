"""SirsiDynix Enterprise/VSE 家族共享模块。

成员：郑州图书馆（`adapters/cn/zhengzhou.py`）。站点是 SirsiDynix Enterprise
（Portfolio 4.3，Tapestry 5.3.3 服务端渲染），与本仓库既有的 Interlib/UILAS/
LibStar 等 JSON 系均不同：检索与详情是 HTML，馆藏＝详情页内联单册表 ＋
懒加载的可用性 JSON。HTTP 层见 `client.py`，解析见 `parser.py`。

三原语：
- 检索 `GET {ctx}/search/results?qu=&te=ILS[&rw=]`（HTML）。
- 详情 `GET {ctx}/search/detailnonmodal?d=&te=ILS&ps=300`（HTML）。
- 馆藏：详情页内联单册表 ＋ `loadavailability` JSON（`X-Requested-With` 必需）。

`book_id` 是 SirsiDynix 实体 URI（`ent://SD_ILS/<lib>/<id>`）。
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import client, parser

if TYPE_CHECKING:
    from ..adapters.base import BookDetail, Holding, SearchPage

# detailnonmodal 的 d 参数：Tapestry 需实体串后随 `~ILS~0~<n>` 才认；n 任意。
# 原值交给 client 的 urlencode 编码，勿预编码（否则被二次编码成 %25 而失效）。
_D_SUFFIX = "~ILS~0~0"
_AVAIL_URL_RE = re.compile(
    r'"(/client/[^"]*loadavailability/[^"]+)"')


@dataclass(frozen=True)
class SirsiEntConfig:
    """SirsiDynix Enterprise 站点配置。quirk 字段必须带默认值。"""

    city: str           # 城市标识，如 "zhengzhou"
    name_cn: str        # 报错与文档用的中文名
    base_url: str       # 站点根地址，不含末尾斜杠
    ctx: str = "/client/zh_CN/default"  # 应用上下文（语言/皮肤路径）
    page_size: int = 12                  # 站点每页固定 12 条（limit 不生效）


def _fetch_detail(cfg: SirsiEntConfig, book_id: str) -> tuple[str, dict]:
    """取详情页 HTML 与合并后的可用性 JSON。"""
    html = client.get(cfg, f"{cfg.ctx}/search/detailnonmodal",
                      {"d": book_id + _D_SUFFIX, "te": "ILS", "ps": "300"})
    ids: list = []
    strings: list = []
    total_available = 0
    for raw in _AVAIL_URL_RE.findall(html):
        path = raw.replace("&amp;", "&")
        try:
            body = client.get(cfg, path, ajax=True)
            payload = json.loads(body)
        except (RuntimeError, ValueError):
            continue
        ids.extend(payload.get("ids") or [])
        strings.extend(payload.get("strings") or [])
        try:
            total_available += int(payload.get("totalAvailable") or 0)
        except (TypeError, ValueError):
            pass
    return html, {"ids": ids, "strings": strings, "totalAvailable": total_available}


def search_books(cfg: SirsiEntConfig, keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键字检索馆藏。站点每页固定 page_size 条，limit 不生效（同南京口径）。"""
    params = {"qu": keyword, "te": "ILS"}
    if page > 1:
        params["rw"] = (page - 1) * cfg.page_size
    html = client.get(cfg, f"{cfg.ctx}/search/results", params)
    r = parser.parse_search(html)
    total = r["total_results"]
    total_pages = math.ceil(total / cfg.page_size) if total > 0 else 0
    return {
        "total_results": total,
        "page": page,
        "total_pages": total_pages,
        "has_next": page * cfg.page_size < total,
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


def get_holdings(cfg: SirsiEntConfig, book_id: str,
                 only_available: bool = True) -> list[Holding]:
    """指定书目在各分馆的馆藏与可借状态，可借的排前面。"""
    html, avail = _fetch_detail(cfg, book_id)
    holdings: list[Holding] = []
    for h in parser.parse_holdings(html, avail):
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


def get_book_detail(cfg: SirsiEntConfig, book_id: str) -> BookDetail:
    """指定书目的完整介绍（ISBN、索书号、内容简介）。失败抛 RuntimeError。"""
    html, _ = _fetch_detail(cfg, book_id)
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
