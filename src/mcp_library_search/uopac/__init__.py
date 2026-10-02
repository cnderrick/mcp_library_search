"""汇文 Libsys/uopac 家族模块：南京金陵源（`uopac.jllib.cn`）与扬州共用。

城市差异只允许以带默认值的 UopacConfig 字段（quirk）新增，默认值即金陵行为；
禁止改变本模块对外函数签名。

对外的原语返回家族内部结构（Book/Holding），供各适配器做城市级包装与跨源归并——
统一模型（base.py 的 TypedDict）的包装留在各适配器。

两站唯一的行为差异是传输层的 securitycam cookie（扬州有、金陵无），已收进
UopacConfig.securitycam；页面结构差异目前为零，将来若分叉，按 interlib 家族
「带默认值的开关」先例加 quirk 字段，别复制解析副本。
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

from . import client  # HTTP 层（测试的 monkeypatch 注入点：client.get）
from . import parser
from .parser import Book, Holding, SearchResult, isbn_wildcard, looks_like_isbn

__all__ = [
    "Book", "Holding", "SearchResult", "UopacConfig", "check_id", "client",
    "get_book_detail", "get_holdings", "get_holding_tabs", "isbn_wildcard",
    "looks_like_isbn", "parser", "search_raw",
]


@dataclass(frozen=True)
class UopacConfig:
    """汇文 uopac 系站点的单源配置。"""

    name_cn: str          # 报错与文档用的中文名
    base_url: str         # 站点根地址，不含末尾斜杠，如 "http://uopac.jllib.cn"
    securitycam: str = ""  # 非空即带该值的 securitycam cookie（扬州站静态挑战）
    throttle: float = 4.0  # 秒/host，按 spec 保守限速
    timeout: float = 90.0  # 秒；源站偶发慢响应（侦察与冒烟各实测一次），放宽


def check_id(cfg: UopacConfig, rid: str) -> str:
    """book_id 必须是 uopac 原生数字 id（源前缀由各适配器剥掉后再传进来）。"""
    s = str(rid or "").strip()
    if not s.isdigit():
        raise RuntimeError(f"{cfg.name_cn}：book_id 格式应为 uopac 数字 id：{rid}")
    return s


def search_url(cfg: UopacConfig, keyword: str, page: int = 1) -> str:
    """检索 URL：ISBN 形态关键词走 meta=14 且数字间插 * 通配（NOTES.md 实证）。"""
    if looks_like_isbn(keyword):
        params = {"q": isbn_wildcard(keyword), "meta": "14", "page": str(page)}
    else:
        params = {"q": str(keyword or ""), "meta": "20", "page": str(page)}
    return f"{cfg.base_url}/uopac/s/search_result.action?" + urllib.parse.urlencode(params)


def search_raw(cfg: UopacConfig, keyword: str, page: int = 1, limit: int = 20,
               prefix: str = "") -> dict:
    """检索并返回 parser 原始结构（books 条目含 isbn 内部字段，供跨源归并）。

    源站每页固定 20 条，limit 参数不生效（数据边界，翻页请用 page）。
    prefix 是 book_id 源前缀（双源城市用，如金陵 "JL:"；单源城市传空串）。
    响应不是结果页即抛含馆名的 RuntimeError，不静默当空结果。
    """
    text = client.get(search_url(cfg, keyword, page), cfg)
    if parser.RESULT_MARK not in text:
        raise RuntimeError(f"{cfg.name_cn}：检索未返回结果页（可能被拦截或接口变更）")
    return parser.parse_search(text, prefix)


def _detail_page(cfg: UopacConfig, rid: str):
    """详情页原文（详情与馆藏 tab 都从它取）。"""
    return client.get(
        f"{cfg.base_url}/uopac/s/detail.action?id={check_id(cfg, rid)}", cfg)


def get_holding_tabs(cfg: UopacConfig, rid: str) -> list:
    """[(持有馆名, ajax 馆藏表绝对 URL)]——每持有馆一条。"""
    return parser.parse_tabs(_detail_page(cfg, rid), cfg.base_url)


def get_holdings(cfg: UopacConfig, rid: str) -> list:
    """该书全部持有馆的单册级 Holding（不筛可借性，口径由适配器定）。

    每持有馆一次代理请求（1+N）。某馆代理失败（成员馆不可达等）→ 该馆 0 条，
    不拖垮整体；详情页本身失败则如实抛错。
    """
    holdings = []
    for library, url in get_holding_tabs(cfg, rid):
        try:
            text = client.get(url, cfg)
        except RuntimeError:
            continue
        holdings.extend(parser.parse_holding_rows(text, library))
    return holdings


def get_book_detail(cfg: UopacConfig, rid: str) -> Book:
    """书目详情。响应无题名（非详情页）→ 抛含馆名的 RuntimeError。"""
    d = parser.parse_detail(_detail_page(cfg, rid))
    if not d["title"]:
        raise RuntimeError(f"{cfg.name_cn}：未找到该书详情：{rid}")
    return Book(
        record_id=str(rid),
        title=d["title"],
        author=d["author"],
        publisher=d["publisher"],
        publish_year=d["publish_year"],
        isbn=d["isbn"],
        call_number=d["call_number"],
        summary=d["summary"],
    )
