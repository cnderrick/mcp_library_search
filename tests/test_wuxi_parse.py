"""无锡（图星 LibStar Find）解析测试：以 tests/fixtures/wuxi/ 实抓为准。

字段侦察结论（字段码表、状态词表、数据边界）全部见 tests/fixtures/wuxi/NOTES.md，
解析器以那份文档为准。
"""
import json
import pathlib

from mcp_library_search.adapters.cn import wuxi

_FIXTURES = pathlib.Path("tests/fixtures/wuxi")


def _load(name):
    return json.loads((_FIXTURES / name).read_text(encoding="utf-8"))


# ---------- 检索 ----------


def test_parse_search_reads_total_and_books():
    """numFound 是扁平数字；一页取回 searchResult 全部条目。"""
    r = wuxi._parse_search(_load("search_shangyin.json"))
    assert r["total_results"] == 83
    assert len(r["books"]) == 10


def test_parse_search_first_book_fields():
    """publisher 源站为 null → 空串；可借概况由 physicalCount/onShelfCountI 拼装。"""
    first = wuxi._parse_search(_load("search_shangyin.json"))["books"][0]
    assert first["book_id"] == "703048"
    assert first["title"] == "上瘾 : 让用户养成使用习惯的四大产品逻辑 : how to build habit-forming products"
    assert first["author"] == "(美)尼尔·埃亚尔(Nir Eyal), (美)瑞安·胡佛(Ryan Hoover)著"
    assert first["publisher"] == ""
    assert first["publish_year"] == "2017"
    assert first["availability_summary"] == "纸本5，可借4"


def test_parse_search_keeps_publisher_when_present():
    """有出版社的书目原值照登（同页第 4 条《思考上瘾》）。"""
    books = wuxi._parse_search(_load("search_shangyin.json"))["books"]
    sikao = next(b for b in books if b["book_id"] == "829436")
    assert sikao["publisher"] == "中国人民大学出版社"
    assert sikao["publish_year"] == "2022"


def test_parse_search_empty_result():
    """零命中：total_results=0 且 books 为空，不报错。"""
    r = wuxi._parse_search({"success": True, "errCode": 200, "data": {"numFound": 0, "searchResult": []}})
    assert r["total_results"] == 0
    assert r["books"] == []


def test_availability_summary_empty_when_on_shelf_count_missing():
    """`onShelfCountI` 可为 null（实抓 143656）——任一项缺失即留空串，不拿单项编造。"""
    payload = {"success": True, "errCode": 200, "data": {"numFound": 1, "searchResult": [
        {"recordId": "143656", "title": "活着", "physicalCount": 1, "onShelfCountI": None}]}}
    assert wuxi._parse_search(payload)["books"][0]["availability_summary"] == ""


def test_parse_search_error_is_not_silently_empty():
    """errCode 9999（缺 Referer 的兜底错误）必须上抛，不能冒充「无结果」。"""
    payload = {"success": False, "message": "系统访问中断，请稍后再试！", "errCode": 9999, "data": None}
    try:
        wuxi._parse_search(payload)
    except RuntimeError as e:
        assert "9999" in str(e) or "Referer" in str(e)
    else:
        raise AssertionError("errCode 9999 应当抛 RuntimeError，而不是静默返回 0 条")


# ---------- 详情 ----------


def test_parse_detail_full_record():
    """cnb01 按「题名/责任者」切分；cnb03 无出版社段时只出出版年。"""
    d = wuxi._parse_detail(_load("detail_shangyin.json"))
    assert d["title"] == "上瘾:让用户养成使用习惯的四大产品逻辑"
    assert d["author"] == "(美)尼尔·埃亚尔(Nir Eyal), (美)瑞安·胡佛(Ryan Hoover)著 钟莉婷，杨晓红译"
    assert d["publisher"] == ""
    assert d["publish_year"] == "2017"
    assert d["isbn"] == "978-7-5086-6831-4"
    assert d["call_number"] == "TB472"
    assert d["summary"].startswith("本书揭示了很多让用户形成使用习惯")


