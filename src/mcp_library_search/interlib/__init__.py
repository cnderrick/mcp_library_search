"""图创 Interlib OPAC 家族模块：广州、杭州等城市共用。

接口契约见 docs/superpowers/specs/2026-10-01-three-city-adapters-design.md。
城市差异只允许以带默认值的 InterlibConfig 字段（quirk）新增，默认值即广州行为；
禁止改变本模块对外函数签名。
"""
from dataclasses import dataclass

from ..adapters.base import BookDetail, Holding, SearchPage


@dataclass(frozen=True)
class InterlibConfig:
    """Interlib 系图书馆的城市配置。

    quirk 字段（未来新增）必须带默认值，默认值即广州行为。
    """

    city: str       # 城市标识，如 "guangzhou"
    name_cn: str    # 报错与文档用的中文名，如 "广州图书馆"
    base_url: str   # OPAC 站点根地址，不含末尾斜杠，如 "https://opac.gzlib.org.cn"


def search_books(cfg: InterlibConfig, keyword: str, page: int = 1, limit: int = 20) -> SearchPage:
    """按关键字检索馆藏，返回统一分页结构。失败抛 RuntimeError（消息含中文馆名）。"""
    raise NotImplementedError("Interlib 家族模块尚未实现（feature/guangzhou 分支落地）")


def get_holdings(cfg: InterlibConfig, book_id: str, only_available: bool = True) -> list[Holding]:
    """指定书目在各分馆的馆藏与可借状态，可借的排前面。失败抛 RuntimeError。"""
    raise NotImplementedError("Interlib 家族模块尚未实现（feature/guangzhou 分支落地）")


def get_book_detail(cfg: InterlibConfig, book_id: str) -> BookDetail:
    """指定书目的完整介绍（ISBN、索书号、内容简介）。失败抛 RuntimeError。"""
    raise NotImplementedError("Interlib 家族模块尚未实现（feature/guangzhou 分支落地）")
