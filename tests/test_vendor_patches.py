"""vendor 本地补丁的回归测试：附注提取、summary 回退、单册 item_id 与归还时间。

补丁内容见仓库根目录 NOTICE 的变更列表。这些测试锁定的是我们
对 vendored 代码的修改行为，上游更新后若测试变红，说明补丁被
覆盖或上游行为变化，需要重新评估。
"""
from mcp_library_search.vendor.shanghai_library.library_client import LibraryClient
from mcp_library_search.vendor.shanghai_library.parser import LibraryParser

_SNIPPET = """
<table>
  <tr><th>著者:</th><td>刘慈欣</td></tr>
  <tr><th>ISBN:</th><td>978-7-229-16692-2</td></tr>
  <tr><th>索书号:</th><td>I247.59/0487</td></tr>
  <tr><th>附注:</th><td>新版本册内容：军方探寻外星文明的绝密工程。</td></tr>
</table>
"""

_HOLDINGS_SNIPPET = """
<h3>浦东馆</h3>
<table>
  <tr>
    <td><span class="callnumber">I247.55</span></td>
    <td><span class="barcode">3楼</span></td>
    <td>
      <span class="text-danger">已借出</span>
      <a class="text-danger item-return-date" data-itemid="item-abc" title="预计归还时间"></a>
    </td>
  </tr>
  <tr>
    <td><span class="callnumber">I247.55</span></td>
    <td><span class="barcode">2楼</span></td>
    <td><span class="availability">可借</span></td>
  </tr>
</table>
"""


def test_parser_extracts_notes_field():
    parsed = LibraryParser().parse_book_detail(_SNIPPET)
    assert parsed["notes"] == "新版本册内容：军方探寻外星文明的绝密工程。"


def test_detail_summary_falls_back_to_notes(monkeypatch):
    client = LibraryClient()
    monkeypatch.setattr(client.http_client, "get", lambda url: _SNIPPET)

    book = client.get_book_detail("fake-id")

    assert book is not None
    assert book.summary == "新版本册内容：军方探寻外星文明的绝密工程。"
    assert book.isbn == "978-7-229-16692-2"


def test_detail_summary_prefers_summary_div(monkeypatch):
    """summary 区块存在时优先用它，附注只做兜底。"""
    html = _SNIPPET + '<div class="record-summary">官方简介区块</div>'
    client = LibraryClient()
    monkeypatch.setattr(client.http_client, "get", lambda url: html)

    book = client.get_book_detail("fake-id")

    assert book is not None
    assert book.summary == "官方简介区块"


def test_holdings_parser_extracts_item_id():
    """已借出馆藏行的 item-return-date 锚点带单册 data-itemid。"""
    parsed = LibraryParser().parse_holdings(_HOLDINGS_SNIPPET)

    assert len(parsed) == 2
    assert parsed[0]["status"] == "已借出"
    assert parsed[0]["item_id"] == "item-abc"
    assert parsed[1]["status"] == "可借"
    assert parsed[1]["item_id"] == ""  # 在架馆藏没有该锚点


def test_get_holdings_passes_item_id(monkeypatch):
    client = LibraryClient()
    monkeypatch.setattr(client.http_client, "get", lambda url, params=None: _HOLDINGS_SNIPPET)

    holdings = client.get_holdings("fake-id")

    assert holdings[0].item_id == "item-abc"
    assert holdings[0].record_id == "fake-id"
    assert holdings[1].item_id == ""


def test_get_return_date_parses_json_payload(monkeypatch):
    client = LibraryClient()

    def fake_get(url, params=None):
        assert url == "https://vufind.library.sh.cn/AJAX/JSON"
        assert params == {"method": "itemReturnDate", "itemId": "item-abc"}
        return '{"data": "2026-11-05"}'

    monkeypatch.setattr(client.http_client, "get", fake_get)
    assert client.get_return_date("item-abc") == "2026-11-05"


def test_get_return_date_failure_returns_empty(monkeypatch):
    client = LibraryClient()
    monkeypatch.setattr(client.http_client, "get", lambda url, params=None: "<html>错误页</html>")
    assert client.get_return_date("item-abc") == ""
