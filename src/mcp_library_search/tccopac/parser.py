"""图创 tcc-opac 家族解析层：检索 / 详情 / 馆藏 JSON 的纯函数。

字段口径由宁波前端 JS 逆向并实抓验证（tests/fixtures/ningbo/NOTES.md），
family 成员共享。错误消息按传入 `name` 前置馆名。
"""
from __future__ import annotations

import re

# 前端对 /search/ 的滑块验证触发码
CAPTCHA_CODES = (43001, -1, -402)
_HOLD_SIZE = 500


def clean(text):
    """JSON 字段值 → 原值字符串（None→空串），只去首尾空白。"""
    if text is None:
        return ""
    return str(text).strip()


def year(text):
    m = re.search(r"(?:19|20)\d{2}", str(text or ""))
    return m.group(0) if m else ""


def year_from_100a(text):
    """UNIMARC 100$a 定长字段：形如「20160911d2003    km…」，d 后 4 位是出版年。"""
    m = re.search(r"d((?:19|20)\d{2})", str(text or ""))
    return m.group(1) if m else ""


def date_only(text):
    """returnTime 完整时间戳「YYYY-MM-DD HH:MM:SS」→ 日期段；形态不符返回空串。"""
    m = re.match(r"(\d{4}-\d{2}-\d{2})", str(text or ""))
    return m.group(1) if m else ""


def check_book_id(book_id, name=""):
    """book_id 是 tcc-opac 原生雪花数字 id（单源，不加前缀）。"""
    s = str(book_id or "").strip()
    if not s.isdigit():
        prefix = f"{name}：" if name else ""
        raise RuntimeError(f"{prefix}book_id 格式应为 tcc-opac 数字 id：{book_id}")
    return s


def _first(values):
    """fieldItem 的值是字符串列表，取首个非空原值。"""
    for v in values or []:
        s = clean(v)
        if s:
            return s
    return ""


def check_search(resp, name=""):
    """/search/ 成功响应无 code 字段；带 code 即异常：43001/-1/-402 是滑块触发码。"""
    prefix = f"{name}：" if name else ""
    if isinstance(resp, dict) and "code" in resp:
        code = resp.get("code")
        desc = clean(resp.get("desc"))
        if code in CAPTCHA_CODES:
            raise RuntimeError(f"{prefix}检索命中滑块验证/风控（code={code}）：{desc}")
        if code != 200:
            raise RuntimeError(f"{prefix}检索失败（code={code}）：{desc}")
    if not isinstance(resp, dict) or "bookList" not in resp:
        raise RuntimeError(f"{prefix}检索响应缺少 bookList（接口可能变更）")
    return resp


def parse_search(resp, name=""):
    """检索响应 → {"books", "total_results"}。`availability_summary` 恒空串。"""
    resp = check_search(resp, name)
    try:
        total = int(resp.get("numFound") or 0)  # 源站给字符串
    except (TypeError, ValueError):
        total = 0
    books = [
        {
            "book_id": clean(it.get("id")),
            "title": clean(it.get("title")),
            "author": clean(it.get("author")),
            "publisher": clean(it.get("publisher")),
            "publish_year": year(it.get("pubdate")),
            "availability_summary": "",
        }
        for it in (resp.get("bookList") or [])
        if isinstance(it, dict) and clean(it.get("id"))
    ]
    return {"books": books, "total_results": total}


def parse_holdings(resp, name=""):
    """馆藏响应 → 单册 dict 列表。code==-1「数据不存在」视同无馆藏空列表。"""
    prefix = f"{name}：" if name else ""
    if not isinstance(resp, dict):
        raise RuntimeError(f"{prefix}馆藏响应形态异常")
    code = resp.get("code")
    if code == -1:
        return []
    if code != 200:
        raise RuntimeError(f"{prefix}馆藏查询失败（code={code}）：{clean(resp.get('desc'))}")
    holdings = []
    for r in (resp.get("data") or {}).get("records") or []:
        if not isinstance(r, dict):
            continue
        status = clean(r.get("statename")) or clean(r.get("stateStr"))
        holdings.append({
            "library": clean(r.get("curOrgName")) or clean(r.get("orgName")),
            "location": clean(r.get("curlocalName")) or clean(r.get("orglocalName")),
            "call_number": clean(r.get("callno")),
            "status": status,
            "available": (status == "在馆"),  # 词表外状态保守不可借，原值照登
            "due_date": date_only(r.get("returnTime")),
        })
    return holdings


def parse_detail(resp, book_id="", name=""):
    """详情响应 → 书目 dict。code==-1「数据不存在」= 聚合条目无本地书目。"""
    prefix = f"{name}：" if name else ""
    if not isinstance(resp, dict):
        raise RuntimeError(f"{prefix}详情响应形态异常")
    code = resp.get("code")
    if code == -1:
        raise RuntimeError(
            f"{prefix}未找到该书详情：{book_id}（{clean(resp.get('desc')) or '数据不存在'}；"
            "检索聚合条目可能无本地书目）")
    if code != 200:
        raise RuntimeError(f"{prefix}详情查询失败（code={code}）：{clean(resp.get('desc'))}")
    data = resp.get("data") or {}
    b = data.get("biblios") or {}
    fi = data.get("fieldItem") or {}
    notes = data.get("fields") or {}
    title = clean(b.get("title")) or _first(fi.get("200$a"))
    if not title:
        raise RuntimeError(f"{prefix}未找到该书详情：{book_id}")
    summary = ""
    for marc in ("330", "327", "300"):  # 内容提要 → 内容附注 → 一般性附注
        summary = clean(notes.get(marc + "a")) or _first(fi.get(marc + "$a"))
        if summary:
            break
    return {
        "title": title,
        "author": clean(b.get("author")) or _first(fi.get("200$f")),
        "publisher": clean(b.get("publisher")) or _first(fi.get("210$c")),
        "publish_year": (year(b.get("pubdate"))
                         or year(_first(fi.get("210$d")))
                         or year_from_100a(_first(fi.get("100$a")))),
        "isbn": clean(b.get("isbn")) or _first(fi.get("010$a")),
        "call_number": clean(b.get("shelfno")),  # classno 分类号不冒充索书号
        "summary": summary,
    }
