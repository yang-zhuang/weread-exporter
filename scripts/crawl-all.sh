# 用途: 全量遍历 7 个榜单 + 21 个主分类 × 全部子分类，按分类目录保存（接管模式，需先跑 launch-chrome.sh）
# 用法: sh scripts/crawl-all.sh
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   （不传 -b）               没给 book-id → 进入「遍历模式」，这是它和单本导出的唯一区别
#   --cdp-endpoint <地址>      接管已登录的常驻 Chrome（本机 9222）
#   --per-category 2          每个分类/子分类最多取前 2 本（默认值就是 2，0 表示不限制，单分类上限 1000）
#   --chapters-per-book 1     每本书只抓 1 章（遍历模式默认就是 1，0 表示全量）—— 风控安全默认
# 结果: 落在 output/<分类>/《书名》_<bookId>/ 下；同一本书出现在多个分类时按 bookId 去重只存一份
python -m weread_exporter --cdp-endpoint http://127.0.0.1:9222 --per-category 2 --chapters-per-book 1
