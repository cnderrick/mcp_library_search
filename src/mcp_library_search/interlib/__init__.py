"""图创 Interlib OPAC 家族模块：广州、杭州等城市共用。

接口契约见 docs/superpowers/specs/2026-10-01-three-city-adapters-design.md。
城市差异只允许以带默认值的 InterlibConfig 字段（quirk）新增，默认值即广州行为；
禁止改变本模块对外函数签名。
"""
from __future__ import annotations

import json
import math
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
    pro2018: bool = False          # 搜索/详情为 pro2018 模板代（台州/成都/绍兴），默认 False = 广州基准
    pro2018_cite_author: bool = False  # pro2018 详情以引文块首句兜底责任者（绍兴实证），默认关
    ctx: str = "/opac"             # 应用上下文路径（西安 `/opac3`、大庆根路径 `""`），默认广州基准 `/opac`
    api_detail: bool = False       # 详情改走 `/api/book/{recno}` JSON（安康详情页 HTML 被源站截断），默认 False = HTML 详情页
    solr_search: bool = False      # 检索改走站点内嵌 Solr `/api/search`（青岛及一批带滑动验证码的站点），默认 False = HTML 检索页
    f_curlibcode: str = ""         # 检索按 `f_curlibcode` 过滤（乐山借省图联合目录过滤乐山馆），默认空 = 不过滤
    captcha: bool = False          # 检索页为滑动验证码墙（乐山）：命中「opac验证」抛 CaptchaError，不破解


def _search_once(cfg: InterlibConfig, keyword: str, page: int, limit: int) -> dict:
    if cfg.solr_search:
        # 检索页被滑动验证码拦截的站点改走内嵌 Solr：q/rows/page/wt=json，
        # 服务端凭 page 自算 start（直传 start 被忽略），命中数在 response.numFound。
        body = client.get(cfg, f"{cfg.ctx}/api/search",
                          {"q": str(keyword or ""), "rows": limit, "page": page, "wt": "json"})
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"{cfg.name_cn}：检索响应不是 JSON（可能被拦截或接口变更）：{body[:120]}") from e
        r = parser.parse_solr(payload, cfg.name_cn)
        total = r["total_results"]
        total_pages = math.ceil(total / limit) if total > 0 and limit > 0 else 0
        return {"books": r["books"], "total_results": total,
                "total_pages": total_pages, "has_next": page < total_pages}
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
    if cfg.f_curlibcode:
        params["f_curlibcode"] = cfg.f_curlibcode
    html = client.get(cfg, f"{cfg.ctx}/search", params)
    if cfg.captcha:
        client.check_captcha(html, cfg)  # 验证码墙：抛 CaptchaError，不静默返回空结果
    parse = parser.parse_search_pro2018 if cfg.pro2018 else parser.parse_search
    return parse(html)


def search_raw(cfg: InterlibConfig, keyword: str, page: int = 1, limit: int = 20) -> dict:
    """检索并返回 parser 原始结构（books 条目含 isbn 内部字段）。

    供天津三源 ISBN 归并使用；search_books 是它的契约形态包装。
    带连字符的 ISBN 在 marc 检索下命中不了（真网实测），首搜为空时去连字符重试一次。
    Solr 通道下越界页同样返回空 books（numFound 不变），故判据用 total_results==0。
    """
    r = _search_once(cfg, keyword, page, limit)
    empty = (r["total_results"] == 0) if cfg.solr_search else (not r["books"])
    if empty and "-" in keyword:
        retry = _search_once(cfg, keyword.replace("-", ""), page, limit)
        if retry["books"]:
            r = retry
    return r


def search_books(cfg: InterlibConfig, keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键字检索馆藏，返回统一分页结构。失败抛 RuntimeError（消息含中文馆名）。"""
    r = search_raw(cfg, keyword, page, limit)
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
    body = client.get(cfg, f"{cfg.ctx}/api/holding/{book_id}",
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
    """指定书目的完整介绍（ISBN、索书号、内容简介）。失败抛 RuntimeError。

    多租户云托管馆（curlibcode 非空）详情 URL 必须带该参数，否则 HTTP 500
    （ZXYH 实测，见 tests/fixtures/tianjin/NOTES.md）。

    `api_detail=True` 时改走 `/api/book/{recno}` JSON（安康详情页 HTML 被源站
    截断，HTML 详情拿不到书目字段；该接口各 Interlib 站点均可通）。
    """
    params = {"curlibcode": cfg.curlibcode} if cfg.curlibcode else None
    if cfg.api_detail:
        body = client.get(cfg, f"{cfg.ctx}/api/book/{book_id}")
        try:
            d = parser.parse_detail_api(json.loads(body))
        except json.JSONDecodeError as e:
            raise RuntimeError(f"{cfg.name_cn}：详情数据解析失败：{e}") from e
    else:
        html = client.get(cfg, f"{cfg.ctx}/book/{book_id}", params)
        if cfg.pro2018:
            d = parser.parse_detail_pro2018(html, cite_author=cfg.pro2018_cite_author)
        else:
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
