"""杭州适配器委托测试：验证薄包装对双源接口的调用参数与 config。

双源合并重构后：HZ 源走 interlib.search_raw（带 isbn 内部字段供归并，
不再是 search_books），ZJ 源走 _zjlib。这里用 monkeypatch 替换两源的
取数函数，只验证「杭州适配器是否把 InterlibConfig 正确传给家族接口、
book_id 是否带 HZ: 前缀、裸 id 是否仍按兼容垫片路由 HZ」，不打真网。
"""
from mcp_library_search.adapters.cn import hangzhou


def _zj_empty():
    return {"books": [], "total_results": 0, "total_pages": 0, "has_next": False}


def test_config_and_delegation(monkeypatch):
    from mcp_library_search.interlib import InterlibConfig

    seen = {}

    def fake_search(cfg, keyword, page=1, limit=20):
        seen["cfg"] = cfg
        # search_raw 原始结构：books 条目带 isbn 内部字段（供跨源归并）
        return {"total_results": 1, "total_pages": 1, "has_next": False,
                "books": [{"book_id": "123456", "title": "三体", "author": "刘慈欣",
                           "publisher": "重庆出版社", "publish_year": "2008",
                           "availability_summary": "", "isbn": "9787536692930"}]}

    monkeypatch.setattr("mcp_library_search.interlib.search_raw", fake_search)
    monkeypatch.setattr("mcp_library_search.adapters.cn._zjlib.search",
                        lambda keyword, page=1, limit=20: _zj_empty())
    page = hangzhou.search_books("三体", page=2, limit=5)
    # 合计口径＝存活源之和（HZ 1 ＋ ZJ 0）
    assert page["total_results"] == 1
    # 家族 book_id → 契约 record_id 的映射在 _Client.search 内完成（真网冒烟曾抓到此回归）；
    # 合并重构后输出形态升级为带前缀 HZ:{bookrecno}（裸 id 仍兼容，仅限输入侧）
    assert page["books"][0]["book_id"] == "HZ:123456"
    assert page["books"][0]["title"] == "三体"
    assert seen["cfg"] == InterlibConfig(
        city="hangzhou", name_cn="杭州图书馆", base_url="https://my1.zjhzlib.cn"
    )


def test_holdings_and_detail_delegate(monkeypatch):
    # 裸数字 id（0.3.0 已上线形态）→ 兼容垫片路由 HZ，不触浙图源
    zj_calls = []
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_holdings",
        lambda cfg, book_id, only_available=True: [
            {"library": "x", "location": "", "call_number": "", "status": "在馆",
             "available": True, "due_date": ""},
        ],
    )
    monkeypatch.setattr(
        "mcp_library_search.interlib.get_book_detail",
        lambda cfg, book_id: {"book_id": book_id, "title": "三体", "author": "刘慈欣",
                              "publisher": "重庆出版社", "publish_year": "2008",
                              "isbn": "", "call_number": "", "summary": ""},
    )
    monkeypatch.setattr("mcp_library_search.adapters.cn._zjlib.get_holdings",
                        lambda rid: zj_calls.append(f"holdings:{rid}") or [])
    monkeypatch.setattr("mcp_library_search.adapters.cn._zjlib.get_work_detail",
                        lambda rid: zj_calls.append(f"detail:{rid}") or {})
    hs = hangzhou.get_holdings("123", only_available=False)
    assert hs[0]["library"] == "x" and hs[0]["available"] is True
    assert hangzhou.get_book_detail("123")["title"] == "三体"
    assert zj_calls == []
