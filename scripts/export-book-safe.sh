# 用途: 单本导出 epub + pdf，并把所有风控相关参数显式写出来 —— 跑得慢，但最不容易被风控
# 用法: sh scripts/export-book-safe.sh <book_id>
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   -b "$1"                     book-id，书 ID（详情页 URL 末段），必填
#   -o epub / -o pdf            输出格式，各写一次；产物在 output/
#   --cdp-endpoint <地址>        接管已登录的常驻 Chrome（先跑 launch-chrome.sh）
#   --load-interval 30          每章之间的间隔 30 秒（默认值就是 30，这里是显式写出来）
#   --jitter 5                  在 30 秒基础上再随机 ±5 秒；固定节拍本身就是机器特征，抖动用来打散它（默认 5）
#   --verify-timeout 600        撞到验证码时停下来等你人工过码，最多等 600 秒（默认 600）
#   --cooldown 600              被风控拦截后冷却 600 秒再退出，防止你立刻重跑硬刚（默认 600）
python -m weread_exporter -b "$1" -o epub -o pdf --cdp-endpoint http://127.0.0.1:9222 --load-interval 30 --jitter 5 --verify-timeout 600 --cooldown 600
