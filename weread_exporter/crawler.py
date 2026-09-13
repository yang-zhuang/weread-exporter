"""书籍抓取/导出的业务逻辑：单本导出 + 全量分类遍历。

从 __main__.py 拆出，与 argparse CLI 定义解耦。CLI 只负责解析参数，
真正「导出单本」和「遍历分类」的两条业务链都在这里。
"""

import asyncio
import json
import logging
import os
import shutil
import sys
from typing import Optional

from . import categories, export, utils, webpage


async def export_book(
    args,
    book_id: str,
    output_dir: str,
    extra_css: Optional[str],
    subdir: Optional[str] = None,
    max_chapters: int = 0,
    max_launch_retries: int = 0,
) -> bool:
    """导出单本书，输出到 output[<分类路径>]/。

    subdir 为 output 下的分类相对路径（如 '文学/古典文学'）；None 表示平铺到 output。
    返回 False 表示应中止整个程序（风控拦截/用户退出），True 表示继续。
    """
    logging.info(
        "Exporting book %s%s" % (book_id, " [%s]" % subdir if subdir else "")
    )
    page = webpage.WeReadWebPage(
        book_id,
        cookie_path=os.path.join("cache", "cookie.txt"),
        webcache_path="cache",
        verify_timeout=args.verify_timeout,
        no_login=args.no_login,
    )
    if not await page.check_valid():
        logging.warning("Book %s status is invalid, stop exporting" % book_id)
        return True
    save_path = os.path.join("cache", book_id)
    exporter = export.WeReadExporter(page, save_path)
    launch_attempts = 0
    while True:
        try:
            await page.launch(
                headless=args.headless,
                force_login=args.force_login,
                use_default_profile=args.use_default_profile,
                mock_user_agent=args.mock_user_agent,
                proxy_server=args.proxy_server,
                cdp_endpoint=args.cdp_endpoint,
                no_login=args.no_login,
            )
        except utils.BreakExportingError:
            logging.info("Exit process...")
            return False
        except RuntimeError:
            launch_attempts += 1
            if max_launch_retries and launch_attempts >= max_launch_retries:
                logging.error(
                    "Launch book %s home page failed after %d attempts, skip"
                    % (book_id, launch_attempts)
                )
                return True
            logging.exception("Launch book %s home page failed" % book_id)
            await asyncio.sleep(2)
            continue

        try:
            await exporter.export_markdown(
                args.load_timeout,
                args.load_interval,
                args.jitter,
                args.shuffle,
                max_chapters,
            )
        except utils.RiskControlError as ex:
            logging.error("被风控拦截，停止导出：%s" % ex)
            await page.close()
            if args.cooldown > 0:
                logging.warning(
                    "冷却 %d 秒后退出。冷却期间请勿重试同一账号，建议当天停手，"
                    "硬刚只会加速封号。" % args.cooldown
                )
                await asyncio.sleep(args.cooldown)
            return False
        except utils.LoadChapterFailedError:
            logging.warning("Load chapter failed, close browser and retry")
            await page.close()
        else:
            await page.close()
            break

    await exporter.pre_process_markdown()
    title = await exporter.get_book_title()
    title = utils.format_filename(title)
    # 分类路径：output/<主分类>/<子分类>/<书名>_<hashid>/
    out_root = output_dir
    if subdir:
        for part in subdir.split("/"):
            out_root = os.path.join(out_root, utils.format_filename(part))
        book_dir = os.path.join(out_root, "%s_%s" % (title, book_id))
        os.makedirs(book_dir, exist_ok=True)
        out_root = book_dir
        # 复制书籍元数据到书目录：meta.json（机器版）+ 详情.json（中文人读版）
        src_meta = os.path.join("cache", book_id, "meta.json")
        if os.path.isfile(src_meta):
            try:
                shutil.copy(src_meta, os.path.join(out_root, "meta.json"))
                with open(src_meta, encoding="utf-8") as fp:
                    detail = export.human_detail(json.load(fp))
                with open(
                    os.path.join(out_root, "详情.json"), "w", encoding="utf-8"
                ) as fp:
                    json.dump(detail, fp, ensure_ascii=False, indent=2)
            except Exception:
                logging.exception("复制书籍元数据到书目录失败")

    if "epub" in args.output_format:
        save_path = os.path.join(out_root, "%s.epub" % title)
        if os.path.isfile(save_path):
            logging.info("File %s exist, ignore export" % save_path)
        else:
            await exporter.markdown_to_epub(save_path, extra_css=extra_css)
            logging.info("Save file %s complete" % save_path)

    if "pdf" in args.output_format:
        save_path = os.path.join(out_root, "%s.pdf" % title)
        if os.path.isfile(save_path):
            logging.info("File %s exist, ignore export" % save_path)
        else:
            image_format = "jpg"
            if sys.platform == "win32":
                image_format = "png"
            await exporter.markdown_to_pdf(
                save_path,
                extra_css=extra_css,
                image_format=image_format,
            )
            logging.info("Save file %s complete" % save_path)

    if "mobi" in args.output_format:
        if sys.platform != "linux":
            logging.error("Only linux system supported to export mobi format")
        else:
            epub_path = os.path.join(out_root, "%s.epub" % title)
            save_path = os.path.join(out_root, "%s.mobi" % title)
            if os.path.isfile(save_path):
                logging.info("File %s exist, ignore export" % save_path)
            else:
                await exporter.epub_to_mobi(epub_path, save_path)
                if not os.path.isfile(save_path):
                    logging.warning("Create mobi file failed")
                else:
                    logging.info("Save file %s complete" % save_path)

    if "txt" in args.output_format:
        save_path = os.path.join(out_root, "%s.txt" % title)
        if os.path.isfile(save_path):
            logging.info("File %s exist, ignore export" % save_path)
        else:
            await exporter.markdown_to_txt(save_path)
            logging.info("Save file %s complete" % save_path)
    return True


async def crawl_all(args, output_dir: str, extra_css: Optional[str]) -> int:
    """全量遍历模式：榜单 + 全部分类/子分类，每分类取前 N 本、每书限量章。"""
    tree = await categories.build_tree()
    targets = categories.flatten_targets(tree)
    if args.categories:
        names = [
            x.strip()
            for x in args.categories.split(",")
            if x.strip()
        ]
        targets, missing = categories.resolve_targets(tree, names)
        for name in missing:
            logging.warning("未识别的分类/榜单：%s（可用 --list-categories 查看）" % name)
    max_chapters = args.chapters_per_book
    if max_chapters is None:
        max_chapters = 1  # 遍历模式安全默认：每书只抓前 1 章
    logging.info(
        "全量遍历：%d 个目标，每分类取前 %d 本，每书最多 %d 章（风控安全默认）"
        % (len(targets), args.per_category or 0, max_chapters)
    )
    processed = set()
    for target in targets:
        logging.info("=== 遍历 %s（%s） ===" % (target["path"], target["code"]))
        try:
            books = await categories.fetch_books_all(
                target["code"],
                rank=(target["kind"] == "rank"),
                limit=args.per_category or 0,
            )
        except Exception:
            logging.exception("获取分类 %s 书单失败" % target["path"])
            continue
        for book in books:
            hid = book["hash_id"]
            if hid in processed:
                continue
            processed.add(hid)
            ok = await export_book(
                args,
                hid,
                output_dir,
                extra_css,
                subdir=target["path"],
                max_chapters=max_chapters,
                max_launch_retries=3,
            )
            if not ok:
                return -1
    return 0
