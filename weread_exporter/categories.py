# -*- coding: utf-8 -*-
"""微信读书分类/榜单发现与书籍列表抓取（公开接口，不需要登录态）。

分类页   GET https://weread.qq.com/web/category/<code>
书单接口 GET https://weread.qq.com/web/bookListInCategory/<code>?maxIndex=N

编码约定（2026-09-01 实测）：
  侧边栏共 28 项：7 个榜单（字母 code）+ 21 个主分类（数字 code，不连续，必须从页面提取）。
    榜单：rising=飙升·出版 / hot_search=热搜榜 / newbook=新书·出版 /
          general_novel_rising=小说榜 / all=总榜 /
          newrating_publish=神作榜·出版 / newrating_potential_publish=神作潜力榜·出版
    主分类：100000 精品小说 … 2100000 医学健康 / 1900001 男生小说 / 2000001 女生小说
  子分类：主分类页 window.__INITIAL_STATE__.categoryStoreModule.categoryInfo.sublist[]，
          每项有 CategoryId / title / parentCategoryTitle。
          如 文学=300000 → 300001 古典文学 … 300014 世界名著（12 个）。
  书单接口按主分类/子分类/榜单 code 直接请求，翻页 maxIndex 每次 +20，单分类上限 1000 本。
  榜单需加 &rank=1。返回的 bookId 是数字字符串，用 utils.wr_hash() 转成 reader 用的
  hash id（已验证 wr_hash("34615967") == "0da329707210329f0da4d39"）。

分类树整体缓存在 cache/categories.json，避免每次全量遍历都抓 21 个分类页。
"""
import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from . import utils

ROOT_URL = "https://weread.qq.com"
CATEGORY_PAGE = ROOT_URL + "/web/category/%s"
BOOK_LIST_API = ROOT_URL + "/web/bookListInCategory/%s"
SIDEBAR_SAMPLE = "300000"  # 拿哪个分类页的侧边栏都一样，用文学页

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": CATEGORY_PAGE % SIDEBAR_SAMPLE,
    "Accept": "application/json, text/plain, */*",
}

_SIDEBAR_RE = re.compile(
    r'<a href="/web/category/([^"]+)" class="ranking_list_item_link">(.*?)</a>',
    re.S,
)

# 分类树缓存文件（相对 CWD，与现有 cache/ 目录一致）
CATEGORY_CACHE = os.path.join("cache", "categories.json")
# 书单接口翻页大小
PAGE_SIZE = 20
# 单分类服务端上限（超过也拿不到更多）
MAX_BOOKS_PER_CATEGORY = 1000


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


async def _fetch_text(url: str) -> str:
    data = await utils.fetch(url, headers=_HEADERS)
    return data.decode("utf-8", errors="replace")


def parse_initial_state(html: str) -> Dict[str, Any]:
    """解析分类页 HTML 里的 window.__INITIAL_STATE__ JSON。"""
    marker = "window.__INITIAL_STATE__="
    pos = html.find(marker)
    if pos < 0:
        raise RuntimeError("Unexpected category page html: no __INITIAL_STATE__")
    seg = html[pos + len(marker):]
    end = seg.find("</script>")
    if end > 0:
        seg = seg[:end]
    data, _ = json.JSONDecoder().raw_decode(seg)
    return data


async def fetch_sidebar() -> List[Dict[str, str]]:
    """抓一个分类页，提取侧边栏全部条目（榜单 + 主分类）。"""
    html = await _fetch_text(CATEGORY_PAGE % SIDEBAR_SAMPLE)
    items = []
    for m in _SIDEBAR_RE.finditer(html):
        code, body = m.group(1), m.group(2)
        name = _strip_tags(body)
        if code and name:
            items.append({"code": code, "name": name})
    if not items:
        raise RuntimeError("Failed to parse sidebar from category page")
    return items


