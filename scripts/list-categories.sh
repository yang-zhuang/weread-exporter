# 用途: 打印全部榜单 + 分类树后退出（不抓任何书），用来查分类代码、确认分类名怎么写
# 用法: sh scripts/list-categories.sh
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   --list-categories   打印分类树并退出；只发分类页请求，不抓书
#                       （首次运行会联网抓 21 个分类页，结果缓存到 cache/categories.json）
#   （不传 -b）         因为没给 book-id，程序走的就是「遍历模式」入口，这里被 --list-categories 提前拦下
python -m weread_exporter --list-categories
