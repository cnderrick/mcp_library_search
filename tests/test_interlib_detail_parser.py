"""Interlib 详情页书目字段解析测试（广州 fixture 钉死值）。"""
from mcp_library_search.interlib.parser import parse_detail

HTML = open("tests/fixtures/guangzhou/detail.html", encoding="utf-8").read()


def test_detail_fields_present():
    d = parse_detail(HTML)
    assert set(d) == {"title", "author", "publisher", "publish_year",
                      "isbn", "call_number", "summary"}
    assert d["title"] == "无论如何都要活著"
    assert d["author"] == "朝井辽"          # 取第一个责任者链接文本，去掉责任方式
    assert d["publisher"] == "采实文化事业股份有限公司"
    assert d["publish_year"] == "2021"
    assert d["isbn"] == "978-986-507-471-5"  # 从「ISBN 价格：」混排值里提取
    assert d["call_number"] == "I313.45"     # 中图分类法取「版次」之前
    assert d["summary"].startswith("收录六则短篇")


def test_detail_missing_fields_are_empty_strings():
    d = parse_detail("<html><body>没有字段的页面</body></html>")
    assert d["isbn"] == "" and d["summary"] == "" and d["call_number"] == ""
    assert d["title"] == "" and d["author"] == "" and d["publisher"] == ""
    assert d["publish_year"] == ""