def test_parse_detail_splits_publisher_when_present():
    """cnb03 形态「出版地:出版社,年份」→ 出版社与年份各自解析。"""
    d = wuxi._parse_detail(_load("detail_sikao.json"))
    assert d["title"] == "思考上瘾"
    assert d["publisher"] == "中国人民大学出版社"
    assert d["publish_year"] == "2022"
    assert d["isbn"] == "978-7-300-30264-5"
    assert d["call_number"] == "B804"


def test_parse_detail_isbn_skips_price_only_line():
    """cnb04 可重复，首条可能是纯定价行（无 ISBN）——取首个真带 ISBN 的那条。

    实抓 764039 的 cnb04 依次是 '/271.00 (8册)' 与 '978-7-229-10062-9/271.00 (8册)'，
    照单取首条会把 ISBN 解析成空串。
    """
    d = wuxi._parse_detail(_load("detail_santi_death.json"))
    assert d["isbn"] == "978-7-229-10062-9"
    assert d["title"] == "三体:典藏版.Ⅲ.死神永生"


def test_parse_detail_year_ignores_month():
    """出版项带月份（实抓 `重庆,2016.6`）→ 四位年份；同青岛/重庆/宁波口径。"""
    assert wuxi._parse_detail(_load("detail_santi_death.json"))["publish_year"] == "2016"


def test_parse_detail_publisher_absent_is_empty_not_guessed():
    """`重庆,2016.6` 无出版社段（只有出版地）→ 空串，不拿出版地冒充出版社。"""
    assert wuxi._parse_detail(_load("detail_santi_death.json"))["publisher"] == ""


def test_parse_search_year_ignores_month():
    """检索结果的 publishYear 同样可带月（实抓 2016.6）。"""
    books = wuxi._parse_search(_load("search_santi.json"))["books"]
    death = next(b for b in books if b["book_id"] == "764039")
    assert death["publish_year"] == "2016"


# ---------- 馆藏 ----------


def test_parse_holdings_maps_status_and_due_date():
    """processType 两态：在架→可借；借出-应还日期:X→不可借并把日期解析出来。"""
    hs = wuxi._parse_holdings(_load("holdings_shangyin.json"))
    assert len(hs) == 5
    borrowed = next(h for h in hs if h["status"] == "借出-应还日期:2025-10-10")
    assert borrowed["available"] is False
    assert borrowed["due_date"] == "2025-10-10"
    on_shelf = next(h for h in hs if h["item_id"] == "1713365")
    assert on_shelf["status"] == "在架"
    assert on_shelf["available"] is True
    assert on_shelf["due_date"] == ""


def test_parse_holdings_library_location_and_call_number():
    """馆名取分组键；馆内位置取 locationName；索书号取 callNo。"""
    hs = wuxi._parse_holdings(_load("holdings_shangyin.json"))
    first = next(h for h in hs if h["item_id"] == "1762051")
    assert first["library"] == "无锡市新吴区图书馆"
    assert first["location"] == "伯渎河文化中心图书馆三层"
    assert first["call_number"] == "TB472/0027 2017 C:2"


def test_parse_holdings_unknown_status_is_conservatively_unavailable():
    """未观测状态：保守判不可借，status 原值照登（同重庆口径）。"""
    payload = {"success": True, "errCode": 200, "data": {"sortedList": {"某馆": {
        "libName": "某馆", "phyItemVo": [
            {"itemId": "1", "callNo": "X", "locationName": "二楼", "processType": "装订中"}]}}}}
    h = wuxi._parse_holdings(payload)[0]
    assert h["status"] == "装订中"
    assert h["available"] is False


def test_parse_holdings_empty_sorted_list():
    hs = wuxi._parse_holdings({"success": True, "errCode": 200, "data": {"sortedList": {}}})
    assert hs == []
