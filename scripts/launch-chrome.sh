# 用途: 启动接管模式的常驻 Chrome（开调试端口），接管模式的第一步；登录态存在独立 profile 里，只需登录一次
# 用法: sh scripts/launch-chrome.sh
# 参数:
#   （这条命令没带参数）  端口默认 9222、profile 默认 data/weread-profile
#   想改就编辑这一行，在命令后追加:
#     --port 9333                    换调试端口（下次导出要用 --cdp-endpoint 对上）
#     --profile-dir D:\some\dir      换配置目录（登录态存在这里，别指向日常浏览器 profile）
#     --chrome "C:\...\chrome.exe"   手动指定 Chrome 可执行文件
#   端口已在用时只打印提示、不会重复启动，重复执行是安全的
python launch_chrome.py
