"""Interlib 家族搜索结果解析测试（广州 fixture 钉死值）。"""
from mcp_library_search.interlib.parser import parse_search

P1 = open("tests/fixtures/guangzhou/search_p1.html", encoding="utf-8").read()
P2 = open("tests/fixtures/guangzhou/search_p2.html", encoding="utf-8").read()
EMPTY = open("tests/fixtures/guangzhou/search_empty.html", encoding="utf-8").read()


def test_p1_parses_books_with_stable_ids():
    r = parse_search(P1)
    assert len(r["books"]) == 10
    for b in r["books"]:
        assert set(b) == {"book_id", "title", "author", "publisher",
                          "publish_year", "availability_summary", "isbn"}
        assert b["book_id"].isdigit() and len(b["book_id"]) >= 6
        assert b["title"]
        assert b["availability_summary"] == ""
    # 钉死第一条（值以实抓 fixture 为准）
    assert r["books"][0]["book_id"] == "3004742677"
    assert r["books"][0]["title"] == "无论如何都要活著"
    assert r["books"][0]["author"] == "朝井辽Ryo Asai著"
    assert r["books"][0]["publisher"] == "采实文化事业股份有限公司"
    assert r["books"][0]["publish_year"] == "2021"
    # isbn 来自条目内 expressServiceTab 的 express_isbn 属性（内部字段，
    # 不进 BookSummary 契约；天津三源 ISBN 归并用）
    assert r["books"][0]["isbn"] == "978-986-507-471-5"


def test_zxyh_tenant_search_carries_isbn():
    z = open("tests/fixtures/tianjin/find_zxyh.html", encoding="utf-8").read()
    r = parse_search(z)
    by_id = {b["book_id"]: b for b in r["books"]}
    assert by_id["217795"]["isbn"] == "978-7-5366-9293-0"
    assert by_id["217795"]["title"] == "三体"


def test_p1_pagination_semantics():
    r = parse_search(P1)
    assert r["total_results"] == 2763
    assert r["total_pages"] == 277
    assert r["has_next"] is True


def test_p2_is_different_page():
    r1, r2 = parse_search(P1), parse_search(P2)
    assert [b["book_id"] for b in r1["books"]] != [b["book_id"] for b in r2["books"]]
    assert r2["books"][0]["book_id"] == "3003800012"


def test_empty_search_yields_nothing():
    r = parse_search(EMPTY)
    assert r["books"] == []
    assert r["total_results"] == 0
    assert r["has_next"] is False
    # 无分页控件时 total_pages 保守取当前页
    assert r["total_pages"] == 1


def test_text_label_fallback_without_link_classes():
    """默认模板变体（铜陵实抓）：著者/出版社锚点无 author-link/publisher-link class。

    家族 parser 用同层前置文本「著者:」「出版社:」兜底，值取紧随的无 class 锚点；
    广州等带 class 的城市仍优先按 class 命中，不受影响。
    """
    t = open("tests/fixtures/tongling/search_p1.html", encoding="utf-8").read()
    assert "author-link" not in t and "publisher-link" not in t
    r = parse_search(t)
    first = r["books"][0]
    assert first["book_id"] == "334623"
    assert first["title"] == "三体"
    assert first["author"] == "刘慈欣著"
    assert first["publisher"] == "重庆出版社"
