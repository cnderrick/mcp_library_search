"""Interlib 馆藏 JSON 解析测试（广州 fixture + 合成数据）。

馆藏走 Ajax JSON 接口（/opac/api/holding/{bookrecno}），不是详情页 HTML——
见 tests/fixtures/guangzhou/NOTES.md。可借分类在接线层做，这里只测解析。
"""
import json

from mcp_library_search.interlib.parser import parse_holdings

_PAYLOAD = json.load(open("tests/fixtures/guangzhou/holding.json", encoding="utf-8"))


def test_fixture_holding_shape_and_content():
    hs = parse_holdings(_PAYLOAD)
    assert len(hs) == 1
    h = hs[0]
    assert set(h) == {"library", "location", "call_number", "status", "due_date"}
    # 馆码/位置码经码表翻译成名称，查不到回退码本身
    assert h["library"] == "广州图书馆"
    assert h["location"] == "参考文献馆•港台书区"
    assert h["call_number"] == "I313.4/5376"
    assert h["status"] == "在馆"
    assert h["due_date"] == ""


def _item(state, barcode, callno="c", curlib="GT", curlocal="CKWX01"):
    return {"state": state, "barcode": barcode, "callno": callno,
            "curlib": curlib, "curlocal": curlocal, "loan": None}


def _payload_with(items, state_names, loan_work=None):
    return {
        "holdingList": items,
        "holdStateMap": {str(k): {"stateType": k, "stateName": v}
                         for k, v in state_names.items()},
        "libcodeMap": {"GT": "广州图书馆"},
        "localMap": {"CKWX01": "参考文献馆•港台书区"},
        "loanWorkMap": loan_work or {},
    }


def test_parse_keeps_order_and_extracts_due_date():
    # 2026-11-05 00:00:00（UTC+8）的 epoch 毫秒
    epoch_ms = 1793808000000
    payload = _payload_with(
        [_item(2, "b1", "c1"), _item(3, "b2", "c2"), _item(13, "b3", "c3")],
        {2: "在馆", 3: "借出", 13: "闭架"},
        loan_work={"b2": {"returnDate": epoch_ms}},
    )
    hs = parse_holdings(payload)
    assert [h["call_number"] for h in hs] == ["c1", "c2", "c3"]  # 保持输入顺序
    assert [h["status"] for h in hs] == ["在馆", "借出", "闭架"]
    assert [h["due_date"] for h in hs] == ["", "2026-11-05", ""]


def test_lookup_fallback_and_empty():
    hs = parse_holdings(_payload_with([_item(2, "b1", curlib="NOPE", curlocal="NOPE")], {2: "在馆"}))
    assert hs[0]["library"] == "NOPE"      # 码表查不到回退码本身
    assert hs[0]["location"] == "NOPE"
    assert parse_holdings({}) == []
    assert parse_holdings({"holdingList": []}) == []
