"""适配层统一入口：按城市分派到具体适配器。

新增一座城市 = 在 adapters/ 下新建一个模块，实现 search_books / get_holdings /
get_book_detail 三个原语（返回结构对齐 base.py 的 TypedDict，由契约测试强制），
然后在本文件 _ADAPTERS 里注册一行。server 层与具体城市解耦。
"""
from . import shanghai
from . import shenzhen

_ADAPTERS = {
    "shanghai": shanghai,
    "shenzhen": shenzhen,
}

_SUPPORTED = "、".join(sorted(_ADAPTERS))


def _get(city: str):
    adapter = _ADAPTERS.get(city.lower())
    if adapter is None:
        raise RuntimeError(f"该城市暂未接入：{city}。当前支持：{_SUPPORTED}")
    return adapter


def search_books(city: str, keyword: str, page: int = 1, limit: int = 20) -> dict:
    return _get(city).search_books(keyword, page=page, limit=limit)


def get_holdings(city: str, book_id: str, only_available: bool = True) -> list[dict]:
    return _get(city).get_holdings(book_id, only_available=only_available)


def get_book_detail(city: str, book_id: str) -> dict:
    return _get(city).get_book_detail(book_id)
