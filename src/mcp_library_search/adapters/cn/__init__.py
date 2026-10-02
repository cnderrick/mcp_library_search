"""中国地区（域名后缀 cn）适配器注册表。

新增一座中国城市 = 在 cn/ 下新建模块，实现 search_books / get_holdings /
get_book_detail 三个原语（返回结构对齐 adapters/base.py 的 TypedDict，由契约
测试强制），然后在本文件 ADAPTERS 里注册一行。地区名供上层错误提示展示。
"""
from . import ankang
from . import baoji
from . import chengdu
from . import chongqing
from . import dalian
from . import guangzhou
from . import hangzhou
from . import hanzhong
from . import hefei
from . import huaian
from . import jiangyin
from . import jinhua
from . import lishui
from . import nanjing
from . import ningbo
from . import qingdao
from . import shaanxi
from . import shanghai
from . import shaoxing
from . import shenzhen
from . import suzhou
from . import taizhou
from . import tianjin
from . import wenzhou
from . import wuxi
from . import xian
from . import xianyang
from . import xuzhou
from . import yancheng
from . import yangzhou
from . import yulin
from . import zhoushan

NAME = "中国"

ADAPTERS = {
    "ankang": ankang,
    "baoji": baoji,
    "chengdu": chengdu,
    "chongqing": chongqing,
    "dalian": dalian,
    "guangzhou": guangzhou,
    "hangzhou": hangzhou,
    "hanzhong": hanzhong,
    "hefei": hefei,
    "huaian": huaian,
    "jiangyin": jiangyin,
    "jinhua": jinhua,
    "lishui": lishui,
    "nanjing": nanjing,
    "ningbo": ningbo,
    "qingdao": qingdao,
    "shaanxi": shaanxi,
    "shanghai": shanghai,
    "shaoxing": shaoxing,
    "shenzhen": shenzhen,
    "suzhou": suzhou,
    "taizhou": taizhou,
    "tianjin": tianjin,
    "wenzhou": wenzhou,
    "wuxi": wuxi,
    "xian": xian,
    "xianyang": xianyang,
    "xuzhou": xuzhou,
    "yancheng": yancheng,
    "yangzhou": yangzhou,
    "yulin": yulin,
    "zhoushan": zhoushan,
}
