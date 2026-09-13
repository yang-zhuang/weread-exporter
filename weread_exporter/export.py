from weread_exporter.webpage import WeReadWebPage


import asyncio
import json
import logging
import os
import random
import sys
import time
from typing import Dict, List, Optional, Any

import bs4
import markdown

from ebooklib import epub

from . import utils

if sys.version_info >= (3, 8):
    from typing import TYPE_CHECKING
else:
    from typing_extensions import TYPE_CHECKING

if TYPE_CHECKING:
    from .webpage import WeReadWebPage

current_path = os.path.dirname(os.path.abspath(__file__))

# 免登录/试读模式下，付费章页面渲染的是购买提示而不是正文。
# 特征词 + 短内容双条件判定，避免把购买提示当正文落盘（免费章正文通常很长）。
_PAYWALL_MARKERS = (
    "购买本章",
    "解锁本章",
    "需要购买",
    "本章为付费",
    "付费内容",
    "购买后阅读",
    "本章需付费",
    "会员专享",
    "试读结束",
    "开通会员",
)


def is_paywall_text(content: str) -> bool:
    """启发式判断：内容为空或极短且含付费特征词 → 付费墙，应跳过该章。"""
    text = (content or "").strip()
    if not text:
        return True  # 空内容视作拿不到正文
    if len(text) >= 300:
        return False  # 正常章节正文不可能这么短
    return any(m in text for m in _PAYWALL_MARKERS)


def human_detail(meta: Dict[str, Any]) -> Dict[str, Any]:
    """把 get_book_info 的完整元数据转成中文人读版（写进每本书的 详情.json）。

    meta 即 cache/<book_id>/meta.json 的内容（含 title/author/chapters 及
    category/publisher/isbn/评分等详情页字段）。chapters 太大，人读版不包含。
    """
    rating = meta.get("ratingDetail") or {}
    new_rating = meta.get("newRatingDetail") or {}
    cats = meta.get("categories") or []
    cat_titles = "、".join(c.get("title") or "" for c in cats) or meta.get("category") or ""
    ranklist = meta.get("ranklist") or {}
    cent_price = meta.get("centPrice")
    return {
        "书名": meta.get("title"),
        "作者": meta.get("author"),
        "分类": cat_titles,
        "标签": meta.get("tags"),
        "出版社": meta.get("publisher"),
        "出版时间": meta.get("publishTime"),
        "ISBN": meta.get("isbn"),
        "定价(元)": meta.get("publishPrice")
        or (cent_price / 100 if isinstance(cent_price, (int, float)) else None),
        "总字数": meta.get("totalWords"),
        "是否完结": "是" if meta.get("finished") else "否",
        "免费章节数": meta.get("maxFreeChapter"),
        "章节总数": meta.get("chapterSize") or meta.get("lastChapterIdx"),
        "推荐值": (
            meta.get("newRating") / 10
            if isinstance(meta.get("newRating"), (int, float))
            else meta.get("newRating")
        ),
        "评分人数": meta.get("newRatingCount") or meta.get("ratingCount"),
        "评分标签": new_rating.get("title"),
        "评分分布": {
            "好评": new_rating.get("good"),
            "中评": new_rating.get("fair"),
            "差评": new_rating.get("poor"),
            "深V用户数": new_rating.get("deepV"),
            "近期评分": new_rating.get("recent"),
            "五星/四星/三星/二星/一星": [
                rating.get(k) for k in ("five", "four", "three", "two", "one")
            ],
        },
        "所在榜单": ranklist.get("categoryName"),
        "上榜序号": ranklist.get("seq"),
        "书籍ID": meta.get("bookId"),
        "阅读ID": meta.get("encodeId"),
        "格式": meta.get("format"),
        "语言": meta.get("language"),
        "更新时间(时间戳)": meta.get("updateTime"),
        "简介": meta.get("intro"),
    }


