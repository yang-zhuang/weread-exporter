# 用途: 单本导出 epub + pdf，走接管模式（推荐用法）；需先跑 launch-chrome.sh 并扫码登录
# 用法: sh scripts/export-book.sh <book_id>
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包，这就是主入口
#   -b "$1"                     book-id，书 ID；来自书籍详情页 URL 末段（如 .../web/bookDetail/0da329707210329f0da4d39）
#                               "$1" 是脚本的第一个命令行参数，必填
#   -o epub                    输出 epub 格式；-o 可重复，这里用了两次
#   -o pdf                     输出 pdf 格式；产物统一落在 output/ 目录
#   --cdp-endpoint <地址>       接管一个已经启动的 Chrome（这里指本机 9222 端口）
#                               不传这个参数就是「默认模式」：每次新建临时 profile 再注入 cookie，风控风险高
python -m weread_exporter -b "$1" -o epub -o pdf --cdp-endpoint http://127.0.0.1:9222
