"""适配层统一入口：按地区 → 城市两级分派到具体适配器。

地区标识取域名后缀（ccTLD），默认 `cn`（中国）。每个地区是一个子包
（如 `cn/`），暴露 `ADAPTERS`（城市标识 → 模块）与 `NAME`（中文名，仅
供错误提示）。新增地区 = 新建子包 + 在 `_REGION_MODULES` 注册一行；
新增城市 = 在对应地区子包的 `ADAPTERS` 里注册一行。server 层与具体城市解耦。
"""
from . import cn

_REGION_MODULES = {
    "cn": cn,
}

# 地区标识 → 城市标识 → 适配器模块
_ADAPTERS = {code: mod.ADAPTERS for code, mod in _REGION_MODULES.items()}

# 地区中文名，仅供错误提示展示。
_REGIONS = {code: mod.NAME for code, mod in _REGION_MODULES.items()}


def _get(region: str, city: str):
    by_city = _ADAPTERS.get((region or "cn").lower())
    if by_city is None:
        supported = "、".join(f"{code}（{name}）" for code, name in sorted(_REGIONS.items()))
        raise RuntimeError(f"该地区暂未接入：{region}。当前支持：{supported}")
    adapter = by_city.get(city.lower())
    if adapter is None:
        supported = "、".join(sorted(by_city))
        raise RuntimeError(f"该城市暂未接入：{city}。当前支持：{supported}")
    return adapter


def search_books(region: str, city: str, keyword: str, page: int = 1, limit: int = 20) -> dict:
    return _get(region, city).search_books(keyword, page=page, limit=limit)


def get_holdings(region: str, city: str, book_id: str, only_available: bool = True) -> list[dict]:
    return _get(region, city).get_holdings(book_id, only_available=only_available)


def get_book_detail(region: str, city: str, book_id: str) -> dict:
    return _get(region, city).get_book_detail(book_id)
