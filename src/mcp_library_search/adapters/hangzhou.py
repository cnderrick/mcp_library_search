"""杭州适配器：图创 Interlib 家族。"""
from .. import interlib
from ..interlib import InterlibConfig
from .base import BookDetail, Holding, SearchPage

_CONFIG = InterlibConfig(
    city="hangzhou", name_cn="杭州图书馆", base_url="https://my1.zjhzlib.cn"
)


def search_books(keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键词检索馆藏，委托给 interlib 家族接口。失败抛 RuntimeError。"""
    return interlib.search_books(_CONFIG, keyword, page=page, limit=limit)


def get_holdings(book_id: str, only_available: bool = True) -> list[Holding]:
    """指定书目在各分馆的馆藏与可借状态，可借的排前面。失败抛 RuntimeError。"""
    return interlib.get_holdings(_CONFIG, book_id, only_available=only_available)


def get_book_detail(book_id: str) -> BookDetail:
    """指定书目的完整介绍（ISBN、索书号、内容简介）。失败抛 RuntimeError。"""
    return interlib.get_book_detail(_CONFIG, book_id)