async def fetch_category_info(code: str) -> Dict[str, Any]:
    """抓分类页，返回 categoryInfo（含 sublist 子分类）。"""
    html = await _fetch_text(CATEGORY_PAGE % code)
    data = parse_initial_state(html)
    info = (data.get("categoryStoreModule") or {}).get("categoryInfo")
    if not info:
        raise RuntimeError("No categoryInfo for category %s" % code)
    return info


async def fetch_subcategories(code: str) -> List[Dict[str, str]]:
    """某主分类的子分类列表：[{'code', 'name'}]。"""
    info = await fetch_category_info(code)
    subs = []
    for s in info.get("sublist") or []:
        cid = s.get("CategoryId")
        title = s.get("title")
        if cid is not None and title:
            subs.append({"code": str(cid), "name": title})
    return subs


def save_tree(tree: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CATEGORY_CACHE), exist_ok=True)
    tmp = CATEGORY_CACHE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fp:
        json.dump(tree, fp, ensure_ascii=False, indent=2)
    os.replace(tmp, CATEGORY_CACHE)


def load_tree() -> Optional[Dict[str, Any]]:
    if not os.path.isfile(CATEGORY_CACHE):
        return None
    try:
        with open(CATEGORY_CACHE, encoding="utf-8") as fp:
            tree = json.load(fp)
        if tree.get("categories") or tree.get("ranks"):
            return tree
    except Exception:
        pass
    return None


async def build_tree(use_cache: bool = True) -> Dict[str, Any]:
    """构建全量分类树：{'ranks': [...], 'categories': [{code,name,subs:[...]}], 'updated_at'}。

    榜单 code 是字母，主分类 code 是数字（isdigit 区分）。
    """
    if use_cache:
        cached = load_tree()
        if cached:
            return cached
    sidebar = await fetch_sidebar()
    ranks: List[Dict[str, Any]] = []
    categories: List[Dict[str, Any]] = []
    for item in sidebar:
        if item["code"].isdigit():
            categories.append(
                {"code": item["code"], "name": item["name"], "subs": []}
            )
        else:
            ranks.append(item)
    for cat in categories:
        try:
            cat["subs"] = await fetch_subcategories(cat["code"])
        except Exception:
            logging.exception(
                "Fetch subcategories of %s(%s) failed" % (cat["name"], cat["code"])
            )
        await asyncio.sleep(0.3)
    tree = {
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "ranks": ranks,
        "categories": categories,
    }
    try:
        save_tree(tree)
    except Exception:
        logging.exception("Save category tree failed")
    return tree


async def fetch_books(code: str, rank: bool = False, max_index: int = 0) -> Dict[str, Any]:
    """抓一页书单。返回 {'total_count', 'has_more', 'books': [...]}。"""
    url = BOOK_LIST_API % code
    if rank:
        url += "?rank=1"
        if max_index:
            url += "&maxIndex=%d" % max_index
    else:
        url += "?maxIndex=%d" % max_index
    data = await utils.fetch(url, headers=_HEADERS)
    payload = json.loads(data.decode("utf-8", errors="replace"))
    books = []
    for item in payload.get("books") or []:
        bi = item.get("bookInfo") or {}
        bid = str(bi.get("bookId") or "")
        if not bid:
            continue
        books.append(
            {
                "book_id": bid,
                "hash_id": utils.wr_hash(bid),
                "title": bi.get("title") or "",
                "author": bi.get("author") or "",
                "categories": [
                    c.get("title") or ""
                    for c in (bi.get("categories") or [])
                    if c.get("title")
                ],
                "search_idx": item.get("searchIdx"),
                "reading_count": item.get("readingCount"),
            }
        )
    return {
        "total_count": int(payload.get("totalCount") or 0),
        "has_more": bool(payload.get("hasMore")),
        "books": books,
    }


