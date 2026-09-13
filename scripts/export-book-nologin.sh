# 用途: 免登录抓单本前 2 章 markdown，用来快速验收导出效果（不碰账号，零封号风险）
# 用法: sh scripts/export-book-nologin.sh <book_id>
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   -b "$1"                    book-id，书 ID（详情页 URL 末段），必填
#   --no-login                 免登录：不读也不写 cookie、不做登录，只下免费章节
#   -o md                      只输出 markdown（不依赖 weasyprint，跑得最快）
#   --chapters-per-book 2      每本最多抓 2 章；单本模式下不传这个参数表示「全量」，
#                              传 0 同样表示全量，这里给 2 是为了几秒内出结果
python -m weread_exporter -b "$1" --no-login -o md --chapters-per-book 2
