"""浙图 JSON 客户端测试：实抓 fixture 解析（tests/fixtures/zjlib/）＋ 合成边界样本。

解析函数是纯函数直接喂 fixture；网络层用 monkeypatch 替换模块 _open 合成
（含实抓的业务报错形态），不打真网。节流形态照 test_tianjin_throttle.py。
"""
import json
from pathlib import Path

import pytest

from mcp_library_search.adapters import _zjlib

FIX = Path(__file__).parent / "fixtures" / "zjlib"


def _load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


# ---- 检索 pageList ----

def test_parse_search_real_fixture():
    r = _zjlib.parse_search(_load("search.json")["data"])
    assert r["total_results"] == 1811  # 真实总数
    assert r["total_pages"] == 182
    assert r["has_next"] is True
    assert len(r["books"]) == 10
    b0 = r["books"][0]
    assert b0["book_id"] == "110000014412989"  # originalId 裸值，前缀由合并层加
    assert b0["title"] == "三体"
    assert b0["publish_year"] == "2019"           # dateIssue「2019.」→ 提取年份
    assert b0["isbn"] == "9784152098702 :"        # 脏值原样带出（清洗在归并层）
    assert b0["availability_summary"] == ""       # 检索记录无可借性字段（数据边界）
    # 中文版三体：与杭图源同 ISBN 的归并候选
    b1 = r["books"][1]
    assert b1["book_id"] == "11000002313805"
    assert b1["isbn"] == "978-7-5366-9293-0"


def test_parse_search_empty_fixture():
    r = _zjlib.parse_search(_load("search_empty.json")["data"])
    assert r["books"] == []
    assert r["total_results"] == 0
    assert r["total_pages"] == 0
    assert r["has_next"] is False


def test_parse_search_page2_fixture_disjoint():
    # 分页 current 真实生效（深圳曾踩「页码参数被静默忽略」的坑，此为探针存证）
    r2 = _zjlib.parse_search(_load("probe_page2.json")["data"])
    r1 = _zjlib.parse_search(_load("search.json")["data"])
    assert r2["has_next"] is True
    ids2 = {b["book_id"] for b in r2["books"]}
    assert not (ids2 & {b["book_id"] for b in r1["books"]})


def test_parse_search_drops_records_without_original_id():
    r = _zjlib.parse_search({"records": [{"title": ["x"], "originalId": []},
                                         {"title": ["y"], "originalId": ["9"]}],
                             "total": 2, "pages": 1, "current": 1})
    assert [b["book_id"] for b in r["books"]] == ["9"]


def test_search_posts_expected_body(monkeypatch):
    seen = {}

    def fake_open(req, timeout=20):
        seen["url"] = req.full_url
        seen["body"] = json.loads(req.data.decode("utf-8"))
        return _load("search.json")

    monkeypatch.setattr(_zjlib, "_open", fake_open)
    r = _zjlib.search("三体", page=2, limit=5)
    assert seen["url"].endswith("/search-admin-service/open-api/search/pageList")
    assert seen["body"]["current"] == 2 and seen["body"]["size"] == 5
    assert seen["body"]["query"][0] == {"key": "", "value": "三体",
                                        "condition": "and", "match": "phrase_fuzzy"}
    assert r["total_results"] == 1811


# ---- 详情 getWorkById ----

def test_parse_record_real_fixture():
    d = _zjlib.parse_record(_load("detail.json")["data"]["record"])
    assert d["title"] == "三体"
    assert d["author"] == "刘慈欣著"  # 责任方式后缀原值照登
    assert d["publisher"] == "重庆出版社"
    assert d["publish_year"] == "2008"
    assert d["isbn"] == "978-7-5366-9293-0"
    assert d["call_number"] == "I247.55"  # 中图分类法，与家族口径一致
    assert d["summary"] == "“地球往事”三部曲之一"
    assert d["work_id"] == "60204f08e60757b629109b158cfbf13f"


def test_parse_record_isbn_falls_back_to_pure():
    d = _zjlib.parse_record({"title": ["x"], "identifierIsbn": [""],
                             "identifierIsbnPure": ["9787536692930"]})
    assert d["isbn"] == "9787536692930"


def test_parse_record_summary_falls_back_to_abstract():
    d = _zjlib.parse_record({"title": ["x"], "description": [""],
                             "descriptionAbstract": ["摘要段一", "段二"]})
    assert d["summary"] == "摘要段一\n段二"


def test_get_work_detail_notfound_raises(monkeypatch):
    # 实抓形态：HTTP 200 ＋ code=500 success=false（probe_detail_notfound.json）
    monkeypatch.setattr(_zjlib, "_open",
                        lambda req, timeout=20: _load("probe_detail_notfound.json"))
    with pytest.raises(RuntimeError) as ei:
        _zjlib.get_work_detail("99999999999999")
    assert "服务器繁忙" in str(ei.value)  # 站点 desc 原值照登进报错


# ---- 馆藏 resourceList ----

