"""深圳适配器：深圳图书馆自研 JSON API → base.py 统一模型。

深圳与 Interlib 无关，完全独立：本模块自带轻量 client（urllib + json），
不打 HTML。三个能力对应 getQueryResult（搜索，真实总数 numFound）、
getBookDetail（详情 + 三桶馆藏 + 借出 ReturnDate）。book_id 用
"{tablename}:{recordid}"，详情接口需要成对 metaTable/metaId。
"""
import json
import urllib.error
import urllib.parse
import urllib.request

_BASE = "https://www.szlib.org.cn"
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
_HEADERS = {"User-Agent": _UA, "Referer": "https://www.szlib.org.cn/opac/"}


def _get(path, params):
    """GET 请求深圳 JSON API，返回解析后的 dict；失败抛含馆名的 RuntimeError。"""
    params = {**params, "client_id": "t1"}
    url = _BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError,
            json.JSONDecodeError, UnicodeDecodeError) as e:
        raise RuntimeError(f"深圳图书馆请求失败：{e}") from e
