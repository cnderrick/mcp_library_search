"""杭州适配器委托测试：验证薄包装对 interlib 家族接口的调用参数与 config。

家族接口在本分支还是骨架（抛 NotImplementedError），所以这里用 monkeypatch
替换 mcp_library_search.interlib 的三个函数，只验证「杭州适配器是否把
InterlibConfig 正确传给家族接口、返回值是否原样透传」，不依赖家族实现。
"""
from mcp_library_search.adapters import hangzhou


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.interlib import InterlibConfig

    seen = {}

    def fake_search(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        return {"total_results": 0, "page": 1, "total_pages": 1,
                "has_next": False, "books": []}

    monkeypatch.setattr("mcp_library_search.interlib.search_books", fake_search)
    assert hangzhou.search_books("三体", page=2, limit=5) == {
        "total_results": 0, "page": 1, "total_pages": 1, "has_next": False, "books": [],
    }
    assert seen["cfg"] == InterlibConfig(
        city="hangzhou", name_cn="杭州图书馆", base_url="https://my1.zjhzlib.cn"
    )


def test_holdings_and_detail_delegate(monkeypatch):
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [{"library": "x", "available": True}],
    )
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "三体"},
    )
    assert hangzhou.get_holdings("123") == [{"library": "x", "available": True}]
    assert hangzhou.get_book_detail("123")["title"] == "三体"
