"""中国地区（域名后缀 cn）适配器注册表。

新增一座中国城市 = 在 cn/ 下新建模块，实现 search_books / get_holdings /
get_book_detail 三个原语（返回结构对齐 adapters/base.py 的 TypedDict，由契约
测试强制），然后在本文件 ADAPTERS 里注册一行。地区名供上层错误提示展示。
"""
from . import chengdu
from . import chongqing
from . import dalian
from . import guangzhou
from . import hangzhou
from . import hefei
from . import jiangyin
from . import jinhua
from . import nanjing
from . import ningbo
from . import qingdao
from . import shanghai
from . import shaoxing
from . import shenzhen
from . import taizhou
from . import tianjin
from . import wenzhou
from . import wuxi
from . import yangzhou

NAME = "中国"

ADAPTERS = {
    "chengdu": chengdu,
    "chongqing": chongqing,
    "dalian": dalian,
    "guangzhou": guangzhou,
    "hangzhou": hangzhou,
    "hefei": hefei,
    "jiangyin": jiangyin,
    "jinhua": jinhua,
    "nanjing": nanjing,
    "ningbo": ningbo,
    "qingdao": qingdao,
    "shanghai": shanghai,
    "shaoxing": shaoxing,
    "shenzhen": shenzhen,
    "taizhou": taizhou,
    "tianjin": tianjin,
    "wenzhou": wenzhou,
    "wuxi": wuxi,
    "yangzhou": yangzhou,
}
