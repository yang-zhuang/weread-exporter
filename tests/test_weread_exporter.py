# -*- coding: utf-8 -*-
"""weread-exporter 核心逻辑回归测试（不依赖网络、不启动浏览器）。

运行方式（二选一）：
    python tests/test_weread_exporter.py
    python -m pytest tests/ -v

设计要点
--------
1. 全程 fake：用 FakePage 顶替真实浏览器，monkeypatch utils.fetch 顶替图片下载，
   因此不需要网络、不需要 Chrome、秒级完成。
2. 乱序测试用可控的 FakeRandom 顶替 random 模块，抓取顺序完全确定，
   不依赖 random.seed 的运气（否则测试会时灵时不灵）。
3. 每个用例都在独立临时目录里跑，互不污染。
"""

import asyncio
import json
import logging
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from weread_exporter import utils  # noqa: E402
from weread_exporter.export import (  # noqa: E402
    WeReadExporter,
    is_paywall_text,
    human_detail,
)

PKG = os.path.join(ROOT, "weread_exporter")


def read_text(path):
    with open(path, encoding="utf-8") as fp:
        return fp.read()


class FakeRandom(object):
    """顶替 random 模块：shuffle 按预设排列、uniform 恒返回 0（免 sleep）。"""

    def __init__(self, orders):
        self._orders = list(orders)
        self._i = 0

    def shuffle(self, lst):
        if self._i < len(self._orders):
            wanted = self._orders[self._i]
            self._i += 1
            lst[:] = list(wanted)
        # 预设用完后保持原序，方便断言

    def uniform(self, a, b):
        return 0.0


class FakePage(object):
    """顶替 WeReadWebPage：记录抓取顺序，按 id 返回正文或付费墙文本。"""

    def __init__(self, paywall_ids=()):
        self.calls = []
        self.paywall_ids = set(paywall_ids)

    async def goto_chapter(self, chapter_id, timeout=60):
        self.calls.append(chapter_id)
        return True

    async def get_markdown(self):
        cid = self.calls[-1]
        if cid in self.paywall_ids:
            # 短且含特征词 → 命中 is_paywall_text
            return "试读结束"
        return "这是一段正常章节正文。" * 40  # 远超 300 字，不会被判付费墙


def make_exporter(tmp, chapters, paywall_ids=(), max_free=None):
    """搭好一个可直接跑 export_markdown 的 exporter（meta/cover 预置好）。"""
    os.makedirs(os.path.join(tmp, "chapters"), exist_ok=True)
    os.makedirs(os.path.join(tmp, "images"), exist_ok=True)
    meta = {
        "title": "测试书",
        "author": "测试作者",
        "cover": "http://example.com/cover.jpg",
        "chapters": chapters,
    }
    if max_free is not None:
        meta["maxFreeChapter"] = max_free
    with open(os.path.join(tmp, "meta.json"), "w", encoding="utf-8") as fp:
        json.dump(meta, fp, ensure_ascii=False)
    # 预置封面，避免 export_markdown 去触发 save_cover_image（那要联网）
    with open(os.path.join(tmp, "cover.jpg"), "wb") as fp:
        fp.write(b"\xff\xd8\xff\xd9")
    return WeReadExporter(FakePage(paywall_ids), tmp)


def chapter_ids(n):
    return [{"id": "c%d" % i, "title": "第%d章" % i, "level": 1, "anchors": []}
            for i in range(n)]


class TestWrHash(unittest.TestCase):
    """wr_hash 是逆向自微信读书混淆 JS 的，改坏了整个工具就废了。"""

    def test_known_values(self):
        self.assertEqual(utils.wr_hash("42557145"), "f343248072895ed9f34f408")
        self.assertEqual(utils.wr_hash("14"), "aab325601eaab3238922e53")

    def test_deterministic(self):
        # wr_hash 只接受数字字符串（内部 int(s[i:i+9])），别喂字母
        self.assertEqual(utils.wr_hash("42557145"), utils.wr_hash("42557145"))
        self.assertNotEqual(utils.wr_hash("42557145"), utils.wr_hash("14"))


class TestPaywallDetection(unittest.TestCase):
    def test_empty_is_paywall(self):
        self.assertTrue(is_paywall_text(""))
        self.assertTrue(is_paywall_text(None))

    def test_long_text_not_paywall(self):
        self.assertFalse(is_paywall_text("正文" * 200))

    def test_short_with_marker_is_paywall(self):
        self.assertTrue(is_paywall_text("试读结束"))
        self.assertTrue(is_paywall_text("开通会员后可继续阅读"))

    def test_short_without_marker_not_paywall(self):
        # 短但没有付费特征词（比如只有一句扉页文字）——不该误杀
        self.assertFalse(is_paywall_text("第一回"))


