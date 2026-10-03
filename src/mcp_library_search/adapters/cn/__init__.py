"""中国地区（域名后缀 cn）适配器注册表。

新增一座中国城市 = 在 cn/ 下新建模块，实现 search_books / get_holdings /
get_book_detail 三个原语（返回结构对齐 adapters/base.py 的 TypedDict，由契约
测试强制），然后在本文件 ADAPTERS 里注册一行。地区名供上层错误提示展示。
"""
from . import ankang
from . import anqing
from . import anshun
from . import baoji
from . import baotou
from . import bijie
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
from . import dongying
from . import eerduosi
from . import enshi
from . import ezhou
from . import fujian_prov
from . import fuzhou
from . import guangzhou
from . import guilin
from . import haikou
from . import hangzhou
from . import hanzhong
from . import hefei
from . import heilongjiang
from . import henan_prov
from . import heyuan
from . import honghe
from . import huaian
from . import huanggang
from . import huangshi
from . import hubei_prov
from . import huhehaote
from . import hulunbuir
from . import hunan_prov
from . import jiangmen
from . import jiangyin
from . import jieyang
from . import jinan
from . import jingmen
from . import jingzhou
from . import jinhua
from . import laibin
from . import lanzhou
from . import leshan
from . import liaocheng
from . import lijiang
from . import lincang
from . import linyi
from . import lishui
from . import liupanshui
from . import maoming
from . import mudanjiang
from . import nanjing
from . import ningbo
from . import ningde
from . import nujiang
from . import puning
from . import qiandongnan
from . import qiannan
from . import qingdao
from . import qiqihar
from . import quanzhou
from . import qujing
from . import rizhao
from . import sanming
from . import sanya
from . import shaanxi
from . import shanghai
from . import shaoxing
from . import shenzhen
from . import shijiazhuang
from . import shiyan
from . import siping
from . import suzhou
from . import taian
from . import taiyuan
from . import taizhou
from . import tangshan
from . import tianjin
from . import tongliao
from . import tongling
from . import weifang
from . import wenzhou
from . import wuhai
from . import wuhan
from . import wuxi
from . import xian
from . import xiangtan
from . import xianyang
from . import xiaogan
from . import xinzhou
from . import xishuangbanna
from . import xuzhou
from . import yancheng
from . import yangjiang
from . import yangzhou
from . import yantai
from . import yueyang
from . import yulin
from . import zaozhuang
from . import zhangjiajie
from . import zhengzhou
from . import zhongshan
from . import zhoukou
from . import zhoushan
from . import zhuzhou
from . import zibo
from . import zunyi

NAME = "中国"

ADAPTERS = {
    "ankang": ankang,
    "anqing": anqing,
    "anshun": anshun,
    "baoji": baoji,
    "baotou": baotou,
    "bijie": bijie,
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
    "dongying": dongying,
    "eerduosi": eerduosi,
    "enshi": enshi,
    "ezhou": ezhou,
    "fujian_prov": fujian_prov,
    "fuzhou": fuzhou,
    "guangzhou": guangzhou,
    "guilin": guilin,
    "haikou": haikou,
    "hangzhou": hangzhou,
    "hanzhong": hanzhong,
    "hefei": hefei,
    "heilongjiang": heilongjiang,
    "henan_prov": henan_prov,
    "heyuan": heyuan,
    "honghe": honghe,
    "huaian": huaian,
    "huanggang": huanggang,
    "huangshi": huangshi,
    "hubei_prov": hubei_prov,
    "huhehaote": huhehaote,
    "hulunbuir": hulunbuir,
    "hunan_prov": hunan_prov,
    "jiangmen": jiangmen,
    "jiangyin": jiangyin,
    "jieyang": jieyang,
    "jinan": jinan,
    "jingmen": jingmen,
    "jingzhou": jingzhou,
    "jinhua": jinhua,
    "laibin": laibin,
    "lanzhou": lanzhou,
    "leshan": leshan,
    "liaocheng": liaocheng,
    "lijiang": lijiang,
    "lincang": lincang,
    "linyi": linyi,
    "lishui": lishui,
    "liupanshui": liupanshui,
    "maoming": maoming,
    "mudanjiang": mudanjiang,
    "nanjing": nanjing,
    "ningbo": ningbo,
    "ningde": ningde,
    "nujiang": nujiang,
    "puning": puning,
    "qiandongnan": qiandongnan,
    "qiannan": qiannan,
    "qingdao": qingdao,
    "qiqihar": qiqihar,
    "quanzhou": quanzhou,
    "qujing": qujing,
    "rizhao": rizhao,
    "sanming": sanming,
    "sanya": sanya,
    "shaanxi": shaanxi,
    "shanghai": shanghai,
    "shaoxing": shaoxing,
    "shenzhen": shenzhen,
    "shijiazhuang": shijiazhuang,
    "shiyan": shiyan,
    "siping": siping,
    "suzhou": suzhou,
    "taian": taian,
    "taiyuan": taiyuan,
    "taizhou": taizhou,
    "tangshan": tangshan,
    "tianjin": tianjin,
    "tongliao": tongliao,
    "tongling": tongling,
    "weifang": weifang,
    "wenzhou": wenzhou,
    "wuhai": wuhai,
    "wuhan": wuhan,
    "wuxi": wuxi,
    "xian": xian,
    "xiangtan": xiangtan,
    "xianyang": xianyang,
    "xiaogan": xiaogan,
    "xinzhou": xinzhou,
    "xishuangbanna": xishuangbanna,
    "xuzhou": xuzhou,
    "yancheng": yancheng,
    "yangjiang": yangjiang,
    "yangzhou": yangzhou,
    "yantai": yantai,
    "yueyang": yueyang,
    "yulin": yulin,
    "zaozhuang": zaozhuang,
    "zhangjiajie": zhangjiajie,
    "zhengzhou": zhengzhou,
    "zhongshan": zhongshan,
    "zhoukou": zhoukou,
    "zhoushan": zhoushan,
    "zhuzhou": zhuzhou,
    "zibo": zibo,
    "zunyi": zunyi,
}
