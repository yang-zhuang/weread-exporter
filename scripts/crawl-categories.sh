# 用途: 只遍历你指定的分类/榜单，不用把全量跑一遍（接管模式，需先跑 launch-chrome.sh）
# 用法: sh scripts/crawl-categories.sh "文学,飙升·出版"
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   "$1"                       要跑的 分类/榜单，逗号分隔，中文名或代码都认；"$1" 是脚本第一个参数，必填
#   --cdp-endpoint <地址>        接管已登录的常驻 Chrome
#   --categories <列表>          指定分类（这里把上面那个参数填进来）；名字写错会打警告并跳过
#   --per-category 5           每个分类最多取前 5 本（默认 2；0 = 不限制）
#   --chapters-per-book 1      每本书只抓 1 章（遍历模式默认 1；0 = 全量）
# 提示: 终端编码是 GBK 时中文参数可能变乱码，这种情况改用代码更稳 —— 文学 = 300000
#       （完整对照跑 sh scripts/list-categories.sh，或看 cache/categories.json）
python -m weread_exporter --cdp-endpoint http://127.0.0.1:9222 --categories "$1" --per-category 5 --chapters-per-book 1
