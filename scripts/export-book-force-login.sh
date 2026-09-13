# 用途: 默认模式导出 epub，并强制先走一遍登录流程 —— 适合缓存里的 cookie 已失效、需要重新登录时
# 用法: sh scripts/export-book-force-login.sh <book_id>
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   -b "$1"          book-id，书 ID（详情页 URL 末段），必填
#   -o epub          输出格式，这里只导出 epub；产物在 output/
#   --force-login    启动浏览器后先登录再开始抓书，登录态写入 cache/cookie.txt
#                    与 --no-login 互斥，两个同时传时以 --no-login 为准（会打警告）
python -m weread_exporter -b "$1" -o epub --force-login
