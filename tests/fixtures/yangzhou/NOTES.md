# 扬州 fixture 字段侦察结论（实抓 2026-10-02）

**站点**：`http://ytlmopac.cn:8080` ——「扬州市图书馆联盟馆藏书目检索 v1.0」，
汇文 Libsys/uopac（Struts2），与南京金陵源（`uopac.jllib.cn`）**同一套系统**，
页面结构逐项同构（解析器与金陵共用 `uopac/` 家族模块）。实抓方式：只读 GET，
间隔 ≥2 秒。

## 一、securitycam 反爬（本站与金陵的唯一差别）

金陵源匿名全通；**扬州站全路径都要求 `securitycam` cookie**，缺 cookie 时返回
约 2.5KB 的 JS 壳页（HTTP 200，不是 403），壳页用 `/aes.min.js`（slowAES）
解密出 cookie 后跳回带 `?securitycam=1` 的原 URL。

实测对照（同一个 URL，`;jsessionid=` 带不带都一样）：

| 请求 | 结果 |
|---|---|
| 不带 cookie | 200，2.5KB JS 壳页 |
| 带 `Cookie: securitycam=6322e5171be855cb6e0f4e8b640895e6` | 200，真结果页（含 `<div id="found">`） |

**壳页是静态挑战**：把两次壳页（不同 URL 触发，2497B / 2540B / 2577B）逐字节
对比，**只有 `location.href` 那行回显的请求 URL 不同**，`a`（key）`b`（IV）
`c`（密文）三个常量完全相同：

```
key(a) = e902d089ea24d86c70281f76469c01a5
iv (b) = 0893562f12e89d337c7737e6151cc6d9
ct (c) = 2d2be258dcd0fce064f17c8a56de01b0     ← 壳页里是明文十六进制字面量
```

单块 AES-128-CBC（`slowAES.decrypt(c, 2, a, b)`，密文恰好 16 字节）→
**cookie 是固定值**：

```
securitycam=6322e5171be855cb6e0f4e8b640895e6
```

所以适配器**不移植 slowAES、也不写 JSFuck 解码器**，直接在 `UopacConfig`
里带这个常量 cookie 即可。壳页 `expires` 写到 2037 年，实测跨多日多请求恒定。

**常量轮换了怎么办**：适配器识别到响应又变回壳页会抛明确错误（而不是静默
空结果）。重算一条命令（`/aes.min.js` + 壳页内联脚本，node 跑一遍官方实现）：

```bash
curl -s "http://ytlmopac.cn:8080/uopac/s/search.action" -o /tmp/shell.html
curl -s "http://ytlmopac.cn:8080/aes.min.js" -o /tmp/aes.min.js
node -e '
const fs=require("fs"),vm=require("vm");
const s=fs.readFileSync("/tmp/shell.html","utf8");
const m=/<script>([\s\S]*?)<\/script>/.exec(s)[1];
let c=null;const box={document:{set cookie(v){c=v},get cookie(){return c}},
  location:{set href(v){},get href(){return""}}};
vm.createContext(box);vm.runInContext(fs.readFileSync("/tmp/aes.min.js","utf8")+"\n"+m,box);
console.log(c);'
```

## 二、检索（`/uopac/s/search_result.action`）

参数与金陵同构：`q`（关键词）、`meta`（20 任意 / 11 题名 / 12 责任者 /
14 ISBN / 15 主题 / 16 分类…）、`page`（从 1 起）。另可选 `groupId` 锁成员馆组，
**当前不启用**（全市联盟口径）。

- 结果页标记 `<div id="found">`；总数在 `有 <font color="red">N</font> 项`；
  分页 `<font color=red>P</font>&nbsp; / &nbsp;<font color=black>T</font>`。
- 每页固定 20 条（`limit` 对源站无效），条目块 `<div class="searchcontent">`，
  条目链接 `detail.action[;jsessionid=…]?id=<数字>`（Tomcat 裸请求会 URL 重写，
  uopac 家族正则已容忍）。
