"""浙江图书馆（www.zjlib.cn）JSON 客户端：BFF 网关三原语，杭州双源共用。

浙图是自研微服务（Nuxt 3 ＋ Java/Spring ＋ ES），与图创 Interlib 家族无关：
全部 POST JSON、无需鉴权，必带 BFF-ORG-ID 头。检索 pageList（真实总数、
current 分页实测生效）；详情 getWorkById（bibliosId＝originalId）；馆藏
resourceList 只认 workId——误传 originalId 是 HTTP 200 ＋ 静默空数组，与
「无纸本馆藏」不可区分，因此馆藏链路是两跳：getWorkById→workId→resourceList。
字段形态（数组值、脏 ISBN、状态码表、馆区字典）与数据边界（访客拿不到
应还日期）全部见 tests/fixtures/zjlib/NOTES.md。
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

_BASE = "https://www.zjlib.cn/bff-api"
_ORG_ID = "1916318653650423810"
_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
_HEADERS = {
    "User-Agent": _UA,
    "Content-Type": "application/json",
    "BFF-ORG-ID": _ORG_ID,
    "Accept-Language": "zh-CN;q=0.9",
}
_THROTTLE = 2.0  # ≥2 秒/host 保守节流（实测无限速墙，仍按任务口径留余量）

# 馆区字典（NOTES.md；查不到回退码原值，与家族 libcodeMap 口径一致）
_DISTRICTS = {
    "1916325141324353538": "之江馆区",
    "1916325244624236545": "曙光路馆区",
    "1960228014308634625": "大学路馆区",
    "1960237529544437762": "孤山路馆区",
    "1960238282716921857": "嘉业堂藏书楼",
    "1953763801877389313": "其他（分馆）",
}
# 可借状态码（NOTES.md 状态码表：2＝在馆可借；3 借出/9 锁定/16 馆内阅览/33 已通还
# 及词表外码一律保守不可借）
_AVAILABLE_STATES = {"2"}


class _Throttle:
    """最小间隔限速器：距上次 wait() 不足 interval 时睡足差值。

    clock/sleep 可注入供单测；真网默认 time.monotonic/time.sleep。
    """

    def __init__(self, interval, clock=time.monotonic, sleep=time.sleep):
        self.interval = interval
        self._clock = clock
        self._sleep = sleep
        self._last = None

    def wait(self):
        now = self._clock()
        if self._last is not None:
            deficit = self.interval - (now - self._last)
            if deficit > 0:
                self._sleep(deficit)
                now = self._clock()
        self._last = now


# 每 host 一个限速器（与天津同款接线；浙图当前单 host，形态留扩展余地）
_throttles = {}


def _throttle_for(url):
    host = urllib.parse.urlsplit(url).netloc
    if host not in _throttles:
        _throttles[host] = _Throttle(_THROTTLE)
    return _throttles[host]


def _open(req, timeout=20):
    """HTTP 入口：每 host 节流 ＋ JSON 解析；网络/解析失败包装 RuntimeError。

    单测 monkeypatch 注入点（本仓库约定：替换模块 _open）。
    """
    _throttle_for(req.full_url).wait()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, OSError,
            json.JSONDecodeError, UnicodeDecodeError) as e:
        raise RuntimeError(f"浙江图书馆请求失败：{e}") from e


def _post(path, body):
    """POST BFF 网关并解出 data；业务失败（success≠true 或 code≠200）报错带 desc 原值。

    「记录不存在」与「服务器繁忙」共用 code=500 形态、不可区分（NOTES.md 探针），
    desc 原值照登进报错，不猜语义。
    """
    req = urllib.request.Request(_BASE + path,
                                 data=json.dumps(body).encode("utf-8"),
                                 headers=_HEADERS, method="POST")
    payload = _open(req)
    if not isinstance(payload, dict):
        raise RuntimeError(f"浙江图书馆响应形态异常：{str(payload)[:200]}")
    if payload.get("code") != 200 or not payload.get("success"):
        raise RuntimeError(
            f"浙江图书馆接口返回异常：code={payload.get('code')}, desc={payload.get('desc')}")
    return payload.get("data")


def _first(value):
    """浙图字段多为数组（通常单元素）：取首元素；None/空数组 → 空串。"""
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return ""
    return str(value).strip()


def _join_paras(value):
    """description 类多段字段（数组）：逐段 strip 后以换行拼接，空段丢弃。"""
    if isinstance(value, list):
        parts = [str(x).strip() for x in value if x is not None and str(x).strip()]
        return "\n".join(parts)
    return str(value or "").strip()


def _year(text):
    """dateIssue 有脏值（如「2019.」），按形态提取 4 位年份；找不到返回空串。"""
    m = re.search(r"(?:19|20)\d{2}", str(text or ""))
    return m.group(0) if m else ""


# ---- 解析（纯函数，单测直接喂 tests/fixtures/zjlib/ 实抓 JSON） ----

def parse_search(data):
    """pageList 的 data → {"books", "total_results", "total_pages", "has_next"}。

    books 条目形态与 interlib.search_raw 对齐（book_id＝originalId 裸值，不带
    ZJ: 前缀——前缀由 hangzhou 合并层加）；isbn 脏值原样带出，清洗在归并层。
    检索记录无可借性字段 → availability_summary 恒空串（数据边界，NOTES.md）。
    """
    books = []
    for r in data.get("records") or []:
        if not isinstance(r, dict):
            continue
        bid = _first(r.get("originalId"))
        if not bid:
            continue  # 无稳定 id 的条目不可路由，丢弃
        books.append({
            "book_id": bid,
            "title": _first(r.get("title")),
            "author": _first(r.get("creator")),
            "publisher": _first(r.get("publisher")),
            "publish_year": _year(_first(r.get("dateIssue"))),
            "availability_summary": "",
            "isbn": _first(r.get("identifierIsbn")),
        })
    total = data.get("total")
    pages = data.get("pages")
    current = data.get("current") or 1
    return {
        "books": books,
        "total_results": total if isinstance(total, int) else None,
        "total_pages": pages if isinstance(pages, int) else 1,
        "has_next": bool(isinstance(pages, int) and current < pages),
    }


def parse_record(rec):
    """getWorkById 的 data.record → 详情字段 dict（含 work_id，供馆藏两跳链）。

    creator 带责任方式后缀原值照登（「刘慈欣著」）；call_number 取中图分类法
    （subjectClassica，与家族口径一致）；isbn 优先 identifierIsbn 原值，
    空则回退站点自身的 identifierIsbnPure。
    """
    summary = _join_paras(rec.get("description"))
    if not summary:
        summary = _join_paras(rec.get("descriptionAbstract"))
    return {
        "work_id": str(rec.get("workId") or "").strip(),
        "title": _first(rec.get("title")),
        "author": _first(rec.get("creator")),
        "publisher": _first(rec.get("publisher")),
        "publish_year": _year(_first(rec.get("dateIssue"))),
        "isbn": _first(rec.get("identifierIsbn")) or _first(rec.get("identifierIsbnPure")),
        "call_number": _first(rec.get("subjectClassica")),
        "summary": summary,
    }


def parse_holdings(items):
    """resourceList 单册数组 → 归一 Holding dict 列表。

    library＝馆区名（districtId 查字典，查不到回退码原值，null → 空串）；
    location＝local_name 原值；status＝state_name 原值（缺失回退 state 码）；
    可借判定只认 state=2，词表外保守不可借；due_date 恒空串（数据边界：
    访客视角无应还日期，需读者登录，不猜）。
    """
    holdings = []
    for it in items:
        if not isinstance(it, dict):
            continue
        state = it.get("state")
        state = str(state).strip() if state is not None else ""
        district = str(it.get("districtId") or "").strip()
        holdings.append({
            "library": _DISTRICTS.get(district, district),
            "location": str(it.get("local_name") or "").strip(),
            "call_number": str(it.get("callno") or "").strip(),
            "status": str(it.get("state_name") or "").strip() or state,
            "available": state in _AVAILABLE_STATES,
            "due_date": "",
        })
    return holdings


# ---- 三原语（网络层） ----

def search(keyword, page=1, limit=20):
    """检索：pageList 任意词（phrase_fuzzy）；ISBN 形态关键词同样直接命中（NOTES.md）。"""
    data = _post("/search-admin-service/open-api/search/pageList", {
        "metadataType": "work",
        "current": page,
        "size": limit,
        "query": [{"key": "", "value": keyword, "condition": "and",
                   "match": "phrase_fuzzy"}],
        "sortBy": [],
    })
    return parse_search(data if isinstance(data, dict) else {})


def _get_record(original_id):
    """getWorkById → data.record 原始 dict；无记录报错（含站点 desc 场景由 _post 拦截）。"""
    data = _post("/portal-admin-service/portal-pc-api/search/getWorkById",
                 {"bibliosId": str(original_id), "orgId": _ORG_ID})
    rec = data.get("record") if isinstance(data, dict) else None
    if not isinstance(rec, dict) or not rec:
        raise RuntimeError(f"浙江图书馆：未找到该书记录：{original_id}")
    return rec


def get_work_detail(original_id):
    """详情：getWorkById(originalId) → parse_record 字段 dict（含 work_id）。"""
    d = parse_record(_get_record(original_id))
    if not d["title"]:
        raise RuntimeError(f"浙江图书馆：未找到该书详情：{original_id}")
    return d


def get_holdings(original_id):
    """馆藏两跳链：getWorkById 取 workId → resourceList 单册 → parse_holdings。

    resourceList 只认 workId：误传 originalId 是静默空数组（NOTES.md 探针存证），
    与「无纸本馆藏」不可区分，因此必须两跳，不能省。
    """
    work_id = str(_get_record(original_id).get("workId") or "").strip()
    if not work_id:
        raise RuntimeError(f"浙江图书馆：详情缺 workId，无法查馆藏：{original_id}")
    data = _post("/portal-admin-service/portal-pc-api/search/resourceList",
                 {"id": work_id, "sourceType": "0"})
    items = data.get("0") if isinstance(data, dict) else None
    return parse_holdings(items if isinstance(items, list) else [])