def test_parse_holdings_real_fixture():
    hs = _zjlib.parse_holdings(_load("holdings.json")["data"]["0"])
    assert len(hs) == 28
    # 实抓状态分布：2 在馆×5、3 借出×20、9 锁定×1、16 馆内阅览×1、33 已通还×1
    assert sum(1 for h in hs if h["available"]) == 5
    by_status = {}
    for h in hs:
        by_status[h["status"]] = by_status.get(h["status"], 0) + 1
    assert by_status == {"借出": 20, "在馆": 5, "馆内阅览": 1, "锁定": 1, "已通还": 1}
    # library＝馆区名（字典查表），location＝local_name 原值
    h0 = next(h for h in hs if h["location"] == "之江馆文学借阅区")
    assert h0["library"] == "之江馆区"
    assert h0["call_number"].startswith("I247.5/0871.4")
    # 分馆样本（其他（分馆）桶）
    h1 = next(h for h in hs if h["location"] == "安吉县天荒坪镇分馆")
    assert h1["library"] == "其他（分馆）" and h1["available"] is True
    # 数据边界：访客视角一律无应还日期
    assert all(h["due_date"] == "" for h in hs)


def test_parse_holdings_state33_item_has_empty_names():
    # 实抓边界样本：已通还单册 local_name/districtId 均为 null → 空串照登
    hs = _zjlib.parse_holdings(_load("holdings.json")["data"]["0"])
    h33 = next(h for h in hs if h["status"] == "已通还")
    assert h33["library"] == "" and h33["location"] == ""
    assert h33["available"] is False  # 保守不可借


def test_parse_holdings_unknown_state_conservative():
    hs = _zjlib.parse_holdings([
        {"state": 99, "state_name": "未知状态", "callno": "X", "local_name": "某处",
         "districtId": "1916325141324353538"},
        {"state": 2, "callno": "Y", "local_name": "别处", "districtId": "不存在的码"},
    ])
    # 词表外状态码保守不可借，status 原值照登
    assert hs[0]["available"] is False and hs[0]["status"] == "未知状态"
    # state_name 缺失回退 state 码；馆区字典查不到回退码原值
    assert hs[1]["available"] is True and hs[1]["status"] == "2"
    assert hs[1]["library"] == "不存在的码"


def test_get_holdings_two_hop_chain(monkeypatch):
    # resourceList 只认 workId（误传 originalId 静默空，探针存证）→ 必须两跳
    bodies = []
    detail = _load("detail.json")
    holdings = _load("holdings.json")

    def fake_open(req, timeout=20):
        bodies.append(json.loads(req.data.decode("utf-8")))
        return detail if "getWorkById" in req.full_url else holdings

    monkeypatch.setattr(_zjlib, "_open", fake_open)
    hs = _zjlib.get_holdings("11000002313805")
    assert bodies[0] == {"bibliosId": "11000002313805", "orgId": _zjlib._ORG_ID}
    assert bodies[1] == {"id": "60204f08e60757b629109b158cfbf13f", "sourceType": "0"}
    assert len(hs) == 28


def test_get_holdings_missing_work_id_raises(monkeypatch):
    monkeypatch.setattr(_zjlib, "_open",
                        lambda req, timeout=20: {"code": 200, "success": True,
                                                 "data": {"record": {"title": ["x"]}}})
    with pytest.raises(RuntimeError) as ei:
        _zjlib.get_holdings("1")
    assert "workId" in str(ei.value)


# ---- 节流（≥2 秒/host，任务口径） ----

class _FakeTime:
    """假时钟：sleep 即推进，记录每次 sleep 时长。"""

    def __init__(self):
        self.now = 0.0
        self.slept = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def test_throttle_first_wait_never_sleeps():
    ft = _FakeTime()
    th = _zjlib._Throttle(2.0, clock=ft.clock, sleep=ft.sleep)
    th.wait()
    assert ft.slept == []


def test_throttle_sleeps_deficit():
    ft = _FakeTime()
    th = _zjlib._Throttle(2.0, clock=ft.clock, sleep=ft.sleep)
    th.wait()
    ft.now += 0.5  # 只过了 0.5 秒 → 差 1.5 秒
    th.wait()
    assert ft.slept == [pytest.approx(1.5)]


def test_throttle_no_sleep_when_interval_passed():
    ft = _FakeTime()
    th = _zjlib._Throttle(2.0, clock=ft.clock, sleep=ft.sleep)
    th.wait()
    ft.now += 10.0  # 超过间隔 → 不睡
    th.wait()
    assert ft.slept == []


def test_per_host_throttle_instances(monkeypatch):
    monkeypatch.setattr(_zjlib, "_throttles", {})
    a = _zjlib._throttle_for("https://www.zjlib.cn/bff-api/x")
    b = _zjlib._throttle_for("https://www.zjlib.cn/bff-api/y")
    assert a is b  # 同 host 复用同一限速器
    assert a.interval == 2.0
