> **复刻说明（Fork Notice）**
>
> 本项目复刻自 GitHub 用户 **drunkdream** 的 [`weread-exporter`](https://github.com/drunkdream/weread-exporter)（**MIT License**）。
> 本仓库为其 **v0.1.0（约 2024-03 的快照）** 的个人使用副本，并附带少量本地改动，详见文末「本仓库相对原版的改动」。
> 原作者保留全部著作权，本复刻仅作个人学习 / 研究使用。

# 微信读书导出工具

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

`-o`参数用于指定要保存的文件格式，目前支持的格式有：`epub`、`pdf`、`mobi`，生成的文件在当前目录下的`output`目录中。

`epub`格式适合手机端访问，`pdf`格式适合电脑端访问，`mobi`格式适合kindle访问。

命令行还支持一个可选参数`--force-login`，默认为`False`，指定该参数时，会先进行登录操作。

## 免责申明

本工具仅作技术研究之用，请勿用于商业或违法用途，由于使用该工具导致的侵权或其它问题，该本工具不承担任何责任！

---

## 本仓库相对原版（drunkdream/weread-exporter）的改动

本仓库基于 `drunkdream/weread-exporter` 的 **v0.1.0 快照（约 2024-03 下载）**，与原版的主要差异如下：

- **`aaaa.py`（已排除）**：原本地有一份用于练习的 Pyppeteer 脚本（抓取 `scrape.center` 示例站），与微信读书无关，属于个人临时测试文件，已从本仓库移除、不纳入版本库。
- **新增 `weread_exporter/bin/win32/chrome.exe`**：一份本地放置的 Chromium 二进制（约 15MB）。上游原版 `bin/win32` 中**并无此文件**；本项目通过 pyppeteer 自带机制管理 Chromium，故该二进制**未纳入版本库**（已在 `.gitignore` 中忽略）。
- **运行痕迹**：曾用本工具实际爬取过一本书（缓存目录 `weread_exporter/cache/c29323c0813ab787cg0145bf/`），但截图 / 导出产物 `images/` 为空，未保留成品；`cache/`、`output/` 已按 `.gitignore` 忽略，不纳入版本库。
- **`export.py` / `webpage.py` / `__main__.py`** 在 2024-03-30 被触碰过（与爬取运行同日）；相对 2024-03-10 快照的具体行级改动未逐行记录（本地并非 git 仓库、且精确上游提交未钉死），如后续需要精确 diff 可对照原版 v0.1.0 对应提交。
- 其余源码基本等同于上游 v0.1.0 快照；与上游当前 `main` 的大量文件差异属于**上游自身的后续演进**，**并非本仓库的修改**。

> 版权与许可：本复刻遵守原项目的 **MIT License**。原作者的著作权归 `drunkdream` 所有；如原项目许可或署名要求有更新，请以原仓库为准。
