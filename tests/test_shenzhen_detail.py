import json
from pathlib import Path

import pytest

from mcp_library_search.adapters.cn import shenzhen

_FIXTURES = Path(__file__).parent / "fixtures" / "shenzhen"
_DETAIL = json.loads((_FIXTURES / "detail.json").read_text(encoding="utf-8"))


def test_detail_contract(monkeypatch):
    monkeypatch.setattr(shenzhen, "_get", lambda path, params: _DETAIL)
    d = shenzhen.get_book_detail("bibliosm:123")
    assert set(d) == {"book_id", "title", "author", "publisher", "publish_year",
                      "isbn", "call_number", "summary"}
    assert d["book_id"] == "bibliosm:123"
    assert d["title"] != ""
    # publish/publishyear 是「城市:出版社,年份」全串，须拆出纯出版社与纯年份
    assert d["publisher"] == "万卷出版公司"
    assert d["publish_year"] == "2008"
    # detail 的 author 带「著」后缀，须清洗
    assert d["author"] == "冯唐"
    assert d["isbn"] != ""
    assert d["summary"] != ""


def test_detail_not_found(monkeypatch):
    # 数据源查不到时的响应形态以 NOTES.md 侦察为准；这里约定返回体里取不到书目信息即判未找到
    monkeypatch.setattr(shenzhen, "_get", lambda path, params: {"data": {}})
    with pytest.raises(RuntimeError, match="未找到"):
        shenzhen.get_book_detail("bibliosm:0")
