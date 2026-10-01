"""统一返回模型：所有城市适配器的输出必须对齐这里的 TypedDict。

字段语义以注释为准。tests/test_adapter_contract.py 会对 _ADAPTERS 里每个
适配器做契约校验——新增城市对齐不对齐，测试直接红。
"""
import types as _types
import typing
from typing import Optional, TypedDict, get_type_hints


class BookSummary(TypedDict):
    """search_books 的列表条目：轻量书目信息，不带简介和馆藏明细。"""
    book_id: str               # 城市内稳定的不透明 ID，原样传给 find_book_availability / get_book_detail
    title: str
    author: str                # 没有则为空串
    publisher: str             # 没有则为空串
    publish_year: str          # 没有则为空串
    availability_summary: str  # 可借概况的简短文本，没有则为空串


class SearchPage(TypedDict):
    total_results: Optional[int]  # 匹配总数；None 表示数据源不提供总数
    page: int                     # 当前页码（从 1 开始）
    total_pages: int              # 总页数
    has_next: bool                # 是否还有下一页
    books: list[BookSummary]


class Holding(TypedDict):
    """单条馆藏记录。"""
    library: str      # 分馆名称
    location: str     # 馆内位置（楼层/室），没有则为空串
    call_number: str  # 索书号，没有则为空串
    status: str       # 原始状态文本，如"可借"、"已借出"
    available: bool   # 可借与否的归一化结果
    due_date: str     # 预计归还时间（YYYY-MM-DD），仅已借出馆藏可能非空


class BookDetail(TypedDict):
    book_id: str
    title: str
    author: str
    publisher: str
    publish_year: str
    isbn: str         # 没有则为空串
    call_number: str  # 没有则为空串
    summary: str      # 内容简介，没有则为空串


# ---------- 契约校验（测试用） ----------


def _check(value, ann, where: str) -> None:
    origin = typing.get_origin(ann)
    if origin is typing.Union or origin is _types.UnionType:  # Optional[X] / X | None
        if value is None:
            return
        for arg in typing.get_args(ann):
            if arg is not type(None):
                _check(value, arg, where)
        return
    if origin is list:
        if not isinstance(value, list):
            raise AssertionError(f"{where}: 期望 list，实际 {type(value).__name__}")
        (item_ann,) = typing.get_args(ann)
        for i, item in enumerate(value):
            _check(item, item_ann, f"{where}[{i}]")
        return
    if ann is int:
        if not (isinstance(value, int) and not isinstance(value, bool)):
            raise AssertionError(f"{where}: 期望 int，实际 {type(value).__name__}")
        return
    if typing.is_typeddict(ann):  # 嵌套模型，如 list[BookSummary] 里的 BookSummary
        if not isinstance(value, dict):
            raise AssertionError(f"{where}: 期望 {ann.__name__}（dict），实际 {type(value).__name__}")
        _check_model(value, ann, where)
        return
    if not isinstance(value, ann):
        raise AssertionError(f"{where}: 期望 {ann.__name__}，实际 {type(value).__name__}")


def _check_model(obj: dict, model: type[TypedDict], where: str) -> None:
    hints = get_type_hints(model)
    expected, actual = set(hints), set(obj)
    if expected != actual:
        raise AssertionError(
            f"{where}: 字段不匹配，缺 {sorted(expected - actual)}，多 {sorted(actual - expected)}"
        )
    for key, ann in hints.items():
        _check(obj[key], ann, f"{where}.{key}")


def validate_search_page(page: SearchPage) -> None:
    _check_model(page, SearchPage, "search_books")


def validate_holdings(holdings: "list[Holding]") -> None:
    _check(holdings, list[Holding], "get_holdings")


def validate_book_detail(detail: BookDetail) -> None:
    _check_model(detail, BookDetail, "get_book_detail")
