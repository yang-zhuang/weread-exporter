# 用途: 免登录全量遍历分类，每本书只下免费章（没有账号可封，零账号风险）
# 用法: sh scripts/crawl-nologin.sh
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   （不传 -b）                没给 book-id → 进入遍历模式（跑全部分类/榜单）
#   --no-login               免登录：不读也不写 cookie、不登录，只下免费章节
#   --per-category 2         每个分类/子分类最多取前 2 本（默认 2；0 = 不限制）
#   --chapters-per-book 1    每本书只抓 1 章（遍历模式默认 1；0 = 全量）
#   （没写 --cdp-endpoint）   免登录不需要浏览器登录态，所以不接管常驻 Chrome；
#                             但 IP/设备层面仍有频率风控，别把间隔调太小
python -m weread_exporter --no-login --per-category 2 --chapters-per-book 1
