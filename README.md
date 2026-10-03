# mcp_library_search

[![PyPI version](https://img.shields.io/pypi/v/mcp_library_search)](https://pypi.org/project/mcp-library-search/)

MCP server：查询城市图书馆的馆藏与可借状态——回答"这本书在哪些馆能借到"。

## 支持情况

| 城市 | 标识 | 状态 | 数据源 |
|---|---|---|---|
| 上海 | `shanghai` | ✅ 已接入 | 上海中心图书馆"一卡通"总分馆体系（900+ 网点，含地铁站 24 小时自助机） |
| 广州 | `guangzhou` | ✅ 已接入 | 广州图书馆（图创 Interlib） |
| 杭州 | `hangzhou` | ✅ 已接入 | 杭州图书馆＋浙江图书馆双源合并（同一本书跨馆归并成一条结果） |
| 深圳 | `shenzhen` | ✅ 已接入 | 深圳图书馆之城统一平台（自研 JSON API，167 馆） |
| 天津 | `tianjin` | ✅ 已接入 | 天津图书馆等三源合并（主馆＋少儿馆＋中新友好图书馆，同一本书跨馆归并成一条结果） |
| 重庆 | `chongqing` | ✅ 已接入 | 重庆 InDigLib 集群数字图书馆 |
| 合肥 | `hefei` | ✅ 已接入 | 安徽省图书馆＋合肥市图书馆双源合并（同一本书跨馆归并成一条结果） |
| 南京 | `nanjing` | ✅ 已接入 | 金陵图书馆＋12 区馆联合目录 ＋ 南京图书馆（江苏省图）双源合并，馆藏到单册级；南图源走 Ex Libris ALEPH，有验证码墙 |
| 成都 | `chengdu` | ✅ 已接入 | 成都平原经济区联合目录（图创 Interlib pro2018） |
| 宁波 | `ningbo` | ✅ 已接入 | 宁波市图书馆全市联合目录（图创 tcc-opac） |
| 绍兴 | `shaoxing` | ✅ 已接入 | 绍兴市公共图书馆联合目录（图创 Interlib pro2018） |
| 大连 | `dalian` | ✅ 已接入 | 大连地区网上联合目录（SirsiDynix iLink） |
| 金华 | `jinhua` | ✅ 已接入 | 金华市图书馆（UILAS HTML OPAC） |
| 江阴 | `jiangyin` | ✅ 已接入 | 江阴市图书馆（图创 Interlib，含农家书屋等 24H 网点） |
| 温州 | `wenzhou` | ✅ 已接入 | 温州市图书馆（图创 Interlib，全市总分馆体系） |
| 台州 | `taizhou` | ✅ 已接入 | 台州市图书馆（图创 Interlib pro2018，含地铁站点通借） |
| 青岛 | `qingdao` | ✅ 已接入 | 青岛市公共图书馆联合目录（图创 Interlib，26 馆联合，检索走站点 Solr 通道） |
| 无锡 | `wuxi` | ✅ 已接入 | 无锡市新吴区图书馆（图星 LibStar Find；市图书馆源预留未接入） |
| 扬州 | `yangzhou` | ✅ 已接入 | 扬州市图书馆联盟联合目录（汇文 uopac，与南京金陵源同系统；站点 securitycam 反爬按静态挑战处理） |
| 苏州 | `suzhou` | ✅ 已接入 | 苏州图书馆＋苏州工业园区图书馆双源合并（图创 Interlib，馆藏到单册级） |
| 徐州 | `xuzhou` | ✅ 已接入 | 徐州市图书馆全市联合目录（图星 LibStar Find，含鼓楼区馆等） |
| 淮安 | `huaian` | ✅ 已接入 | 淮安市图书馆全市联合目录（图星 LibStar Find，含少儿馆、清江浦区馆等） |
| 盐城 | `yancheng` | ✅ 已接入 | 盐城市图书馆（图星 LibStar Find，单实例） |
| 丽水 | `lishui` | ✅ 已接入 | 丽水市公共图书馆联合目录（图创 Interlib pro2018，含景宁/庆元/缙云等县馆） |
| 舟山 | `zhoushan` | ✅ 已接入 | 舟山市图书馆（UILAS 知识检索平台） |
| 陕西省图书馆 | `shaanxi` | ✅ 已接入 | 陕西省图书馆（新版 UILAS REST 平台，省级馆馆址西安） |
| 西安 | `xian` | ✅ 已接入 | 西安市公共图书馆集群平台（图创 Interlib pro2018，上下文 `/opac3`） |
| 咸阳 | `xianyang` | ✅ 已接入 | 咸阳市公共图书馆联盟（图创 Interlib） |
| 宝鸡 | `baoji` | ✅ 已接入 | 宝鸡市公共图书馆集群平台（图创 Interlib） |
| 安康 | `ankang` | ✅ 已接入 | 安康市图书馆（图创 Interlib pro2018） |
| 汉中 | `hanzhong` | ✅ 已接入 | 汉中市图书馆全市联合目录（图星 LibStar Find，含洋县等县馆） |
| 榆林 | `yulin` | ✅ 已接入 | 榆林市图书馆（新版 UILAS REST 平台） |
| 海口 | `haikou` | ✅ 已接入 | 海口市图书馆（图创 Interlib） |
| 株洲 | `zhuzhou` | ✅ 已接入 | 株洲市图书馆（图创 Interlib） |
| 孝感 | `xiaogan` | ✅ 已接入 | 孝感市图书馆（图创 Interlib） |
| 荆门 | `jingmen` | ✅ 已接入 | 荆门市图书馆（图创 Interlib） |
| 湖南图书馆 | `hunan_prov` | ✅ 已接入 | 湖南图书馆省级馆（图创 Interlib） |
| 福建省图书馆 | `fujian_prov` | ✅ 已接入 | 福建省图书馆（图创 Interlib） |
| 阳江 | `yangjiang` | ✅ 已接入 | 阳江市图书馆（图创 Interlib） |
| 淄博 | `zibo` | ✅ 已接入 | 淄博市图书馆（图创 Interlib） |
| 德州 | `dezhou` | ✅ 已接入 | 德州市图书馆（图创 Interlib） |
| 周口 | `zhoukou` | ✅ 已接入 | 周口市图书馆（图创 Interlib） |
| 泉州 | `quanzhou` | ✅ 已接入 | 泉州市图书馆（图创 Interlib） |
| 通辽 | `tongliao` | ✅ 已接入 | 通辽市图书馆（图创 Interlib） |
| 河源 | `heyuan` | ✅ 已接入 | 河源市图书馆（图创 Interlib） |
| 黑龙江省图书馆 | `heilongjiang` | ✅ 已接入 | 黑龙江省图书馆（图创 Interlib，检索走内嵌 Solr） |
| 长春 | `changchun` | ✅ 已接入 | 长春市图书馆（图创 Interlib，检索走内嵌 Solr） |
| 唐山 | `tangshan` | ✅ 已接入 | 唐山市图书馆（图创 Interlib，检索走内嵌 Solr） |
| 包头 | `baotou` | ✅ 已接入 | 包头市图书馆（图创 Interlib，检索走内嵌 Solr） |
| 乌海 | `wuhai` | ✅ 已接入 | 乌海市图书馆（图创 Interlib，检索走内嵌 Solr） |
| 呼和浩特 | `huhehaote` | ✅ 已接入 | 呼和浩特市图书馆（图创 Interlib，检索走内嵌 Solr） |
| 潮州 | `chaozhou` | ✅ 已接入 | 潮州市图书馆（图创 Interlib，检索走内嵌 Solr） |
| 兰州 | `lanzhou` | ✅ 已接入 | 兰州市图书馆（新版 UILAS REST 平台） |
| 江门 | `jiangmen` | ✅ 已接入 | 江门市图书馆（新版 UILAS REST 平台） |
| 河南省图书馆 | `henan_prov` | ✅ 已接入 | 河南省图书馆（老版 UILAS HTML OPAC） |
| 济南 | `jinan` | ✅ 已接入 | 济南市图书馆（图创 tcc-opac 全市联合目录） |
| 鄂尔多斯 | `eerduosi` | ✅ 已接入 | 鄂尔多斯市图书馆（图创 tcc-opac） |
| 丽江 | `lijiang` | ✅ 已接入 | 丽江市图书馆全市联合目录（图创 Interlib，含古城区/玉龙/宁蒗/华坪等分馆） |
| 来宾 | `laibin` | ✅ 已接入 | 来宾市图书馆全市联合目录（图创 Interlib，含各镇/县分馆） |
| 黄石 | `huangshi` | ✅ 已接入 | 黄石市图书馆（图创 Interlib） |
| 遵义 | `zunyi` | ✅ 已接入 | 遵义市图书馆（图创 Interlib） |
| 黔东南 | `qiandongnan` | ✅ 已接入 | 黔东南州图书馆（图创 Interlib，含乡镇分馆与城市书房） |
| 黔南 | `qiannan` | ✅ 已接入 | 黔南州图书馆（图创 Interlib） |
| 曲靖 | `qujing` | ✅ 已接入 | 曲靖市图书馆（图创 Interlib） |
| 临沧 | `lincang` | ✅ 已接入 | 临沧市图书馆（图创 Interlib，含区县馆与乡镇分馆） |
| 楚雄 | `chuxiong` | ✅ 已接入 | 楚雄州图书馆（图创 Interlib） |
| 红河 | `honghe` | ✅ 已接入 | 红河州图书馆（图创 Interlib） |
| 德宏 | `dehong` | ✅ 已接入 | 德宏州图书馆（图创 Interlib） |
| 怒江 | `nujiang` | ✅ 已接入 | 怒江州图书馆（图创 Interlib） |
| 德清 | `deqing` | ✅ 已接入 | 德清县图书馆（图创 Interlib，检索走内嵌 Solr） |
| 西双版纳 | `xishuangbanna` | ✅ 已接入 | 西双版纳州图书馆（图创 Interlib，检索走内嵌 Solr） |
| 更多城市 | — | 欢迎提需求或贡献适配器 | 北京等因站点侧限制暂未接入，详见 docs/data-sources/README.md |

## 安装

### Claude Code

```bash
claude mcp add mcp-library-search -- uvx mcp_library_search
```

### Claude Desktop

在 `claude_desktop_config.json` 里加：

```json
"mcpServers": {
  "mcp-library-search": {
    "command": "uvx",
    "args": ["mcp_library_search"]
  }
}
```

改完重启桌面版。

## 使用

接入后提供 3 个 tool，查询链路为：先 `search_books` 按关键字找到 `book_id`，再用它查馆藏或详情。都带 `region` 与 `city` 两个定位参数：`region` 是地区标识（取域名后缀），默认 `cn`（中国）；`city` 默认 `shanghai`。未接入的地区或城市会返回明确提示：

| tool | 作用 |
|---|---|
| `search_books(keyword, region, city, page, limit)` | 按关键字（书名、ISBN、作者等）搜书，返回分页列表，每条带 `book_id` 和可借概况 |
| `find_book_availability(book_id, region, city, only_available)` | 查这本书在哪些馆有、是否可借，可借的馆排前面；`only_available=False` 时已借出的馆藏带预计归还时间（`due_date`） |
| `get_book_detail(book_id, region, city)` | 查这本书的完整介绍（ISBN、索书号、内容简介） |

典型用法：对 Claude 说"帮我查《三体》在哪个馆能借到" → 搜书拿到 `book_id` → 查各馆可借状态 → 就近推荐。

## 赞赏

如果这个项目帮到了你，欢迎打赏支持：

<a href="https://github.com/cnderrick/mcp_library_search/raw/main/assets/alipay.JPG"><img src="https://github.com/cnderrick/mcp_library_search/raw/main/assets/alipay.JPG" width="240" alt="支付宝收款码"></a>
<a href="https://github.com/cnderrick/mcp_library_search/raw/main/assets/wxpay.JPG"><img src="https://github.com/cnderrick/mcp_library_search/raw/main/assets/wxpay.JPG" width="240" alt="微信收款码"></a>

## 致谢

- [shanghai-library-book-search-python](https://github.com/ZedeX/shanghai-library-book-search-python)——上海图书馆检索能力的来源（Apache-2.0）。

完整的第三方组件列表、归属与变更说明见 [NOTICE](NOTICE)。
