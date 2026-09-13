# 用途: 免登录抓单本全部免费章，输出 epub（不碰账号，零封号风险；适合批量下的第一选择）
# 用法: sh scripts/export-book-nologin-all.sh <book_id>
# 参数:
#   python -m weread_exporter   -m = 以「模块名」方式运行；weread_exporter 是本仓库的主包
#   -b "$1"      book-id，书 ID（详情页 URL 末段），必填
#   --no-login   免登录：不读也不写 cookie、不登录，只下免费章节
#   （没写 -o）   不传 -o 时默认输出 epub；产物在 output/
#   （没写 --chapters-per-book）  单本模式下不传即「全量」：抓到付费墙为止，
#                                 撞墙的章节会被识别出来跳过，不会把购买提示当正文存下来
python -m weread_exporter -b "$1" --no-login
