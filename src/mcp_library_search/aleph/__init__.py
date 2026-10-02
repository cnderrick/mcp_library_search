"""Ex Libris ALEPH www_f_chi 家族模块：天津（主馆/少儿馆）、南京图书馆共用。

城市差异只允许以带默认值的 AlephConfig 字段（quirk）新增，默认值即天津行为；
禁止改变本模块对外函数签名。

对外的三个原语返回家族内部结构（Book/Holding），供各适配器做跨源归并——
统一模型（base.py 的 TypedDict）的包装留在各适配器，因为归并口径是城市级的。
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

from . import client  # HTTP 层（测试的 monkeypatch 注入点：client.get）
from . import parser
from .client import CaptchaError, check_captcha
from .parser import Book, Holding, SearchResult, looks_like_isbn

__all__ = [
    "AlephConfig", "Book", "CaptchaError", "Holding", "SearchResult",
    "client", "get_book_detail", "get_holdings", "looks_like_isbn",
    "parser", "search_raw",
]


@dataclass(frozen=True)
class AlephConfig:
    """ALEPH 系图书馆的单源配置。

    source 同时充当三个角色：`local_base` 检索库代码、`doc_library` 馆藏库代码、
    book_id 前缀——三者在实抓站点上取值一致（天津 TJL01/TJC01、南图 NJL01）。
    """

    source: str        # 库代码，如 "TJL01" / "NJL01"
    name_cn: str       # 报错与文档用的中文名
    base_url: str      # 站点根地址，不含末尾斜杠，如 "http://opacwh.tjl.tj.cn:8991"
    unblock_urls: str  # 验证码墙手动解封指引里列出的地址
    throttle: float = 4.0              # 秒/host：验证码墙按 IP 封，限速是硬约束
    item_global_all_params: bool = False  # item-global 必须带 year/volume/sub_library 空参（南图实证）


def _find_url(cfg: AlephConfig, request: str, find_code: str) -> str:
    return (f"{cfg.base_url}/F?func=find-b&request={urllib.parse.quote(request)}"
            f"&find_code={find_code}&local_base={cfg.source}")


def search_raw(cfg: AlephConfig, keyword: str, page: int = 1, limit: int = 20) -> dict:
    """检索并返回 parser 原始结构（books 条目含 isbn 内部字段）。

    供多源 ISBN 归并使用。翻页走同会话 short-jump：jump=(page-1)*10+1，
    必须用页内会话 URL（F/VV... 前缀）。失败抛 RuntimeError（消息含中文馆名）。
    """
    find_code = "ISB" if parser.looks_like_isbn(keyword) else "WRD"
    text = client.get(_find_url(cfg, keyword, find_code), cfg)
    check_captcha(text, cfg)
    if page > 1:
        m = parser.JUMP.search(text)
        if m:
            text = client.get(m.group(1) + str((page - 1) * parser.PAGE_SIZE + 1), cfg)
            check_captcha(text, cfg)
    return parser.parse_find(text, cfg.source)


def get_holdings(cfg: AlephConfig, doc_number: str) -> list[Holding]:
    """单册页 item-global → Holding 列表（不筛可借性，口径由适配器定）。

    南图实测：`year/volume/sub_library` 三个参数**可以留空但不能整个省略**，
    省略即返回「在服务器上没有找到所要查询的文件」错误页；天津省略无碍。
    """
    url = (f"{cfg.base_url}/F?func=item-global"
           f"&doc_library={cfg.source}&doc_number={doc_number}")
    if cfg.item_global_all_params:
        url += "&year=&volume=&sub_library="
    text = client.get(url, cfg)
    check_captcha(text, cfg)
    return parser.parse_item_global(text)


def get_book_detail(cfg: AlephConfig, doc_number: str) -> Book:
    """详情走 SYS 系统号检索：单命中直出完整记录页，无需先建立结果集会话。

    页内 full-set-set 链接是 set_number 会话形态，跨请求不可复用。失败抛 RuntimeError。
    """
    text = client.get(_find_url(cfg, doc_number, "SYS"), cfg)
    check_captcha(text, cfg)
    b = parser.parse_full_record(text, cfg.source)
    if b is None:
        raise RuntimeError(f"{cfg.name_cn}：未找到该书详情：{cfg.source}:{doc_number}")
    return b
