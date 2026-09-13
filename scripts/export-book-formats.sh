# 用途: 单本一次性导出全部 5 种格式，另留一份 markdown 方便直接读正文（接管模式）
# 用法: sh scripts/export-book-formats.sh <book_id>
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   -b "$1"                     book-id，书 ID（详情页 URL 末段），必填
#   -o md                       输出 markdown（正文原样，最适合直接看）
#   -o epub                     epub（手机端友好）
#   -o pdf                      pdf（电脑端友好）
#   -o mobi                     mobi（Kindle 用）—— 注意: 代码里只支持 Linux 生成，
#                               在 Windows/macOS 上这一项会被跳过、只打一行 error，其余格式照常
#   -o txt                      txt 纯文本
#   --cdp-endpoint <地址>        接管已登录的常驻 Chrome（先跑 launch-chrome.sh）
#   （-o 是 action=append，所以重复 5 次即可；只写 -o mobi 时程序会自动补上 epub）
python -m weread_exporter -b "$1" -o md -o epub -o pdf -o mobi -o txt --cdp-endpoint http://127.0.0.1:9222