- 元信息行「责任者 / 出版社 / ISBN / 出版年」固定四段，例：
  `刘慈欣原著 / 浙江文艺出版社  / 9787533974022 / 2024`。
- 「所在馆：」一行列出全部持有馆，多馆以空白分隔：
  `扬州市图书馆 … 扬州市邗江区图书馆`。
- **ISBN 索引是「存储原样」前缀匹配**（同金陵）：`978-7-5339-7402-2` 命中 1 条，
  纯 13 位 `9787533974022` 命中 0 条，数字间插 `*` 的通配
  `9*7*8*7*5*3*3*9*7*4*0*2*2` 命中 1 条 → 走金陵同一套通配策略（`meta=14`）。

实测样本：`q=三体&meta=20` → 总数 73、4 页、每页 20 条。

## 三、详情（`/uopac/s/detail.action?id=<数字>`）

`<dl>` 里 `<dt>字段名</dt><dd>值</dd>`，字段名与金陵完全一致：
`题名/责任者`、`出版发行项`（形如「杭州:浙江文艺出版社,2024」）、`ISBN`、
`提要文摘附注`（＝简介）、`中图法分类号`。**无索书号字段**——`call_number`
照金陵/重庆先例恒空串，不拿中图法分类号冒充。

详情页 id 是 uopac 书目 id（`780232`），与代理 URL 里的 `marc_no=0000984184`
不是一回事。

## 四、馆藏（`ajax_holding.action` 服务端代理）

详情页每个持有馆一个 `<li><a href="#loca_XX">馆名</a></li>` tab，
`<div id="loca_XX">` 里的 `<span id="data">` 是相对 URL，经
`/uopac/s/ajax_holding.action` 由 uopac 服务端代理到成员馆自站的
`opac.yzlib.cn:8080/opac/libsys_view.php?libCode=…`（与金陵同一形态）。

实测：`780232` 只有 YZLIB 一个 tab；`1054519` 有 `YZLIB`（扬州市图书馆）与
`YZHJQG`（扬州市邗江区图书馆）两个 tab，各自取回各自的馆藏表。

馆藏表列序与金陵逐列相同：
`索书号 | 条码号 | 年卷期 | 校区 | 馆藏地 | 馆藏书刊状态`，
行标记 `<tr align="center" bgcolor="#FFFFFF">`。

**状态词表**：实测见「可借」与「借出」两种裸词，**未见**金陵那种
「借出-应还日期：YYYY-MM-DD」形态（扬州 `libsys_view.php` 这版不给应还日期）。
按家族同一口径处理：`可借` → `available=True`；其余（含「借出」与词表外）
保守 `False`，**状态原值照登**，`due_date` 认不到标准形态就是空串、不猜。

实例（`780232`，扬州市图书馆）：4 册 = 3 可借 + 1 借出；
校区/馆藏地组合有「委托借阅 网约书」「总馆 少儿外借室」等。

## 五、fixture 清单

| 文件 | 内容 |
|---|---|
| `uopac_challenge.html` | 无 cookie 时的 2497B JS 壳页（静态挑战，含 a/b/c 常量） |
| `uopac_result_santi.html` | `q=三体&meta=20&page=1`：总数 73、4 页、20 条 |
| `uopac_result_santi_p2.html` | 同上的第 2 页（首条《唐宋词三体钢笔字帖》） |
| `uopac_result_empty.html` | `q=zzzzqqqxyz`：总数 0、无分页区、0 条（`#found` 仍在） |
| `uopac_result_isbn_wild.html` | `q=9*7*8*7*5*3*3*9*7*4*0*2*2&meta=14`：1 条 |
| `uopac_detail_multi.html` | `id=1054519`：两个馆 tab（YZLIB / YZHJQG） |
| `uopac_detail_single.html` | `id=780232`：单 tab（YZLIB） |
| `uopac_holding_yzlib.html` | 扬州市图书馆馆藏表：4 册（3 可借 / 1 借出） |
| `uopac_holding_hjq.html` | 扬州市邗江区图书馆馆藏表：1 册可借 |