class TestImageLocalization(unittest.TestCase):
    """远程图片 URL → 本地 images/<md5>.jpg，且不再产生 .bak。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.orig_fetch = utils.fetch

        async def fake_fetch(url):
            return b"FAKEJPEGDATA"

        utils.fetch = fake_fetch

    def tearDown(self):
        utils.fetch = self.orig_fetch
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_remote_url_replaced_with_local_path(self):
        ch_dir = os.path.join(self.tmp, "chapters")
        os.makedirs(ch_dir)
        os.makedirs(os.path.join(self.tmp, "images"))
        # 章节文件名规则是 {index+1}-{chapter_id}.md，这里 id="c0" → 1-c0.md
        url = "https://res.weread.qq.com/wrepub/epub_12345_2"
        with open(os.path.join(ch_dir, "1-c0.md"), "wb") as fp:
            fp.write(("![](%s)\n" % url).encode())

        meta = {"chapters": chapter_ids(1)}
        with open(os.path.join(self.tmp, "meta.json"), "w", encoding="utf-8") as fp:
            json.dump(meta, fp)

        ex = WeReadExporter(FakePage(), self.tmp)
        asyncio.run(ex.pre_process_markdown())

        with open(os.path.join(ch_dir, "1-c0.md"), encoding="utf-8") as fp:
            content = fp.read()
        expected_name = utils.md5(url) + ".jpg"
        self.assertIn("images/" + expected_name, content)
        self.assertNotIn("res.weread.qq.com", content)
        self.assertTrue(
            os.path.isfile(os.path.join(self.tmp, "images", expected_name)),
            "图片应下载到 images/ 目录",
        )

    def test_no_bak_file_generated(self):
        """旧版会留一份 .bak（含远程 URL），误导人以为没替换。"""
        ch_dir = os.path.join(self.tmp, "chapters")
        os.makedirs(ch_dir)
        os.makedirs(os.path.join(self.tmp, "images"))
        url = "https://res.weread.qq.com/wrepub/epub_999_1"
        with open(os.path.join(ch_dir, "1-c0.md"), "wb") as fp:
            fp.write(("![](%s)\n" % url).encode())
        with open(os.path.join(self.tmp, "meta.json"), "w", encoding="utf-8") as fp:
            json.dump({"chapters": chapter_ids(1)}, fp)

        ex = WeReadExporter(FakePage(), self.tmp)
        asyncio.run(ex.pre_process_markdown())

        # 先确认替换真的发生了（否则下面"没有 .bak"会是假通过）
        with open(os.path.join(ch_dir, "1-c0.md"), encoding="utf-8") as fp:
            self.assertIn("images/%s.jpg" % utils.md5(url), fp.read())
        self.assertFalse(
            os.path.isfile(os.path.join(ch_dir, "1-c0.md.bak")),
            "不应再生成 .bak 冗余快照",
        )


class TestChapterOrderStrategy(unittest.TestCase):
    """免费区优先 + 付费墙跳过 + 撞墙后往回跳。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.orig_random = None

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, chapters, paywall_ids, max_free, shuffle, orders, max_chapters=0):
        import weread_exporter.export as export_mod

        orig_random = export_mod.random
        export_mod.random = FakeRandom(orders)
        try:
            ex = make_exporter(self.tmp, chapters, paywall_ids, max_free)
            asyncio.run(
                ex.export_markdown(
                    timeout=1, interval=0, jitter=0,
                    shuffle=shuffle, max_chapters=max_chapters,
                )
            )
            return list(ex._page.calls)  # 元素是 chapter id 字符串
        finally:
            export_mod.random = orig_random

    def test_limited_mode_takes_free_zone_head(self):
        """限量模式：只抓免费区最靠前的 N 章，且不打乱。"""
        chapters = chapter_ids(6)
        calls = self._run(
            chapters, paywall_ids=(), max_free=3,
            shuffle=True, orders=[[5, 4, 3, 2, 1, 0]],  # 即使打乱也要被免费区覆盖
            max_chapters=2,
        )
        self.assertEqual(calls, ["c0", "c1"])

    def test_shuffle_puts_free_zone_first(self):
        """乱序模式：免费区随机序在前，付费区垫底。"""
        chapters = chapter_ids(6)
        # 预设 shuffle 结果：打乱后是 [5,3,4,2,0,1]，
        # 免费区(0,1,2)应被提到前面（保持相对序 2,0,1），付费区(3,4,5)垫底(5,3,4)
        calls = self._run(
            chapters, paywall_ids=("c3", "c4", "c5"), max_free=3,
            shuffle=True, orders=[[5, 3, 4, 2, 0, 1]],
        )
        self.assertEqual(calls[:3], ["c2", "c0", "c1"], "免费区 3 章应排在最前")
        self.assertEqual(set(calls[3:]), {"c3", "c4", "c5"}, "付费区垫底")

    def test_paywall_chapters_skipped(self):
        """付费墙章节不落盘。"""
        chapters = chapter_ids(4)
        self._run(
            chapters, paywall_ids=("c1", "c3"), max_free=None,
            shuffle=False, orders=[],
        )
        ch_dir = os.path.join(self.tmp, "chapters")
        produced = sorted(os.listdir(ch_dir))
        self.assertEqual(produced, ["1-c0.md", "3-c2.md"], "付费章不应产出文件")

    def test_paywall_rollback_goes_backwards(self):
        """撞到付费墙后，剩余顺序改为「比它更靠前的未抓章节优先」。

        这是关键回归点：order[0]=c2 是付费墙，撞墙时队列里还有 c0/c1（更靠前）
        和 c3/c4（更靠后）。没有回退的话接下来会抓 c3；有回退则抓 c0/c1。
        """
        chapters = chapter_ids(5)
        # 第一次 shuffle → 抓取顺序以 c2 打头；第二次 shuffle → before 的随机序
        calls = self._run(
            chapters, paywall_ids=("c2", "c4"), max_free=None,
            shuffle=True, orders=[[2, 3, 0, 1, 4], [1, 0]],
        )
        self.assertEqual(calls[0], "c2", "首个抓的是付费墙章 c2")
        self.assertEqual(calls[1:3], ["c1", "c0"], "撞墙后应先回头抓更靠前的 c1/c0")
        self.assertEqual(calls[3], "c3")
        self.assertEqual(calls[4], "c4")

    def test_sequential_mode_keeps_order(self):
        chapters = chapter_ids(3)
        calls = self._run(
            chapters, paywall_ids=(), max_free=None, shuffle=False, orders=[]
        )
        self.assertEqual(calls, ["c0", "c1", "c2"])


