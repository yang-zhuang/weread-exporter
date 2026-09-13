# 用途: 小批量冒烟测试：只跑「文学」一个分类，用快节奏参数确认整条链路通不通（接管模式）
# 用法: sh scripts/crawl-smoke.sh
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   --cdp-endpoint <地址>      接管已登录的常驻 Chrome（先跑 launch-chrome.sh）
#   --categories 300000       只遍历「文学」，300000 是它的分类代码（写中文名「文学」也可以）
#   --per-category 2          该分类最多取前 2 本
#   --chapters-per-book 1     每本书只抓 1 章
#   --load-interval 3         章与章之间只隔 3 秒（默认 30）—— 正式跑请调回 30，这里是故意压快
#   --jitter 1                间隔随机 ±1 秒（默认 5），配合上面的快节奏
# 注意: 冒烟参数是高频的，正式批量导出务必改回 --load-interval 30 --jitter 5
python -m weread_exporter --cdp-endpoint http://127.0.0.1:9222 --categories 300000 --per-category 2 --chapters-per-book 1 --load-interval 3 --jitter 1
