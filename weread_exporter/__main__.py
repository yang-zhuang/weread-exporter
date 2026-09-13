import argparse
import asyncio
import logging
import os
import sys
from typing import Callable, Optional

from . import utils


def patch_windows() -> None:
    bin_path: str = os.path.join(
        os.path.abspath(os.path.dirname(__file__)), "bin", "win32"
    )
    os.environ["PATH"] += ";" + bin_path
    if hasattr(os, "add_dll_directory"):
        os.add_dll_directory(bin_path)  # pyright: ignore[reportUnusedCallResult]


def patch_macos() -> None:
    fallback_lib_path: str = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
    if not fallback_lib_path:
        os.environ["DYLD_FALLBACK_LIBRARY_PATH"] += "/opt/homebrew/lib"


def patch_generateRequestHash() -> None:
    from pyppeteer import network_manager

    orig_generateRequestHash: Callable[..., str] = network_manager.generateRequestHash

    def patched_generateRequestHash(request):
        request["headers"].pop("Origin", None)
        return orig_generateRequestHash(request)

    network_manager.generateRequestHash = patched_generateRequestHash


async def async_main() -> int:
    from . import crawler

    parser = argparse.ArgumentParser(
        prog="weread-exporter", description="WeRead book export cmdline tool"
    )
    parser.add_argument(
        "-b", "--book-id", help="book id；不传则全量遍历分类/榜单（详见 README）", default=None
    )  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "-o",
        "--output-format",
        help="output file format",
        action="append",
        choices=["md", "epub", "pdf", "mobi", "txt"],
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--load-timeout",
        help="load chapter page timeout",
        type=int,
        default=60,
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--load-interval",
        help="load chapter page interval time",
        type=int,
        default=30,
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--css-file",
        help="overide default css style",
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--headless", help="chrome headless", action="store_true", default=False
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--force-login", help="force login first", action="store_true", default=False
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--use-default-profile",
        help="use default profile",
        action="store_true",
        default=False,
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--mock-user-agent",
        help="use mock user-agent",
        action="store_true",
        default=False,
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--proxy-server",
        help="http proxy server, e.g. http://127.0.0.1:8888",
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--cdp-endpoint",
        help="接管一个已经启动的 Chrome，例如 http://127.0.0.1:9222",
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--verify-timeout",
        help="检测到验证码时，等待人工过码的最长时间(秒)",
        type=int,
        default=600,
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--jitter",
        help="章节间隔的随机抖动(秒)，实际间隔为 load-interval ± jitter",
        type=int,
        default=5,
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--no-shuffle",
        help="按原顺序抓取章节（默认打乱抓取顺序，写入仍按原序）",
        action="store_false",
        dest="shuffle",
        default=True,
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--cooldown",
        help="被风控拦截后的冷却时间(秒)，冷却期间不退出、防止立刻重跑，默认 600",
        type=int,
        default=600,
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--list-categories",
        help="打印微信读书分类树后退出（不抓书）",
        action="store_true",
        default=False,
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--categories",
        help="全量遍历时只处理指定分类/榜单，逗号分隔，支持中文名或代码，如 '文学,飙升·出版'",
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--per-category",
        help="全量遍历时每个分类/子分类最多取前 N 本（默认 2，0=不限制）",
        type=int,
        default=2,
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--chapters-per-book",
        help="每本书最多下载 N 章（0=全量；遍历模式默认 1 章，单本模式默认全量）",
        type=int,
        default=None,
    )
    parser.add_argument(  # pyright: ignore[reportUnusedCallResult]
        "--no-login",
        help="免登录模式：不读/不写 cookie、不登录，只下载免费章节（每本书 maxFreeChapter 之前）。"
        "实测正文接口不校验登录态，免费章节无登录即可读全文；账号层面零封号风险",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()
    args.output_format = args.output_format or ["epub"]  # pyright: ignore[reportAny]
    if "mobi" in args.output_format and "epub" not in args.output_format:
        args.output_format.append("epub")  # pyright: ignore[reportUnusedCallResult]

    if args.headless:  # pyright: ignore[reportAny]
        logging.warning(
            "--headless 会大幅提高被判定为自动化的概率。原项目自己在 "
            "webpage.py 里就写着「继续执行可能导致帐号被封禁」。"
            "建议改用 --cdp-endpoint 接管一个已登录的真实浏览器。"
        )
    if args.cdp_endpoint and (  # pyright: ignore[reportAny]
        args.headless  # pyright: ignore[reportAny]
        or args.mock_user_agent  # pyright: ignore[reportAny]
        or args.use_default_profile  # pyright: ignore[reportAny]
    ):
        logging.warning(
            "接管模式下 --headless / --mock-user-agent / --use-default-profile 不生效，已忽略"
        )
    if args.no_login and args.cdp_endpoint:  # pyright: ignore[reportAny]
        logging.warning(
            "--no-login 与 --cdp-endpoint 同时使用：接管模式本就复用浏览器的登录态，"
            "--no-login 仅让工具不读取它；如需完全免登录请去掉 --cdp-endpoint"
        )
    if args.no_login and args.force_login:  # pyright: ignore[reportAny]
        logging.warning("--no-login 模式下 --force-login 不生效，已忽略")

    extra_css: Optional[str] = None
    if args.css_file:  # pyright: ignore[reportAny]
        if not os.path.isfile(args.css_file):  # pyright: ignore[reportAny]
            raise RuntimeError(
                "CSS file %s not exist" % args.css_file
            )  # pyright: ignore[reportAny]
        with open(args.css_file) as fp:  # pyright: ignore[reportAny]
            extra_css = fp.read()

    if args.list_categories:  # pyright: ignore[reportAny]
        from . import categories

        tree = await categories.build_tree()
        print(categories.describe_tree(tree))
        return 0

    output_dir = "output"
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    if args.book_id is None:  # pyright: ignore[reportAny]
        # 全量遍历模式：榜单 + 全部分类/子分类
        return await crawler.crawl_all(args, output_dir, extra_css)

    if "_" in args.book_id:  # pyright: ignore[reportAny]
        # book list id
        book_list = [it["id"] for it in await utils.get_book_list(args.book_id)]
    else:
        book_list = [args.book_id]  # pyright: ignore[reportAny]

    for book_id in book_list:
        ok = await crawler.export_book(
            args,
            book_id,
            output_dir,
            extra_css,
            max_chapters=args.chapters_per_book or 0,  # pyright: ignore[reportAny]
        )
        if not ok:
            return -1
    return 0


def main() -> int:
    if sys.platform == "win32":
        patch_windows()
    elif sys.platform == "darwin":
        patch_macos()
    patch_generateRequestHash()
    utils.check_cairo_installed()
    logging.root.level = logging.INFO
    handler = logging.StreamHandler()
    fmt = "[%(asctime)s][%(levelname)s]%(message)s"
    formatter = logging.Formatter(fmt)
    handler.setFormatter(formatter)
    logging.root.addHandler(handler)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(async_main())
    except:
        import traceback

        traceback.print_exc()
        return -1


if __name__ == "__main__":
    sys.exit(main())
