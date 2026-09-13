# 用途: 安装依赖（可编辑模式），clone 下来或换新机器后跑一次
# 用法: sh scripts/install.sh
# 参数:
#   -m pip        用 python -m 方式调用 pip，等价于 README「INSTALL」里的 pip3
#                 （Windows 上没有 pip3 这个命令，写 python -m pip 才通用）
#   -e .          editable 可编辑安装：把当前目录以「开发模式」装进 site-packages，
#                 之后改本仓库代码立刻生效，不用重新安装
python -m pip install -e .