async def fetch_books_all(
    code: str, rank: bool = False, limit: int = 0
) -> List[Dict[str, Any]]:
    """翻页取该分类全部书。limit=0 不限制（服务端单分类上限 1000 本）。"""
    all_books: List[Dict[str, Any]] = []
    offset = 0
    while True:
        page = await fetch_books(code, rank=rank, max_index=offset)
        batch = page["books"]
        if not batch:
            break
        all_books.extend(batch)
        if limit and limit > 0 and len(all_books) >= limit:
            return all_books[:limit]
        if not page["has_more"] or len(all_books) >= page["total_count"]:
            break
        offset += len(batch)
        await asyncio.sleep(0.3)
    return all_books


def flatten_targets(tree: Dict[str, Any]) -> List[Dict[str, str]]:
    """展开为扁平抓取目标列表。

    - 榜单：每个榜单一个目标，路径 = 榜单名
    - 主分类有子分类：每个子分类一个目标，路径 = 主分类/子分类
    - 主分类无子分类：主分类自身一个目标，路径 = 主分类
    """
    targets: List[Dict[str, str]] = []
    for r in tree.get("ranks") or []:
        targets.append(
            {
                "kind": "rank",
                "code": r["code"],
                "name": r["name"],
                "path": r["name"],
            }
        )
    for cat in tree.get("categories") or []:
        subs = cat.get("subs") or []
        if subs:
            for s in subs:
                targets.append(
                    {
                        "kind": "category",
                        "code": s["code"],
                        "name": s["name"],
                        "path": "%s/%s" % (cat["name"], s["name"]),
                    }
                )
        else:
            targets.append(
                {
                    "kind": "category",
                    "code": cat["code"],
                    "name": cat["name"],
                    "path": cat["name"],
                }
            )
    return targets


def resolve_targets(
    tree: Dict[str, Any], names: List[str]
) -> tuple:
    """按用户输入（榜单名/主分类名/子分类名）过滤扁平目标。

    主分类名精确命中时返回该分类下全部子分类（如 "文学" → 文学/古典文学…）；
    其余先精确匹配 name/path，再退到子串包含。返回 (命中, 未识别)。
    """
    if not names:
        return [], []
    targets = flatten_targets(tree)
    # 主分类名 → 该分类下全部子分类目标
    cat_index: Dict[str, List[Dict[str, str]]] = {}
    for cat in tree.get("categories") or []:
        subs = cat.get("subs") or []
        prefix = cat["name"] + "/"
        cat_index[cat["name"]] = [
            t
            for t in targets
            if t["kind"] == "category"
            and (t["path"].startswith(prefix) if subs else t["name"] == cat["name"])
        ]
    hits, missing = [], []
    for raw in names:
        key = str(raw).strip()
        if not key:
            continue
        if key in cat_index and cat_index[key]:
            hits.extend(cat_index[key])
            continue
        matched = [t for t in targets if t["name"] == key or t["path"] == key]
        if not matched:
            matched = [t for t in targets if key in t["path"] or key in t["name"]]
        if matched:
            hits.extend(matched)
        else:
            missing.append(key)
    seen, unique = set(), []
    for t in hits:
        uid = (t["kind"], t["code"])
        if uid not in seen:
            seen.add(uid)
            unique.append(t)
    return unique, missing


def describe_tree(tree: Dict[str, Any]) -> str:
    """--list-categories 的可读输出。"""
    lines = ["分类树构建时间：%s" % tree.get("updated_at", "?")]
    ranks = tree.get("ranks") or []
    lines.append("【榜单】%d 个" % len(ranks))
    lines.append("  " + "、".join(r["name"] for r in ranks))
    cats = tree.get("categories") or []
    lines.append("【分类】%d 个主分类" % len(cats))
    for cat in cats:
        subs = cat.get("subs") or []
        if subs:
            lines.append("  %s（%d 个子分类）：%s" % (
                cat["name"], len(subs),
                "、".join(s["name"] for s in subs),
            ))
        else:
            lines.append("  %s（无子分类）" % cat["name"])
    return "\n".join(lines)
