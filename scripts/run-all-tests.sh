# 用途: 用 pytest 跑 tests/ 下的全部测试，比 run-tests.sh 多覆盖 test_utils.py 里的 wr_hash 校验
# 用法: sh scripts/run-all-tests.sh
# 参数:
#   -m pytest   以「模块名」方式运行 pytest（等价于直接敲 pytest 命令）
#   tests/      要跑的测试目录（含 test_weread_exporter.py 与 test_utils.py）
#   -v          verbose：逐条打印用例名，失败时更容易定位是哪个挂了
# 前提: 环境里要装了 pytest（conda 的 py12 环境有；没装就 python -m pip install pytest）
python -m pytest tests/ -v
