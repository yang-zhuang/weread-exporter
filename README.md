# 微信读书导出工具

> **本仓库 fork 自 [drunkdream/weread-exporter](https://github.com/drunkdream/weread-exporter)（MIT 许可）**，感谢原作者与全部贡献者。
> 相对上游改了什么 → [本仓库相对上游做了什么](#本仓库相对上游做了什么)；代码怎么组织 → [代码组织结构](#代码组织结构)。

> ⚠️ **先用「接管模式」再导出（强烈建议）。** 默认的 `python -m weread_exporter -b <id>` 会自己启动一个临时 profile 的浏览器、再把 cookie 文件注进去，对微信读书来说等价于「一台从没见过的设备，突然用你的账号把整本书从头翻到尾」——这是最容易被风控的路径。请先按下方「降低风控风险 → 接管模式」操作，用你手动登录过的真实浏览器来跑。

## 本仓库的来历与致谢

本仓库是 **[drunkdream/weread-exporter](https://github.com/drunkdream/weread-exporter)** 的 fork。原项目通过 Hook 页面 Canvas 拿到绘制文本的思路、以及 epub/pdf/mobi 的导出链路，全部由原作者实现，本仓库在此之上继续开发。

- 上游仓库：<https://github.com/drunkdream/weread-exporter>
- 本 fork：<https://github.com/yang-zhuang/weread-exporter>
- 许可：**MIT**。上游只把许可写在 `setup.py` 的 `license="MIT"` 字段里、并未附协议全文；本仓库补齐了 [`LICENSE`](LICENSE)，版权行保留原作者，另列本 fork 的修改
- 本仓库的本地基线：上游提交 [`80a9ccb`](https://github.com/drunkdream/weread-exporter/commit/80a9ccb01647951cfac70f4554eb7741089f0263) *Fixed the command to start Chrome under Arch Linux (#121)*（2026-03-21）

上游共有 88 个提交，作者包括 **drunkdream**（56）、**shadowyang**（29）、Jiancong Zhu、Hu Jin、Mingxi Wu。**本仓库上游部分的版权归原作者所有，按 MIT 条款使用。**

## 本仓库相对上游做了什么

以下相对上游基线 `80a9ccb` 统计（`git diff --numstat --diff-filter=M 80a9ccb HEAD`，只计被修改的已有文件、不含新增）：**代码与配置合计 +615 / −227 行**，另新增 5 个 `.py` 文件、1 个 `LICENSE` 与 1 个 `scripts/` 目录（16 个 `.sh`）；`README.md` 自身另 +450 / −2。

> 统计不含本文档自身——README 的增删是自指的，写进来会随文档更新立刻过期。

### 新增文件

| 文件 | 行数 | 职责 |
|---|---|---|
| `weread_exporter/categories.py` | 343 | 分类/榜单树发现、书单抓取、中文名与代码互转 |
| `weread_exporter/crawler.py` | 220 | 业务编排：单本导出 `export_book` / 全量遍历 `crawl_all` |
| `weread_exporter/injections.py` | 85 | 注入浏览器的 JS 常量（stealth 补丁、headless/验证码探测） |
| `tests/test_weread_exporter.py` | 449 | 回归测试，29 项，无网络无浏览器 |
| `launch_chrome.py` | 115 | 接管模式：启动带调试端口的常驻 Chrome |
| `LICENSE` | 22 | MIT 协议全文。上游只声明了 `license="MIT"` 却没附全文，本仓库补齐；版权行为两行标准格式（`drunkdream` / `yang-zhuang`），不带额外缩进行——**这直接决定 GitHub 能否把许可证识别成 MIT** |
| `scripts/*.sh` | 各 7~14 行 | 常用命令封装：注释头（用途 / 用法 / 逐参数解释）+ 一行 `python ...` 命令，覆盖本文档出现的全部用法（见「常用命令脚本」） |

### 修改文件

| 文件 | 增删 | 改动要点 |
|---|---|---|
| `weread_exporter/webpage.py` | +297 / −110 | 接管模式、风控检测与等待、免登录、console 日志节流 |
| `weread_exporter/export.py` | +182 / −15 | 付费墙检测、免费区优先、图片本地化、中文可读元数据 |
| `weread_exporter/__main__.py` | +106 / −95 | 拆出 `crawler.py`，本文件回归纯 CLI |
| `weread_exporter/utils.py` | +8 / −0 | 新增 `RiskControlError` 异常 |
| `README.md` | 本文档扩充 | 新增「来历与致谢」「相对上游的改动」「代码组织结构」三节，并把「常用命令脚本」扩成全部 16 个脚本的对照表 |
| `.gitignore` | +16 / −0 | 忽略调试产物、日志轮转产物、pytest 缓存、接管模式的 Chrome profile（`data/`，含登录态） |
| `setup.py` | +6 / −4 | `url` / `author` / `author_email` 从上游改指本 fork；`description` 补全实际支持的 5 种格式（`md/epub/pdf/mobi/txt`） |
| `.gitmodules` | −3 / −0 | 删除（详见文末「已删除的配置」） |

### 功能层面的改动

**1. 风控防护（本仓库最大的改动）**

| 手段 | 说明 |
|---|---|
| 接管模式 `--cdp-endpoint` | 不再自建临时 profile，改为接管你手动登录过的常驻 Chrome，指纹与登录态跨次稳定（配合 `launch_chrome.py`） |
| 验证码检测与人工过码 | `is_verify_page()` / `wait_verify_cleared()` 只检测**可见** DOM 与页面文本（不扫打包 JS 源码，那是误报根因），命中后等你在窗口里过码，最长 `--verify-timeout` 秒 |
| 间隔抖动 `--jitter` | 固定节拍本身就是机器特征，叠加随机抖动去掉周期性 |
| 章节乱序 `--no-shuffle` | 默认打乱抓取顺序，请求序列不再严格 1→N；写入顺序不变 |
| 风控冷却 `--cooldown` | 被拦截后冷却默认 600 秒再退出，避免你立刻重跑 |

新增 `RiskControlError`（`utils.py`）区分「重试有用」（加载失败）与「重试只会再撞验证码」（风控）——后者立即中止，不做无意义重试。

**2. 免登录模式 `--no-login`**

实测正文接口不校验登录态，免费章节无 cookie 即可读全文，账号层面零封号风险。

**3. 全量遍历分类/榜单（不传 `-b`）**

自动发现 7 个榜单 + 21 个主分类 × 全部子分类，按分类目录保存；同一本书按 bookId 去重。

**4. 付费墙处理**

`is_paywall_text` 检测 + 免费区优先抓取 + 撞墙后**往回**随机（而非继续往后硬撞）。详见「免登录模式 → 边界与注意」。

**5. 元数据完整化与可读化**

`get_book_info` 提取首页全部信息（分类/出版社/ISBN/定价/字数/评分分布/榜单/版权等 92 字段），输出 `meta.json`（机器版）+ `详情.json`（中文人读版），均 `ensure_ascii=False`。

**6. 图片本地化与容错**

远程图片下载到 `images/` 并替换成相对路径；付费墙页面容错返回空而非崩溃；移除 `.bak` 冗余快照（旧实现会与替换后的 `.md` 并存，容易误判成「没替换」）。

**7. 结构整理**

`__main__.py` 拆出 `crawler.py`（业务逻辑）与 `injections.py`（JS 常量），其余模块大小合理，未做进一步拆分。

**8. 跨平台与稳定性修复**

- `_check_chrome` 补 Windows 常见安装路径
- Chrome 启动加 `--no-proxy-server`（本机代理会让 weread 请求超时）
- weasyprint 延迟导入，`-o md` 不再强制依赖它
- **移除 `asyncio.wait_for` 对 `goto_chapter` 的包裹**：超时取消会让 CDP 已拦截的请求永久挂起，页面后续加载全部卡死、hook 脚本注入失败（表现为 `canvasContextHandler is not defined`）；且 90 秒的包裹会误杀最长 600 秒的撞码等待

**9. console 日志节流**

canvas 刷屏曾把单个日志撑到 15 MB（14.8 万行里唯一内容仅 333 行）→ 连续重复折叠 + 4 MB 上限轮转。详见「运行日志与磁盘占用」。

**10. 回归测试**

`tests/test_weread_exporter.py`（449 行 / 29 项）全程 fake：无网络、无浏览器、0.2 秒跑完。覆盖 wr_hash、付费墙检测、图片本地化、免费区优先、撞墙回退、元数据可读性、结构拆分、CLI 参数、日志节流。

## 代码组织结构

```
weread-exporter/
├─ weread_exporter/                    主包
│  ├─ __main__.py               245 行  纯 CLI：参数解析、环境 patch、日志初始化
│  ├─ crawler.py                220 行  业务编排：单本导出 / 全量遍历
│  ├─ webpage.py                863 行  页面对象：启动与接管、元数据解析、章节抓取、hook 注入、风控检测
│  ├─ export.py                 562 行  导出器：抓章节、图片本地化、付费墙检测、生成 epub/pdf/mobi/txt
│  ├─ webproxy.py               558 行  CDP 请求拦截框架（上游原样保留）
│  ├─ categories.py             343 行  分类/榜单发现与书单抓取
│  ├─ utils.py                  215 行  工具：wr_hash、fetch、md5、异常类型、cairo 检测
│  ├─ injections.py              85 行  注入浏览器的 JS 常量
│  ├─ hook.js                   270 行  ★ Canvas Hook 脚本（注入页面，抓正文的核心）
│  ├─ epub.css                  197 行  epub 样式
│  ├─ style.css                 194 行  pdf 样式
│  └─ bin/                             二进制依赖：linux 27.3 MB（kindlegen）+ win32 15.3 MB（cairo/gtk DLL）
├─ tests/
│  ├─ test_weread_exporter.py   449 行  回归测试（fake，29 项）
│  └─ test_utils.py               6 行  wr_hash 校验
├─ scripts/                            常用命令封装，每个 .sh = 注释头（用途/用法/逐参数解释）+ 一行 python 命令
│  ├─ install.sh                       安装依赖（pip install -e .）
│  ├─ launch-chrome.sh                 启动接管用的常驻 Chrome
│  ├─ list-categories.sh               打印分类树
│  ├─ export-book.sh                   单本导出 epub + pdf（接管模式，推荐）
│  ├─ export-book-safe.sh              单本导出，显式写全风控参数
│  ├─ export-book-default.sh           单本导出（默认模式，风控风险最高）
│  ├─ export-book-force-login.sh       单本导出 + 强制先登录
│  ├─ export-book-formats.sh           单本导出 md/epub/pdf/mobi/txt 全格式
│  ├─ export-book-nologin.sh           免登录单本前 2 章（markdown）
│  ├─ export-book-nologin-all.sh       免登录单本全部免费章
│  ├─ crawl-all.sh                     全量遍历榜单 + 分类
│  ├─ crawl-categories.sh              只遍历指定分类/榜单
│  ├─ crawl-smoke.sh                   小批量冒烟（文学分类）
│  ├─ crawl-nologin.sh                 免登录全量遍历
│  ├─ run-tests.sh                     跑回归测试（unittest）
│  └─ run-all-tests.sh                 跑全部测试（pytest）
├─ launch_chrome.py             115 行  接管模式：启动常驻 Chrome（--remote-debugging-port）
├─ build.py                     128 行  上游的 PyInstaller 打包脚本
├─ setup.py                      60 行  安装脚本（`url`/`author` 已指向本 fork）
├─ requirements.txt
├─ LICENSE                             MIT 协议全文（版权行保留原作者 drunkdream）
└─ README.md
```

各模块的包内依赖（单向，无循环）：

```
__main__.py   →  crawler.py, categories.py, utils.py
crawler.py    →  webpage.py, export.py, categories.py, utils.py
export.py     →  webpage.py, utils.py
webpage.py    →  webproxy.py, injections.py, utils.py
categories.py →  utils.py
webproxy.py   →  utils.py
utils.py      →  (无包内依赖)
injections.py →  (无包内依赖)
```

两个容易踩的点：

- `utils.py` 里 `cairocffi` 是**延迟导入**（运行时检测 cairo 是否安装），不是死代码，别当成未使用的 import 删掉；
- `utils.py` 的 `wr_hash` 及其 `_0x22edbf` 一类变量名是从微信读书混淆 JS 逐行逆向来的，**变量名与 JS 原文一一对应是排查哈希正确性的依据**，重命名会破坏对照关系。

## 实现原理

通过Hook Web页面中的Canvas函数，获取绘制到Canvas中的文本及样式等信息，转换成markdown格式，保存到本地文件，然后再转换成最终的epub或pdf格式，而mobi格式则是使用kindlegen工具从epub格式转换来的。

## INSTALL

```bash
$ pip3 install -e .
```

## USAGE

```bash
$ python -m weread_exporter -b $book_id -o epub -o pdf
```

> 获取书籍ID的方法：在页面`https://weread.qq.com/`搜索目标书籍，进入到书籍介绍页，URL格式为：`https://weread.qq.com/web/bookDetail/08232ac0720befa90825d88`，这里的`08232ac0720befa90825d88`就是书籍ID。

`-o`参数用于指定要保存的文件格式，**可以重复指定多个**，目前支持：`md`、`epub`、`pdf`、`mobi`、`txt`，生成的文件在当前目录下的`output`目录中。不传 `-o` 时默认只生成 `epub`（指定 `-o mobi` 会自动附带一份 `epub`，因为 mobi 是从 epub 转出来的）。

`epub` 适合手机端访问，`pdf` 适合电脑端访问，`mobi` 适合 kindle 访问（⚠️ **仅 Linux 可生成**：`crawler.py` 里对非 Linux 平台只打一行 error 后跳过），`md` 是正文原样、最适合直接读，`txt` 是纯文本。

命令行还支持一个可选参数`--force-login`，默认为`False`，指定该参数时，会先进行登录操作。

> ⚠️ 上面的默认命令是**高风险路径**（每次新建临时 profile + 注入 cookie）。如果只是想跑通导出，可以用它；如果想长期、多次使用而不被风控，**务必改用下面的「接管模式」**。

> 也可以**不传 `-b`**：自动全量遍历微信读书全部 7 个榜单 + 21 个主分类 × 全部子分类，并按分类保存。见下方「全量遍历分类/榜单」。

### 常用命令脚本（scripts/）

`scripts/` 把**本文档里出现的每条命令**都封装成了一个脚本。每个 `.sh` 的结构固定为：**注释头 + 一行命令**——

- **注释头**：三段固定格式，`# 用途:` 说这个脚本干什么，`# 用法:` 说怎么调、要传什么，`# 参数:` **逐条解释命令里出现的每一个参数**（含默认值），最后一行是命令本身；
- **命令**：永远只有一行、以 `python ` 开头，没有循环、没有 shell 变量（`"$1"` 除外）、没有 `cd`。想改参数就改这一行。

```sh
# 用途: 免登录抓单本前 2 章 markdown，用来快速验收导出效果（不碰账号，零封号风险）
# 用法: sh scripts/export-book-nologin.sh <book_id>
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   -b "$1"                    book-id，书 ID（详情页 URL 末段），必填
#   --no-login                 免登录：不读也不写 cookie、不做登录，只下免费章节
#   -o md                      只输出 markdown（不依赖 weasyprint，跑得最快）
#   --chapters-per-book 2      每本最多抓 2 章；单本模式下不传这个参数表示「全量」，
#                              传 0 同样表示全量，这里给 2 是为了几秒内出结果
python -m weread_exporter -b "$1" --no-login -o md --chapters-per-book 2
```

用法是 `sh scripts/xxx.sh`，**须在仓库根目录执行**（命令里的 `python -m weread_exporter` 依赖当前目录在 `sys.path` 上）。

**环境准备**

| 脚本 | 命令（脚本最后一行） | 说明 |
|---|---|---|
| `install.sh` | `python -m pip install -e .` | 安装依赖（可编辑模式），等价于上面「INSTALL」那节 |
| `launch-chrome.sh` | `python launch_chrome.py` | 启动接管用的常驻 Chrome（调试端口 9222）。首次需在弹出的窗口里扫码登录。端口已在用时只提示、不重复启动 |

**单本导出（`-b`）**

| 脚本 | 命令（脚本最后一行） | 说明 |
|---|---|---|
| `export-book.sh <book_id>` | `python -m weread_exporter -b "$1" -o epub -o pdf --cdp-endpoint http://127.0.0.1:9222` | ★推荐。接管模式导出 epub + pdf，需先跑 `launch-chrome.sh` |
| `export-book-safe.sh <book_id>` | 同上，另加 `--load-interval 30 --jitter 5 --verify-timeout 600 --cooldown 600` | 把「新增参数」表里的风控参数全部显式写出，慢但最稳 |
| `export-book-default.sh <book_id>` | `python -m weread_exporter -b "$1" -o epub -o pdf` | 默认模式（自建临时 profile + 注入 cookie）。**风控风险最高**，仅用于跑通流程 |
| `export-book-force-login.sh <book_id>` | `python -m weread_exporter -b "$1" -o epub --force-login` | 默认模式 + 强制先登录（`--force-login`） |
| `export-book-formats.sh <book_id>` | `python -m weread_exporter -b "$1" -o md -o epub -o pdf -o mobi -o txt --cdp-endpoint http://127.0.0.1:9222` | 一次导出全部 5 种格式。注意 **`mobi` 只有 Linux 能生成**（`crawler.py` 里 `sys.platform != "linux"` 时只打一行 error），Windows/macOS 上会被跳过，其余 4 种照常 |
| `export-book-nologin.sh <book_id>` | `python -m weread_exporter -b "$1" --no-login -o md --chapters-per-book 2` | 免登录抓前 2 章 markdown，用来快速看效果 |
| `export-book-nologin-all.sh <book_id>` | `python -m weread_exporter -b "$1" --no-login` | 免登录抓全部免费章（不传 `--chapters-per-book` 即全量，撞付费墙自动跳过） |

**分类/榜单遍历（不传 `-b`）**

| 脚本 | 命令（脚本最后一行） | 说明 |
|---|---|---|
| `list-categories.sh` | `python -m weread_exporter --list-categories` | 打印分类树后退出，不抓书 |
| `crawl-all.sh` | `python -m weread_exporter --cdp-endpoint http://127.0.0.1:9222 --per-category 2 --chapters-per-book 1` | 全量遍历 7 榜单 + 21 主分类 × 全部子分类（每分类 2 本、每书 1 章的风控安全默认） |
| `crawl-categories.sh <分类>` | `python -m weread_exporter --cdp-endpoint http://127.0.0.1:9222 --categories "$1" --per-category 5 --chapters-per-book 1` | 只遍历指定分类/榜单，逗号分隔，中文名或代码均可 |
| `crawl-smoke.sh` | `python -m weread_exporter --cdp-endpoint http://127.0.0.1:9222 --categories 300000 --per-category 2 --chapters-per-book 1 --load-interval 3 --jitter 1` | 小批量冒烟：只跑「文学」（代码 `300000`），快节奏参数，用来验证整条链路 |
| `crawl-nologin.sh` | `python -m weread_exporter --no-login --per-category 2 --chapters-per-book 1` | 免登录全量遍历，只下每本书的免费章（零账号风险） |

**测试**

| 脚本 | 命令（脚本最后一行） | 说明 |
|---|---|---|
| `run-tests.sh` | `python tests/test_weread_exporter.py` | 跑回归测试（29 项，无网络无浏览器，约 0.2 秒） |
| `run-all-tests.sh` | `python -m pytest tests/ -v` | 跑 `tests/` 下全部测试（含 `test_utils.py` 的 `wr_hash` 校验），需要环境里装了 pytest |

```bash
$ sh scripts/launch-chrome.sh                                # 另开一个窗口扫码登录
$ sh scripts/export-book.sh 0da329707210329f0da4d39          # 接管模式导出 epub + pdf
$ sh scripts/export-book-nologin.sh 0da329707210329f0da4d39  # 免登录抓前 2 章
$ sh scripts/crawl-categories.sh "文学,飙升·出版"              # 只跑这两个分类
$ sh scripts/run-tests.sh
```

三点说明：

- **`"$1"` 就是命令行传进来的第一个参数**：`export-book*.sh` 收书 ID，`crawl-categories.sh` 收分类名。**必须传参**，不传会退化成 `-b ""` / `--categories ""` 而报错。其余脚本的参数都写在注释头和最后那行命令里，想调直接改。
- **用 `sh scripts/xxx.sh` 而不是 `./scripts/xxx.sh`**：脚本里刻意只留了一行命令、没写 shebang，交给 `sh` 执行即可。Windows 下 `.sh` 需要 Git Bash / WSL；PowerShell 里等价写法就是把最后那行 `python ...` 原样敲一遍。
- **`crawl-categories.sh` 传中文名时留意 Windows 编码**：Git Bash 默认 UTF-8 没问题，若你的终端是 GBK，中文参数可能传成乱码——这种情况传分类代码更保险（`文学` = `300000`，完整对照可用 `sh scripts/list-categories.sh` 打印，或看 `cache/categories.json`）。
- **每个脚本的注释头都逐条解释了参数**，包括默认值；不确定某个参数什么作用时直接 `cat scripts/xxx.sh`，不用回来翻 README。

## 降低风控风险（强烈建议）

### 默认模式的风险在哪

默认情况下，工具自己启动一个 Chrome，profile 用的是 `tempfile.mkdtemp()` 每次新建的临时目录，然后把 cookie 文件注入进去（见 `weread_exporter/webpage.py` 的 `launch()` 和 `_inject_cookie()`）。

对微信读书来说，这个组合等价于：**一台从没见过的设备，突然拿着你的身份把整本书从头翻到尾**。这是原实现最大的风控隐患，跟用没用 CDP 没有关系 —— pyppeteer 本身就是 CDP 客户端，两种模式底层协议是一样的。

另外原实现没有任何风控检测：一旦被拦截，只会表现为章节加载超时，你分不清是网络问题还是被风控了。

### 接管模式：复用你手动登录的浏览器

改成接管一个固定 profile、你手动登录过的 Chrome 之后，指纹和登录态都是真实且跨次稳定的。

```bash
# 第一步：启动一个常驻 Chrome，会打开微信读书
$ python launch_chrome.py

# 在弹出的窗口里扫码登录（只需一次，登录态保存在 data/weread-profile 里）

# 第二步：用 --cdp-endpoint 接管它，而不是自己启动浏览器
$ python -m weread_exporter -b $book_id -o epub --cdp-endpoint http://127.0.0.1:9222
```

`launch_chrome.py` 会带 `--remote-debugging-port=9222` 和一个独立的 `--user-data-dir` 启动 Chrome。用独立 profile 而不是你日常浏览器的 profile，是因为调试端口没有任何鉴权，本机任何进程都能驱动这个浏览器。可以用 `--port` 和 `--profile-dir` 改。

profile 默认落在仓库的 `data/weread-profile/`，**里面装着你的微信读书登录态**（cookie 等），已被 `.gitignore` 忽略——别手动 `git add -f` 把它提交上去。

接管模式和默认模式有三处刻意的不同：

| | 默认模式 | 接管模式 |
|---|---|---|
| 浏览器来源 | 自己 launch，临时 profile | 接管常驻 Chrome，固定 profile |
| 登录态 | cookie 文件注入 | 浏览器里真人登录，工具读回来存盘 |
| stealth 补丁 | 打（`evaluateOnNewDocument` 覆盖 `navigator.webdriver` 等） | 不打 |
| viewport | 覆盖成 0x0 | 不动，保持标签页正常可见 |

不打补丁是因为真实浏览器本来就没有自动化痕迹，反过来覆盖 `navigator.webdriver`、`hasOwnProperty` 只会多一处异常特征。不覆盖 viewport 是为了让你能看见页面 —— 撞验证码时要靠你在那个窗口里手动过码。

### 撞到验证码怎么办

接管模式新增了风控检测（`is_verify_page()` / `wait_verify_cleared()`）：每章导航后检查可见的验证码 DOM 和页面文本，命中就打印提示并轮询等待，**你在浏览器窗口里手动过码，脚本感知到页面恢复后自动继续**，最长等 `--verify-timeout` 秒（默认 600）。

检测只看可见元素和 body 可见文本，不扫打包 JS 源码 —— 那是误报的根因。也刻意没把裸的"验证码"三个字作为信号，否则登录组件上的"获取验证码"按钮会误报。

超时还没过，就抛 `RiskControlError` 直接中止，不会无意义地重试。

### 新增参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--cdp-endpoint` | 无 | 接管已启动的 Chrome，如 `http://127.0.0.1:9222`。不传则走原来的自启动模式 |
| `--verify-timeout` | 600 | 检测到验证码时，等待人工过码的最长时间（秒） |
| `--jitter` | 5 | 章节间隔的随机抖动（秒），实际间隔为 `--load-interval` ± jitter |
| `--no-shuffle` | 关 | 默认打乱章节抓取顺序（向服务器的请求不再严格 1→N 线性），写入仍按原序；传它则按原顺序抓取 |
| `--cooldown` | 600 | 被风控拦截后的冷却时间（秒）。冷却期间进程不退出、防止你立刻重跑，结束后以非零码退出 |

`--jitter` 的意义：固定 30 秒一章的节拍本身就是一个机器特征。叠加抖动后平均值不变，但去掉了周期性。

`--no-shuffle` 的意义：真人极少严格 1→N 顺读，线性抓取是强自动化信号。默认每次随机打乱抓取顺序（断点续传不受影响——已下载的章节会自动跳过），每章仍按它在书中的原始下标写入，所以导出的文件与 epub/pdf 章节顺序完全不变，只是请求序列不再可预测。

### 其他建议

- **不要用 `--headless`**。原项目自己在 `webpage.py` 里就写着「浏览器检测到Headless模式，继续执行可能导致帐号被封禁」。现在传 `--headless` 会额外打一条警告。
- **间隔别调太小**。`--load-interval` 默认 30 秒/章，这已经是很好的保护，慢本身就能让行为曲线接近真人阅读。相比之下番茄小说那种 0~0.3 秒/章是靠"撞码就等人过"兜底，不是靠"不被风控"。
- **`--use-default-profile` 在 Chrome 136+ 已经失效**，代码里有对应警告。想拿真实指纹请改用 `--cdp-endpoint`。

### 进一步的操作建议（代码之外的习惯）

接管模式已经把"指纹空白"这个最大隐患堵上了，但行为层面还能再收一收：

- **一次只导出一本书，不要连着导出几十本**。连发式批量行为是强信号；两本书之间最好隔几分钟、甚至分几天。
- **不要并发**。同时只跑一个 weread 导出进程，也别让别的脚本同时驱动同一个 Chrome。
- **保持浏览器窗口在前台、可见**。一来撞验证码时你能立刻手动过码；二来部分检测会看页面可见性，最小化或切到后台不如开着。
- **间隔别调太小**。`--load-interval` 默认 30 秒/章 + `--jitter 5` 已经是不错的拟人节奏，别为了快去压到几秒级。
- **撞到风控就停手冷却**。代码里 `RiskControlError` 触发后会自动冷却 `--cooldown` 秒（默认 600）再退出；冷却期间别手动再跑，当天尽量别再碰同一账号，硬刚只会加速封号。
- **用独立的 `data/weread-profile`，别指向日常浏览器 profile**。调试端口没有鉴权，本机任何进程都能驱动它；独立 profile 是安全上的取舍（牺牲一点"日常设备"相似性，换不被本地恶意进程劫持）。
- **账号别共用 / 别借**。风控往往按账号维度而非设备；一个账号的异常会连带它读过的所有书。

> 说明：以上基于代码事实与通用风控原理。微信读书具体的封号阈值和阶梯我没有可靠数据，不做断言。代码层已实现的拟人化手段包括：间隔抖动（`--jitter`）、打乱章节抓取顺序（`--no-shuffle` 可关）、风控冷却（`--cooldown`）。

## 全量遍历分类/榜单（不传 -b）

不传 `-b` 时，工具自动发现微信读书全部分类并按分类保存，与 fanqie-cdp-downloader 的分类下载模式同构。

### 用法

```bash
# 查看分类树（首次会抓 21 个分类页构建，缓存到 cache/categories.json）
$ python -m weread_exporter --list-categories

# 全量遍历：7 个榜单 + 21 个主分类 × 全部子分类（每分类取前 2 本、每书 1 章，风控安全默认）
$ python -m weread_exporter --cdp-endpoint http://127.0.0.1:9222

# 只遍历指定分类/榜单（中文名或代码，逗号分隔）
$ python -m weread_exporter --cdp-endpoint http://127.0.0.1:9222 \
    --categories 文学,飙升·出版 --per-category 5 --chapters-per-book 1
```

### 保存结构

```
output/
├─ 飙升·出版/《书名》_<bookId>/
├─ 热搜榜/《书名》_<bookId>/
├─ 精品小说/社会小说/《书名》_<bookId>/
├─ 文学/古典文学/《书名》_<bookId>/
└─ ...
```

同一本书出现在多个分类时**只存一份**（按 bookId 去重，目录落在首次出现的分类下），`meta.json` 记录它所属的全部分类。

### 数据来源（公开接口，无需登录）

| 接口 | 用途 |
|---|---|
| `weread.qq.com/web/category/<code>` | 分类页，`window.__INITIAL_STATE__` 里含子分类树 |
| `weread.qq.com/web/bookListInCategory/<code>?maxIndex=N` | 分类/榜单书单（榜单加 `&rank=1`） |

接口返回的数字 bookId 经 `wr_hash()` 转成 reader 用的 hash id，与页面 deepLink 完全一致（已实测验证：`wr_hash("34615967") == "0da329707210329f0da4d39"`）。

### 遍历模式参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `--list-categories` | 关 | 打印分类树后退出 |
| `--categories` | 全部 | 只遍历指定分类/榜单，逗号分隔，中文名或代码均可 |
| `--per-category` | 2 | 每个分类/子分类最多取前 N 本（0=不限制，单分类上限 1000 本） |
| `--chapters-per-book` | 遍历=1，单本=全量 | 每本书最多下载 N 章（0=全量） |
| `--no-login` | 关 | 免登录模式：不读/不写 cookie、不登录，只下载免费章节 |

### 风控说明

遍历模式默认**每本书只抓前 1 章**（开头通常是免费试读章），叠加接管模式、间隔抖动、章节乱序、撞码等待、风控冷却全部防护。测试时建议 `--per-category 2 --chapters-per-book 1 --load-interval 3 --jitter 1` 快速验证；正式批量导出再加大限量、调回慢间隔。

### 免登录模式（--no-login，零账号风险）

实测（2026-09-01，无 cookie 全新浏览器）：微信读书正文接口 `POST /web/book/chapter/e_0~e_3` **不校验登录态**，免费章节（每本书 `maxFreeChapter` 之前）无登录即可读全文——请求参数是前端本地算的签名 + 内容加密，不含任何登录凭据。只有划线/笔记等个人数据接口才要求登录。

```bash
# 免登录下载单本书的免费章节（不注入 cookie、不登录）
$ python -m weread_exporter -b $book_id --no-login

# 免登录全量遍历分类（只下每本书的免费章）
$ python -m weread_exporter --no-login --per-category 2 --chapters-per-book 1
```

**边界与注意**：
- **只能下免费章节**。超过 `maxFreeChapter` 的付费章会被服务端拒绝，工具检测到付费墙提示后自动跳过该章（`is_paywall_text` 启发式：内容极短且含"购买本章/解锁本章"等特征词），不会把购买提示当正文落盘。
- **免费区优先 + 付费墙回退**：元数据里的 `maxFreeChapter`（免费章数）用于预过滤——免费区的章优先抓、付费区垫底；运行中真撞到付费墙时，剩余顺序自动重排为「比首个付费章更靠前的未抓章节优先、随机」，往回找免费章而不是继续往后硬撞。
- **账号层面零封号风险**（没有账号可封），但 IP/设备层面仍有频率风控——实测连续高频请求会触发限流，依然要保持慢间隔。
- 与 `--force-login` 冲突（忽略后者）；与 `--cdp-endpoint` 同时用时仅不读取浏览器 cookie，建议直接去掉 `--cdp-endpoint`。
- `meta.json`、`详情.json` 均为中文可读格式（`ensure_ascii=False`）；章节内容里只有一张图片引用属正常——微信读书部分"章"本身就是整页图片扉页。

### 运行日志与磁盘占用

浏览器 console 会被原样落盘到根目录的 `<bookId>.log`。微信读书正文画在 canvas 上，console 会被 `fillRect`/`fillStyle` 疯狂刷屏——实测单次抓取产生 14.8 万行，其中**唯一内容只有 333 行（0.22%）**，无节流时单个日志能涨到十几 MB。

`handle_log`（`webpage.py`）已做两层节流：

- **连续重复折叠**：同一行反复刷只落一条，重复次数补记为 `^^^ 上一行重复 N 次`
- **大小上限轮转**：单个日志超过 `MAX_CONSOLE_LOG_BYTES`（4 MB）时归档为 `<bookId>.log.1` 后重新开始，只保留一代

`.log` 与 `.log.1` 均已被 `.gitignore` 忽略。如果确认不需要这份 console 日志，删掉根目录的 `*.log` 即可，不影响抓取。

### 每本书保存的元数据（首页信息全量）

书籍详情页（首页）的信息会完整保存，不再只有书名/作者/封面。`get_book_info` 从 `bookDetail` 页的 `__INITIAL_STATE__` 提取：分类（`category`/`categories`）、出版社（`publisher`）、出版时间、ISBN、定价、总字数、是否完结、免费章节数、评分（`newRating`/`ratingCount`/评分分布 `ratingDetail`/`newRatingDetail`）、所在榜单（`ranklist`）、版权信息（`copyrightInfo`）、作者分段（`authorSeg`）、标签（`bookTags`）等，并把完整的 92 字段原始 `bookInfo` 原样保留在 `book_info` 键下（零丢失）。

| 文件 | 位置 | 内容 |
|---|---|---|
| `meta.json` | 书目录（分类模式）或 `cache/<bookId>/`（单本模式） | 机器版完整元数据 + 章节目录，兼作断点续传状态 |
| `详情.json` | 书目录（分类模式） | 中文人读版：书名/作者/分类/标签/出版社/ISBN/定价/字数/评分分布/所在榜单/简介等 |

## 已删除的配置：`.gitmodules`

上游用 `.gitmodules` 把 `cache` 声明成一个 submodule（指向 `drunkdream/weread-books`）：

```ini
[submodule "cache"]
	path = cache
	url = https://github.com/drunkdream/weread-books.git
```

本仓库删除了该文件。依据是实测三条命令**全部无输出**：

```bash
$ git submodule status               # 无输出 → submodule 从未初始化
$ git config --get-regexp submodule  # 无输出 → .git/config 里没有对应条目
$ git ls-files -s cache              # 无输出 → git 索引里根本没有 cache
```

即它**从未生效**，且语义自相矛盾：`cache` 在本项目里是运行时数据目录（抓取的章节、图片、元数据），已被 `.gitignore` 忽略，不可能同时是别人的书库 submodule。删除后 `git status` 无任何异常。

## 许可

本仓库遵循 **MIT** 许可，协议全文见 [`LICENSE`](LICENSE)。上游部分（原作者 **drunkdream** 及全部贡献者）的版权归原作者所有，本仓库修改部分的版权归本 fork 作者。`LICENSE` 的版权行为两行标准格式：

```
Copyright (c) 2023 drunkdream
Copyright (c) 2026 yang-zhuang
```

三点说明：

- **年份 2023 的依据**：上游仓库的起始提交是 `2023-02-11` 的 *Initial commit*（`GET /repos/drunkdream/weread-exporter/commits?until=2023-03-01` 可复现）。两位署名的项目地址见上文「本仓库的来历与致谢」。
- **为什么要补全文**：上游只在 `setup.py` 里写了 `license="MIT"`，**从未附协议全文**——GitHub API 的 `GET /repos/drunkdream/weread-exporter/license` 返回 404，仓库根目录也没有 `LICENSE` 文件。而 MIT 条款本身就要求"上述版权声明和许可声明应包含在软件的**所有副本**中"，fork 对外分发正是"副本"，所以补一份全文既是合规要求，也让下游使用者有据可依。
- **版权行必须写成标准单行格式**：即 `Copyright (c) <年份> <署名>`，一行一条。**不要**在版权行下方再补缩进的 URL 或备注行——GitHub 的许可证识别只会剥离以 `Copyright` 开头的行，残留的 URL 行会被计入协议正文，使整份文件与标准 MIT 文本不匹配，徽章会显示成 **Other**（API 里是 `NOASSERTION`）而非 MIT。这是实测踩到的坑：同样的正文，只因为多了两行缩进 URL，就被判成了 Other。

## 免责申明

本工具仅作技术研究之用，请勿用于商业或违法用途，由于使用该工具导致的侵权或其它问题，该本工具不承担任何责任！