class TestMetadataChineseReadable(unittest.TestCase):
    """meta.json 必须是中文可读，不能是 \\uXXXX 转义。"""

    def test_meta_json_not_escaped(self):
        src = read_text(os.path.join(PKG, "export.py"))
        self.assertIn("ensure_ascii=False", src,
                      "写 meta.json 时必须 ensure_ascii=False 否则中文变成 \\uXXXX")

    def test_human_detail_fields(self):
        detail = human_detail({
            "title": "红楼梦",
            "author": "曹雪芹",
            "publisher": "人民文学出版社",
            "isbn": "9787020002207",
            "finished": True,
        })
        self.assertEqual(detail["书名"], "红楼梦")
        self.assertEqual(detail["作者"], "曹雪芹")
        self.assertEqual(detail["出版社"], "人民文学出版社")
        self.assertEqual(detail["ISBN"], "9787020002207")
        self.assertEqual(detail["是否完结"], "是")


class TestProjectStructure(unittest.TestCase):
    """拆分后的结构约束：CLI 只管参数，业务逻辑在 crawler，注入 JS 在 injections。"""

    def setUp(self):
        self.main = read_text(os.path.join(PKG, "__main__.py"))
        self.crawler = read_text(os.path.join(PKG, "crawler.py"))
        self.webpage = read_text(os.path.join(PKG, "webpage.py"))

    def test_crawler_module_exists(self):
        self.assertTrue(os.path.isfile(os.path.join(PKG, "crawler.py")))
        self.assertTrue(os.path.isfile(os.path.join(PKG, "injections.py")))

    def test_business_logic_in_crawler(self):
        self.assertIn("async def export_book", self.crawler)
        self.assertIn("async def crawl_all", self.crawler)
        self.assertNotIn("async def export_book", self.main, "业务逻辑应已搬走")

    def test_main_imports_crawler(self):
        self.assertIn("from . import crawler", self.main)

    def test_injections_used_by_webpage(self):
        self.assertIn("injections.", self.webpage)
        for name in ("DETECT_HEADLESS_SCRIPT", "DETECT_CAPTCHA_SCRIPT",
                     "STEALTH_PATCH_SCRIPT"):
            self.assertNotIn("%s = " % name, self.webpage,
                             "%s 应已挪到 injections.py" % name)

    def test_max_file_size_reasonable(self):
        for name in ("__main__.py", "crawler.py", "injections.py"):
            path = os.path.join(PKG, name)
            lines = sum(1 for _ in read_text(path).splitlines())
            self.assertLess(lines, 500, "%s 不应超过 500 行（当前 %d）" % (name, lines))


