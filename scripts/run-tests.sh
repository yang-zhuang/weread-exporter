# 用途: 跑核心逻辑回归测试（29 项），全程 fake —— 不联网、不起浏览器，约 0.2 秒
# 用法: sh scripts/run-tests.sh
# 参数:
#   （这条命令没有可用参数）  直接执行测试文件即可；
#   测试文件自己在开头把仓库根目录插进 sys.path，所以不用额外设 PYTHONPATH
#   覆盖范围: wr_hash、付费墙检测、图片本地化、免费区优先、撞墙回退、元数据可读性、结构拆分、CLI 参数、日志节流
python tests/test_weread_exporter.py
