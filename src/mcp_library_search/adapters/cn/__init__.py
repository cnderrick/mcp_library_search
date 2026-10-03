"""中国地区（域名后缀 cn）适配器注册表。

新增一座中国城市 = 在 cn/ 下新建模块，实现 search_books / get_holdings /
get_book_detail 三个原语（返回结构对齐 adapters/base.py 的 TypedDict，由契约
测试强制），然后在本文件 ADAPTERS 里注册一行。地区名供上层错误提示展示。
"""
from . import ankang
from . import baoji
from . import baotou
from . import changchun
from . import chaozhou
from . import chengdu
from . import chongqing
from . import chuxiong
from . import dalian
from . import daqing
from . import dehong
from . import deqing
from . import dezhou
from . import eerduosi
from . import fujian_prov
from . import guangzhou
from . import haikou
from . import hangzhou
from . import hanzhong
from . import hefei
from . import heilongjiang
from . import henan_prov
from . import heyuan
from . import honghe
from . import huaian
from . import huangshi
from . import huhehaote
from . import hunan_prov
from . import jiangmen
from . import jiangyin
from . import jinan
from . import jingmen
from . import jinhua
from . import laibin
from . import lanzhou
from . import leshan
from . import lijiang
from . import lincang
from . import lishui
from . import nanjing
from . import ningbo
from . import nujiang
from . import qiandongnan
from . import qiannan
from . import qingdao
from . import quanzhou
from . import qujing
from . import shaanxi
from . import shanghai
from . import shaoxing
from . import shenzhen
from . import suzhou
from . import taiyuan
from . import taizhou
from . import tangshan
from . import tianjin
from . import tongliao
from . import wenzhou
from . import wuhai
from . import wuhan
from . import wuxi
from . import xian
from . import xianyang
from . import xiaogan
from . import xishuangbanna
from . import xuzhou
from . import yancheng
from . import yangjiang
from . import yangzhou
from . import yulin
from . import zaozhuang
from . import zhoukou
from . import zhoushan
from . import zhuzhou
from . import zibo
from . import zunyi

NAME = "中国"

ADAPTERS = {
    "ankang": ankang,
    "baoji": baoji,
    "baotou": baotou,
    "changchun": changchun,
    "chaozhou": chaozhou,
    "chengdu": chengdu,
    "chongqing": chongqing,
    "chuxiong": chuxiong,
    "dalian": dalian,
    "daqing": daqing,
    "dehong": dehong,
    "deqing": deqing,
    "dezhou": dezhou,
    "eerduosi": eerduosi,
    "fujian_prov": fujian_prov,
    "guangzhou": guangzhou,
    "haikou": haikou,
    "hangzhou": hangzhou,
    "hanzhong": hanzhong,
    "hefei": hefei,
    "heilongjiang": heilongjiang,
    "henan_prov": henan_prov,
    "heyuan": heyuan,
    "honghe": honghe,
    "huaian": huaian,
    "huangshi": huangshi,
    "huhehaote": huhehaote,
    "hunan_prov": hunan_prov,
    "jiangmen": jiangmen,
    "jiangyin": jiangyin,
    "jinan": jinan,
    "jingmen": jingmen,
    "jinhua": jinhua,
    "laibin": laibin,
    "lanzhou": lanzhou,
    "leshan": leshan,
    "lijiang": lijiang,
    "lincang": lincang,
    "lishui": lishui,
    "nanjing": nanjing,
    "ningbo": ningbo,
    "nujiang": nujiang,
    "qiandongnan": qiandongnan,
    "qiannan": qiannan,
    "qingdao": qingdao,
    "quanzhou": quanzhou,
    "qujing": qujing,
    "shaanxi": shaanxi,
    "shanghai": shanghai,
    "shaoxing": shaoxing,
    "shenzhen": shenzhen,
    "suzhou": suzhou,
    "taiyuan": taiyuan,
    "taizhou": taizhou,
    "tangshan": tangshan,
    "tianjin": tianjin,
    "tongliao": tongliao,
    "wenzhou": wenzhou,
    "wuhai": wuhai,
    "wuhan": wuhan,
    "wuxi": wuxi,
    "xian": xian,
    "xianyang": xianyang,
    "xiaogan": xiaogan,
    "xishuangbanna": xishuangbanna,
    "xuzhou": xuzhou,
    "yancheng": yancheng,
    "yangjiang": yangjiang,
    "yangzhou": yangzhou,
    "yulin": yulin,
    "zaozhuang": zaozhuang,
    "zhoukou": zhoukou,
    "zhoushan": zhoushan,
    "zhuzhou": zhuzhou,
    "zibo": zibo,
    "zunyi": zunyi,
}