class TestConsoleLogThrottle(unittest.TestCase):
    """console 日志去重 + 上限轮转。

    微信读书把正文画在 canvas 上，浏览器 console 会被 fillRect/fillStyle 疯狂
    刷屏（实测 14.8 万行里唯一内容只有 333 行），无节流时单个 .log 能涨到十几 MB。
    """

    class _Msg(object):
        """pyppeteer ConsoleMessage 的最小替身（只用到 .text）。"""

        def __init__(self, text):
            self.text = text

    def setUp(self):
        from weread_exporter.webpage import WeReadWebPage

        self._cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)  # handle_log 写 "./<book_id>.log"，切到临时目录再跑
        logging.disable(logging.CRITICAL)  # 静音 handle_log 里的 logging.info
        self.page = WeReadWebPage(
            "testbook",
            no_login=True,
            webcache_path=os.path.join(self.tmp, "cache"),
        )
        self.log_path = os.path.join(self.tmp, "testbook.log")

    def tearDown(self):
        logging.disable(logging.NOTSET)
        os.chdir(self._cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _feed(self, *texts):
        for t in texts:
            self.page.handle_log(self._Msg(t))

    def test_consecutive_repeats_collapsed(self):
        # 重复计数在下一条不同日志到来时补写（真实 canvas 刷屏是交替的，
        # fillRect / fillStyle 来回切，换行很频繁，计数不会积压）
        self._feed("same line", "same line", "same line", "next line")
        content = read_text(self.log_path)
        self.assertEqual(content.count("] same line\n"), 1,
                         "连续重复行应只落一条：%r" % content)
        self.assertIn("上一行重复 2 次", content)
        self.assertIn("next line", content)

    def test_trailing_repeats_not_duplicated(self):
        # 以重复行结尾时（进程被杀/抓取结束），也不应把刷屏内容全部写盘
        self._feed("only line", "only line", "only line")
        content = read_text(self.log_path)
        self.assertEqual(content.count("only line"), 1,
                         "结尾的重复不应逐条落盘：%r" % content)

    def test_non_consecutive_repeats_kept(self):
        self._feed("A", "B", "A")
        content = read_text(self.log_path)
        code_lines = [ln for ln in content.splitlines() if "^^^" not in ln]
        self.assertEqual(len(code_lines), 3, "非连续重复不应折叠：%r" % content)

    def test_rotation_on_size_limit(self):
        self.page.MAX_CONSOLE_LOG_BYTES = 200  # 调小上限，避免测试真写 4MB
        self._feed("x" * 150)
        self._feed("y" * 150)  # 累计超限，写入前应触发轮转
        self._feed("z" * 10)

        rotated = self.log_path + ".1"
        self.assertTrue(os.path.isfile(rotated), "超限应轮转出 .log.1")
        rotated_text = read_text(rotated)
        self.assertIn("x" * 150, rotated_text, ".log.1 应保留超限前的内容")
        self.assertIn("字节上限", rotated_text, "归档文件末尾应留一句轮转说明")
        current = read_text(self.log_path)
        self.assertIn("z" * 10, current, "轮转后新内容应写入新文件")
        self.assertNotIn("x" * 150, current, "新文件应是干净的，不含归档内容")

    def test_source_has_throttle(self):
        src = read_text(os.path.join(PKG, "webpage.py"))
        self.assertIn("MAX_CONSOLE_LOG_BYTES", src)
        self.assertIn("os.replace(log_path, log_path", src, "轮转应使用 os.replace")


class TestCliArguments(unittest.TestCase):
    def setUp(self):
        self.main = read_text(os.path.join(PKG, "__main__.py"))
        self.crawler = read_text(os.path.join(PKG, "crawler.py"))

    def test_required_flags(self):
        for flag in ("--cdp-endpoint", "--verify-timeout", "--jitter",
                     "--no-shuffle", "--cooldown", "--no-login",
                     "--list-categories", "--categories", "--per-category",
                     "--chapters-per-book"):
            self.assertIn('"%s"' % flag, self.main, "CLI 缺少 %s" % flag)

    def test_no_login_propagates(self):
        self.assertIn("no_login=args.no_login", self.crawler)

    def test_crawl_defaults_to_one_chapter(self):
        self.assertIn("max_chapters = 1", self.crawler,
                      "遍历模式必须默认每书只抓 1 章（风控安全默认）")

    def test_cooldown_on_risk_control(self):
        self.assertIn("asyncio.sleep(args.cooldown)", self.crawler)
        self.assertIn("建议当天停手", self.crawler)


if __name__ == "__main__":
    unittest.main(verbosity=2)
