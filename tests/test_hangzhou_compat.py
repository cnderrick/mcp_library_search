"""杭州 OPAC 结构与 Interlib 家族模块假设的兼容性证据。

这些测试不跑家族解析器（那是 feature/guangzhou 分支的代码），
只验证杭州页面含家族解析器依赖的结构标记。合流后若有标记缺失，
说明杭州需要 quirk 回调，集成者据此处理。详见 fixtures/hangzhou/NOTES.md。
"""
import re
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "hangzhou"

SEARCH = (FIXTURES / "search_p1.html").read_text(encoding="utf-8")
EMPTY = (FIXTURES / "search_empty.html").read_text(encoding="utf-8")
DETAIL = (FIXTURES / "detail.html").read_text(encoding="utf-8")


def test_search_uses_bookrecno_anchors():
    # 书目锚点是「bookDetail( 后跟数字」。空结果页里那处 bookDetail( 是页面自带的
    # JS 函数定义 function bookDetail(bookrecno,index,flag){，不是书目锚点，
    # 所以这里按「后跟数字」匹配，家族解析器也应如此。
    assert re.search(r"bookDetail\(\d+", SEARCH)
    assert not re.search(r"bookDetail\(\d+", EMPTY)


def test_empty_page_reports_zero_results():
    assert "检索到: 0 条结果" in EMPTY


def test_detail_has_holdings_markers():
    # spec 里广州依赖的「馆藏浏览」锚点杭州没有（计数 0），杭州用「馆藏地点」表述。
    assert "馆藏地点" in DETAIL or "馆藏地" in DETAIL


def test_detail_holdings_come_from_json_api():
    # 杭州馆藏不在详情页 HTML 内联，而是单独 JSON 接口 /opac/api/holding/{bookrecno}。
    assert "/opac/api/holding/" in DETAIL


def test_interlib_fingerprint():
    assert "interlib" in DETAIL.lower() or "interlib" in SEARCH.lower()