class WeReadExporter(object):
    def __init__(self, page: WeReadWebPage, save_dir: str) -> None:
        self._page: WeReadWebPage = page
        self._save_dir: str = save_dir
        if not os.path.isdir(save_dir):
            os.makedirs(save_dir)
        self._meta_path: str = os.path.join(self._save_dir, "meta.json")
        self._chapter_dir: str = os.path.join(self._save_dir, "chapters")
        self._image_dir: str = os.path.join(self._save_dir, "images")
        if not os.path.isdir(self._image_dir):
            os.mkdir(self._image_dir)
        self._cover_image_path: str = os.path.join(self._save_dir, "cover.jpg")
        self._meta_data: Dict[str, Any] = {}
        self._current_chapter: int = 0

    async def get_book_title(self) -> str:
        meta_data = await self._load_meta_data()
        return meta_data["title"]

    def _make_chapter_path(self, index: int, chapter_id: str) -> str:
        return os.path.join(self._chapter_dir, "%d-%s.md" % (index + 1, chapter_id))

    async def _load_meta_data(self) -> Dict[str, Any]:
        if self._meta_data:
            return self._meta_data

        if not os.path.isfile(self._meta_path):
            self._meta_data = await self._page.get_book_info()
            with open(self._meta_path, "w", encoding="utf-8") as fp:
                # ensure_ascii=False：中文直接写，人读 meta.json 不再是 \uXXXX 转义
                fp.write(json.dumps(self._meta_data, ensure_ascii=False))
        else:
            with open(self._meta_path) as fp:
                text = fp.read()
                if text:
                    self._meta_data = json.loads(text)
        return self._meta_data

    async def merge_markdown(self, save_path: str) -> None:
        meta_data = await self._load_meta_data()
        with open(save_path, "w") as fp:
            for index, chapter in enumerate(meta_data["chapters"]):
                file_path = self._make_chapter_path(index, chapter["id"])
                if not os.path.isfile(file_path):
                    raise RuntimeError("File %s not exist" % file_path)
                with open(file_path) as fd:
                    fp.write(fd.read() + "\n")

    async def pre_process_markdown(self) -> None:
        meta_data: Dict[str, Any] = await self._load_meta_data()
        for index, chapter in enumerate(meta_data["chapters"]):
            chapter_path = self._make_chapter_path(index, chapter["id"])
            if not os.path.isfile(chapter_path):
                logging.warning(
                    "[%s] File %s not exist" % (self.__class__.__name__, chapter_path)
                )
                continue
            with open(chapter_path, "rb") as fp:
                text = fp.read().decode()

            output = ""
            code_mode = False
            blank_line = False
            for line in text.split("\n"):
                if line == "```":
                    if not code_mode:
                        output += "\n%s\n" % line
                    else:
                        output += "%s\n" % line
                    code_mode = not code_mode
                elif code_mode:
                    output += line + "\n"
                elif line == "":
                    blank_line = True
                elif blank_line:
                    output += "\n\n%s" % line
                    blank_line = False
                else:
                    output += line
            output += "\n"
            pos = 0
            while pos >= 0:
                pos = output.find("](https://", pos)
                if pos < 0:
                    break
                pos1: int = output.find(")", pos)
                url = output[pos + 2 : pos1]
                logging.info("[%s] Replace image %s" % (self.__class__.__name__, url))
                try:
                    data = await utils.fetch(url)
                except:
                    logging.exception(
                        "[%s] Fetch image data of %s failed"
                        % (self.__class__.__name__, url)
                    )
                    pos += 10
                else:
                    image_name = utils.md5(url) + ".jpg"
                    with open(os.path.join(self._image_dir, image_name), "wb") as fp:
                        fp.write(data)
                    output = output[: pos + 2] + "images/" + image_name + output[pos1:]
            # 直接写替换后的最终内容，不再保留 .bak 冗余快照。
            # 旧版 .bak 保留「替换前」的远程 URL，与最终 .md 并存会让人误以为图片未本地化。
            with open(chapter_path, "wb") as fp:
                fp.write(output.encode())

    async def markdown_to_txt(self, save_path: str) -> None:
        meta_data = await self._load_meta_data()
        for index, chapter in enumerate(meta_data["chapters"]):
            chapter_path = self._make_chapter_path(index, chapter["id"])
            raw_html = self._markdown_to_html(chapter_path, wrap=False)
            soup = bs4.BeautifulSoup(raw_html, features="html.parser")
            with open(save_path, "a+") as fp:
                fp.write(soup.text + "\n\n")

    def _markdown_to_html(self, path_or_text: str, wrap: bool = True) -> str:
        if os.path.isfile(path_or_text):
            with open(path_or_text, "rb") as fp:
                markdown_text = fp.read().decode()
        else:
            markdown_text = path_or_text
        html = markdown.markdown(
            markdown_text,
            extensions=[
                "markdown.extensions.fenced_code",
                "markdown.extensions.attr_list",
            ],
        )
        html += '<div class="page-break"></div>'
        if wrap:
            html = (
                '<html><head><link rel="stylesheet" href="style.css"></head><body>%s</body></html>'
                % html
            )
        return html

    async def markdown_to_pdf(
        self,
        save_path: str,
        extra_css: Optional[str] = None,
        image_format: str = "jpg",
        dump_html: bool = False,
    ) -> None:
        # weasyprint 只在 PDF 转换时需要，延迟导入避免 -o md/epub 也拉重依赖
        from weasyprint import HTML, CSS

        meta_data = await self._load_meta_data()
        raw_html: str = '<img src="cover.jpg" style="width: 100%;">\n'
        for index, chapter in enumerate(meta_data["chapters"]):
            chapter_path: str = self._make_chapter_path(index, chapter["id"])
            raw_html += self._markdown_to_html(chapter_path, wrap=False)
        raw_html = raw_html.replace(
            "<pre><code>", "<pre><code>\n"
        )  # Fix unexpected indent
        if image_format == "png":
            soup = bs4.BeautifulSoup(raw_html, features="html.parser")
            for img in soup.find_all("img"):
                src: str = os.path.join(self._save_dir, img.attrs["src"])
                if not src.endswith(".png"):
                    png_path: str = src[:-3] + "png"
                    utils.save_to_png(src, png_path)
                    img.attrs["src"] = img.attrs["src"][:-3] + "png"

            raw_html = soup.prettify()

        if dump_html:
            html_path = os.path.join(self._save_dir, "output.html")
            with open(html_path, "w") as fp:
                fp.write(raw_html)  # pyright: ignore[reportUnusedCallResult]
        html = HTML(string=raw_html, base_url=self._save_dir)
        css: List[CSS] = []
        css_path = os.path.join(current_path, "style.css")
        with open(css_path) as fp:
            raw_css = fp.read()
            if extra_css:
                raw_css += "\n" + extra_css
            css.append(CSS(string=raw_css))

        # Generate PDF
        html.write_pdf(
            save_path, stylesheets=css
        )  # pyright: ignore[reportUnknownMemberType, reportUnusedCallResult]

    async def markdown_to_epub(
        self, save_path: str, extra_css: Optional[str] = None
    ) -> None:
        meta_data = await self._load_meta_data()
        book = epub.EpubBook()
        book.set_identifier("id123456")
        book.set_title(meta_data["title"])
        book.set_language("zh-cn")
        book.add_author(meta_data["author"])
        # add cover image
        with open(self._cover_image_path, "rb") as fp:
            image_data = fp.read()
            book.set_cover("cover.jpg", image_data)
        # define CSS style
        css_path = os.path.join(current_path, "epub.css")
        with open(css_path) as fp:
            style = fp.read()
        if extra_css:
            style += "\n" + extra_css
        default_css = epub.EpubItem(
            uid="style_default",
            file_name="style/default.css",
            media_type="text/css",
            content=style,
        )

        # add CSS file
        book.add_item(default_css)
        chapters = []
        toc = []
        section: Optional[tuple] = None
        for index, chapter in enumerate(meta_data["chapters"]):
            chapter_path = self._make_chapter_path(index, chapter["id"])
            xhtml_name = "chap_%.4d.xhtml" % (index + 1)
            chap = epub.EpubHtml(
                title=chapter["title"], file_name=xhtml_name, lang="hr"
            )
            html = self._markdown_to_html(chapter_path)
            chap.content = html.replace("code>", "epub-code>")
            chap.add_item(default_css)
            # add chapter
            book.add_item(chap)
            chapters.append(chap)

            if section:
                if chapter["level"] > 1:
                    section[1].append(chap)
                else:
                    toc.append(section)
                    section = None

            if not section:
                if chapter["anchors"]:
                    section = (epub.Section(chapter["title"], xhtml_name), [])
                    for i, it in enumerate(chapter["anchors"]):
                        # add anchor point
                        chap.content = chap.content.replace(
                            ">%s<" % it["title"].replace(" ", ""),
                            ' id="t%d">%s<' % ((i + 1), it["title"]),
                        )
                        section[1].append(
                            epub.Link(
                                "%s#t%d" % (xhtml_name, (i + 1)),
                                it["title"],
                                str(chapter["id"]),
                            )
                        )
                elif chapter["level"] > 1:
                    section = (toc.pop(-1), [])
                    section[1].append(
                        epub.Link(xhtml_name, chapter["title"], str(chapter["id"]))
                    )
                else:
                    toc.append(
                        epub.Link(xhtml_name, chapter["title"], str(chapter["id"]))
                    )

        for it in os.listdir(self._image_dir):
            with open(os.path.join(self._image_dir, it), "rb") as fp:
                content = fp.read()
                image = epub.EpubItem(
                    file_name="images/" + it,
                    media_type="image/jpeg",
                    content=content,
                )
                book.add_item(image)

        book.toc = toc
        # add default NCX and Nav file
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        book.spine = ["nav", *chapters]
        # write to the file
        epub.write_epub(save_path, book, {})

    async def epub_to_mobi(self, epub_path: str, save_path: str) -> None:
        kindlegen_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "bin", sys.platform, "kindlegen"
        )
        if not os.path.isfile(kindlegen_path):
            raise RuntimeError("File %s not exist" % kindlegen_path)
        if sys.platform != "win32":
            os.chmod(kindlegen_path, 0o755)
        cmdline = [
            kindlegen_path,
            os.path.abspath(epub_path),
            "-o",
            os.path.basename(save_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmdline, cwd=os.path.dirname(save_path)
        )
        await proc.wait()

    async def save_cover_image(self) -> None:
        meta_data = await self._load_meta_data()
        cover_url = meta_data["cover"].replace("/s_", "/t9_")
        data = await utils.fetch(cover_url)
        with open(self._cover_image_path, "wb") as fp:
            fp.write(data)

    async def export_markdown(
        self,
        timeout: int = 60,
        interval: int = 30,
        jitter: int = 5,
        shuffle: bool = True,
        max_chapters: int = 0,
    ) -> None:
        """逐章导出 markdown。

        interval 是章节之间的基准间隔，jitter 是叠加在上面的正负随机抖动。
        固定 30 秒一章的节拍本身就是一个机器特征，抖动后平均值不变但去掉了周期性。

        shuffle 为 True 时打乱章节的抓取顺序：真人极少严格 1→N 顺读，线性抓取
        本身就是一个自动化信号。每章写入仍用它在书中的原始下标命名，因此最终
        文件与导出的 epub/pdf 顺序完全不受影响，只是向服务器的请求顺序不再线性。

        max_chapters > 0 时只抓书的前 N 章（测试/风控模式），此时强制不 shuffle：
        书的开头通常是免费试读章，按序取才能保证抓到的不是付费墙后面的章。
        """
        if not os.path.isdir(self._chapter_dir):
            os.makedirs(self._chapter_dir)
        meta_data = await self._load_meta_data()
        if not os.path.isfile(self._cover_image_path):
            await self.save_cover_image()

        chapters = meta_data["chapters"]
        # maxFreeChapter 元数据：书的免费章集中在开头（前 mf 个章节位置），
        # 边界可能 ±1，由运行时的付费墙检测兜底。免费区的章优先抓。
        free_limit = None
        mf = meta_data.get("maxFreeChapter")
        if isinstance(mf, int) and mf > 0:
            free_limit = min(mf, len(chapters))

        order = list(range(len(chapters)))
        if max_chapters and max_chapters > 0:
            if free_limit:
                free_zone = [i for i in order if i < free_limit]
                order = free_zone[:max_chapters] or order[:max_chapters]
            else:
                order = order[:max_chapters]
        elif shuffle:
            random.shuffle(order)
            if free_limit:
                # 免费区优先：免费区的随机序放前面，付费区随机序垫底
                free_part = [i for i in order if i < free_limit]
                paid_part = [i for i in order if i >= free_limit]
                order = free_part + paid_part
            logging.info(
                "[%s] 已打乱章节抓取顺序（共 %d 章），写入仍按原序"
                % (self.__class__.__name__, len(order))
            )
        if len(order) < len(chapters):
            logging.info(
                "[%s] 限量模式：只抓 %d 章（共 %d 章，免费区优先）"
                % (self.__class__.__name__, len(order), len(chapters))
            )

        # 队列化循环：撞到付费墙后把剩余顺序重排——比首个付费章更靠前的
        # 未抓章节优先（免费章集中在书的前部，往回找比往后找命中率高）
        queue = list(order)
        paywall_seen = False
        while queue:
            index = queue.pop(0)
            chapter = chapters[index]
            logging.info(
                "[%s] Check chapter %s/%s"
                % (self.__class__.__name__, chapter["id"], chapter["title"])
            )

            file_path = self._make_chapter_path(index, chapter["id"])
            if os.path.isfile(file_path) and os.path.getsize(file_path) > 3:
                continue
            logging.info(
                "[%s] File %s not exist" % (self.__class__.__name__, file_path)
            )

            time0 = 0
            for _ in range(3):
                time0 = time.time()
                try:
                    # 不用 asyncio.wait_for 包裹：goto_chapter 内部每步都有超时
                    # （goto / 撞码等待 / 按钮等待），wait_for 超时会在 CDP 请求
                    # 拦截处理中途取消任务，被拦截的请求永远挂起，页面后续
                    # 加载全部卡死（hook 脚本也加载不了）
                    await self._page.goto_chapter(
                        chapter["id"],
                        timeout=timeout,
                    )
                except utils.RiskControlError:
                    # 撞验证码重试没有意义，只会再等一轮超时，直接往上抛
                    raise
                except asyncio.TimeoutError:
                    logging.warning(
                        "[%s] Load chapter %s timeout %ds"
                        % (
                            self.__class__.__name__,
                            chapter["title"],
                            time.time() - time0,
                        )
                    )
                    raise utils.LoadChapterFailedError()
                except KeyboardInterrupt as ex:
                    raise ex
                except:
                    logging.exception(
                        "[%s] Go to chapter %s failed"
                        % (self.__class__.__name__, chapter["title"])
                    )
                else:
                    break
            else:
                raise utils.LoadChapterFailedError(
                    "Load chapter %s failed" % chapter["title"]
                )

            markdown_content = await self._page.get_markdown()
            if is_paywall_text(markdown_content):
                logging.warning(
                    "[%s] Chapter %s 疑似付费墙，跳过（免费章节上限之外）"
                    % (self.__class__.__name__, chapter["title"])
                )
                if not paywall_seen:
                    paywall_seen = True
                    # 回退：剩余顺序改为「比首个付费章更靠前的未抓章节优先，
                    # 随机」——免费章集中在书的前部，往回找比往后找命中率高；
                    # 前面的抓完再考虑后面的
                    before = [i for i in queue if i < index]
                    after = [i for i in queue if i > index]
                    random.shuffle(before)
                    queue = before + after
                    if before:
                        logging.info(
                            "[%s] 付费墙后回退：优先尝试更靠前的 %d 个未抓章节"
                            % (self.__class__.__name__, len(before))
                        )
                await asyncio.sleep(
                    max(0.0, interval + random.uniform(-jitter, jitter))
                )
                continue
            logging.info(
                "[%s] Export chapter %s to %s"
                % (self.__class__.__name__, chapter["title"], file_path)
            )
            with open(file_path, "wb") as fp:
                fp.write(markdown_content.encode("utf-8", errors="replace"))

            await asyncio.sleep(max(0.0, interval + random.uniform(-jitter, jitter)))
