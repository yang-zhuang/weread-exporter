# 用途: 单本导出 epub + pdf，用「默认模式」（自建临时 profile + 注入 cookie）—— 风控风险最高，只建议拿来跑通流程
# 用法: sh scripts/export-book-default.sh <book_id>
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   -b "$1"         book-id，书 ID（详情页 URL 末段），必填
#   -o epub        输出 epub（-o 可重复）
#   -o pdf         输出 pdf；产物在 output/
#   （故意没写 --cdp-endpoint）  缺了它就走默认模式：每次新开临时 profile 再注入 cookie，
#                               对微信读书而言等于「一台陌生设备突然翻完整本书」，长期用极易被风控
python -m weread_exporter -b "$1" -o epub -o pdf
